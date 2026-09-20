#!/usr/bin/env python3
import json
import os
import subprocess
import sys
import time
import uuid
from pathlib import Path
from urllib import request, error

SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPT_DIR.parent
ENV_FILE = SKILL_DIR / '.env'

if ENV_FILE.exists():
    for line in ENV_FILE.read_text(encoding='utf-8').splitlines():
        line = line.strip()
        if line and not line.startswith('#') and '=' in line:
            k, v = line.split('=', 1)
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))

BASE_URL = os.environ.get('METERSPHERE_BASE_URL', '').rstrip('/')
ACCESS_KEY = os.environ.get('METERSPHERE_ACCESS_KEY') or os.environ.get('METERSPHERE_ACCESS_KEY', '')
SECRET_KEY = os.environ.get('METERSPHERE_SECRET_KEY') or os.environ.get('METERSPHERE_SECRET_KEY', '')


def die(msg: str):
    print(msg, file=sys.stderr)
    sys.exit(1)


def signature() -> str:
    plain = f"{ACCESS_KEY}|{uuid.uuid4()}|{int(time.time() * 1000)}"
    proc = subprocess.run([
        'openssl', 'enc', '-aes-128-cbc',
        '-K', SECRET_KEY.encode('utf-8').hex(),
        '-iv', ACCESS_KEY.encode('utf-8').hex(),
        '-base64', '-A', '-nosalt'
    ], input=plain.encode('utf-8'), capture_output=True, check=True)
    return proc.stdout.decode('utf-8').strip()


def headers():
    if not BASE_URL or not ACCESS_KEY or not SECRET_KEY:
        die('缺少 METERSPHERE_BASE_URL / METERSPHERE_ACCESS_KEY / METERSPHERE_SECRET_KEY')
    return {
        'Content-Type': 'application/json',
        'accessKey': ACCESS_KEY,
        'signature': signature(),
    }


def post_json(path: str, body: dict):
    req = request.Request(
        BASE_URL + path,
        data=json.dumps(body, ensure_ascii=False).encode('utf-8'),
        headers=headers(),
        method='POST',
    )
    with request.urlopen(req, timeout=60) as resp:
        return json.loads(resp.read().decode('utf-8', errors='replace'))


def get_json(path: str):
    req = request.Request(BASE_URL + path, headers=headers(), method='GET')
    with request.urlopen(req, timeout=60) as resp:
        return json.loads(resp.read().decode('utf-8', errors='replace'))


def case_detail(case_id: str):
    return (get_json(f'/track/test/case/get/{case_id}').get('data') or {})


def case_reviews(case_id: str):
    data = post_json('/track/test/review/case/list/1/100', {'caseId': case_id}).get('data') or {}
    return data.get('listObject') or []


def _bug_key(bug: dict):
    return bug.get('bugId') or bug.get('id') or bug.get('num') or json.dumps(bug, ensure_ascii=False, sort_keys=True)


def _parse_steps(raw):
    # steps 通常为 JSON 数组字符串，但 API 创建的用例可能存纯文本（如 "1. verify"），
    # json.loads 会抛 Extra data；降级为单步纯文本，保证 case-report 不崩。
    if not raw:
        return []
    try:
        val = json.loads(raw)
    except ValueError:
        return [{'num': 1, 'desc': str(raw)}]
    return val if isinstance(val, list) else [{'num': 1, 'desc': json.dumps(val, ensure_ascii=False)}]


def case_bugs(project_id: str, case_id: str):
    lists = []

    # v2.10 "用例关联 issue" 端点是 GET /issues/get/case/{refType}/{id}
    # (getIssuesByCaseId, test_case_issues join, refType=FUNCTIONAL)；data 为列表非包络。
    # 勿用 POST /test/case/issues/list——语义相反（按 issue 查用例，必填 issuesId，否则 500）。
    data = get_json(f'/track/issues/get/case/FUNCTIONAL/{case_id}').get('data') or []
    if isinstance(data, list):
        lists.extend(data)
    else:
        lists.extend(data.get('listObject') or [])

    merged = {}
    for bug in lists:
        key = _bug_key(bug)
        if key not in merged:
            merged[key] = bug
        else:
            merged[key] = {**merged[key], **{k: v for k, v in bug.items() if v not in (None, '', [], {})}}
    return list(merged.values())


def build_summary(detail: dict, bugs: list, reviews: list):
    return {
        'caseId': detail.get('id'),
        'num': detail.get('num'),
        'name': detail.get('name'),
        'moduleId': detail.get('moduleId'),
        'moduleName': detail.get('moduleName'),
        'projectId': detail.get('projectId'),
        'versionId': detail.get('versionId'),
        'versionName': detail.get('versionName'),
        'caseEditType': detail.get('caseEditType'),
        'functionalPriority': detail.get('functionalPriority'),
        'reviewStatus': detail.get('reviewStatus'),
        'lastExecuteResult': detail.get('lastExecuteResult'),
        'bugCount': max(int(detail.get('bugCount') or 0), len(bugs)),
        'caseReviewCount': detail.get('caseReviewCount', len(reviews)),
        'testPlanCount': detail.get('testPlanCount', 0),
        'demandCount': detail.get('demandCount', 0),
        'reviewed': len(reviews) > 0,
    }


def main():
    if len(sys.argv) != 3:
        die('用法: ms_case_report.py <projectId> <caseId>')
    project_id = sys.argv[1]
    case_id = sys.argv[2]

    detail = case_detail(case_id)
    reviews = case_reviews(case_id)
    bugs = case_bugs(project_id, case_id)

    result = {
        'summary': build_summary(detail, bugs, reviews),
        'detail': {
            'prerequisite': detail.get('prerequisite'),
            'description': detail.get('description'),
            'textDescription': detail.get('textDescription'),
            'expectedResult': detail.get('expectedResult'),
            'steps': _parse_steps(detail.get('steps')),
            'attachments': detail.get('attachments') or [],
            'tags': detail.get('tags') or [],
        },
        'bugs': [
            {
                'id': b.get('id'),
                'num': b.get('num'),
                'name': b.get('name'),
                'statusName': b.get('statusName'),
                'handleUserName': b.get('handleUserName'),
                'createUserName': b.get('createUserName'),
                'createTime': b.get('createTime'),
            }
            for b in bugs
        ],
        'reviews': [
            {
                'reviewId': r.get('reviewId'),
                'reviewNum': r.get('reviewNum'),
                'reviewName': r.get('reviewName'),
                'reviewStatus': r.get('reviewStatus'),
                'caseReviewStatus': r.get('status'),
            }
            for r in reviews
        ],
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    try:
        main()
    except error.HTTPError as e:
        detail = e.read().decode('utf-8', errors='replace')
        die(f'HTTP {e.code}: {detail}')
    except Exception as e:
        die(str(e))
