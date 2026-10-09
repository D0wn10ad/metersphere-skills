# -*- coding: utf-8 -*-
"""skills/scripts/v2/ms.sh 的 functional-case split-create 端到端回归（todo 5）。

钉住四件事：

1. **G1 —— 6 步编排顺序与同调用关联。**
   拆分（ms_split_cases.py）→ moduleId 解析注入 nodeId → name 查重 →
   项目文件上传原文件一次（file create）→ batch-create --file-id 写入
   （relateFileMetaIds 注入 + exists 预校验）→ 计数清单。
   上传必须先于 batch-create；batch-create 请求体每条含 relateFileMetaIds==[fileId]。

2. **G2 —— separate 降级模式。**
   --link-mode separate 对每个新 caseId 调既有 attachment relate，
   relate 调用次数 == 新用例数。

3. **G3 —— 查重幂等。**
   已存在同名用例跳过并计数，不重复写入。

4. **G4 —— 中途失败即停并报告已完成步骤。**
   stub 对 batch-create 返回 500 时，输出已完成步骤（①-④）并退出非 0。

录制服务器在测试进程内跑（ThreadingHTTPServer + daemon 线程），无残留；
全程只用回环 127.0.0.1；不读 .env、不需要真实凭据、不走外网。
"""
import json
import os
import re
import socket
import subprocess
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(os.path.dirname(TESTS_DIR))
MS_SH = os.path.join(REPO_ROOT, "skills", "scripts", "v2", "ms.sh")
XMIND_FIXTURE = os.path.join(TESTS_DIR, "fixtures", "sample.xmind")

PROJECT_ID = "proj-split-42"
FAKE_ACCESS_KEY = "fake-access-key"
FAKE_SECRET_KEY = "00112233445566778899aabbccddeeff"
FILE_ID = "file-777"

MODULE_TREE = {"success": True, "data": [
    {"id": "mod-root", "name": "未规划用例", "parentId": None, "level": 1,
     "children": [
         {"id": "mod-login", "name": "登录模块", "parentId": "mod-root",
          "level": 2, "children": []},
     ]},
]}


def extract_request_field(body):
    """从 curl -F multipart 报文里取出 request= 字段的 JSON（与既有 stub 同款正则）。"""
    m = re.search(
        r'name="request"[^\r\n]*\r\n(?:[^\r\n]+\r\n)*\r\n(.*?)\r\n--', body, re.S)
    candidate = (m.group(1) if m else body).strip()
    try:
        parsed = json.loads(candidate)
    except json.JSONDecodeError:
        return {"_raw": candidate}
    return parsed if isinstance(parsed, dict) else {"_raw": candidate}


class RecordingHandler(BaseHTTPRequestHandler):
    """把每个请求的 (method, path, body) 记进 ``server.requests``，供断言逐字检查。"""

    protocol_version = "HTTP/1.1"

    def log_message(self, fmt, *args):
        pass

    def _send(self, code, payload):
        body = json.dumps(payload, ensure_ascii=False,
                          separators=(",", ":")).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _read_body(self):
        length = int(self.headers.get("Content-Length", 0))
        if not length:
            return ""
        return self.rfile.read(length).decode("utf-8", errors="replace")

    def do_GET(self):
        self.server.requests.append(("GET", self.path, self._read_body()))
        if re.match(r"^/track/case/node/list/[^/?]+$", self.path):
            self._send(200, MODULE_TREE)
            return
        self._send(404, {"error": "not found: %s" % self.path})

    def do_POST(self):
        body = self._read_body()
        self.server.requests.append(("POST", self.path, body))
        if re.match(r"^/track/test/case/list/\d+/\d+$", self.path):
            self._send(200, {"success": True, "data": {
                "listObject": self.server.existing_names, "pageCount": 1,
                "itemCount": len(self.server.existing_names)}})
            return
        if self.path == "/track/file/metadata/exists":
            self._send(200, {"success": True, "data": [FILE_ID]})
            return
        if self.path == "/track/file/metadata/create":
            self.server.file_create_bodies.append(extract_request_field(body))
            self._send(200, {"success": True,
                             "data": [{"id": FILE_ID, "name": "sample.xmind"}]})
            return
        if self.path == "/track/test/case/add":
            if self.server.fail_case_add:
                self._send(500, {"success": False, "message": "stub 注入失败"})
                return
            received = extract_request_field(body)
            self.server.case_add_bodies.append(received)
            self._send(200, {"success": True,
                             "data": "case-%d" % len(self.server.case_add_bodies)})
            return
        if self.path == "/track/attachment/testcase/metadata/relate":
            self.server.relate_bodies.append(json.loads(body))
            self._send(200, {"success": True})
            return
        self._send(404, {"error": "not found: %s" % self.path})


def _free_port():
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])
    finally:
        sock.close()


class RecordingServer(object):
    """进程内录制服务器句柄：基址 + 已录请求 + 各命令载荷。"""

    def __init__(self, httpd, thread):
        self.httpd = httpd
        self.thread = thread
        self.port = httpd.server_address[1]
        self.base_url = "http://127.0.0.1:%d" % self.port

    @property
    def requests(self):
        return self.httpd.requests

    @property
    def file_create_bodies(self):
        return self.httpd.file_create_bodies

    @property
    def case_add_bodies(self):
        return self.httpd.case_add_bodies

    @property
    def relate_bodies(self):
        return self.httpd.relate_bodies

    def close(self):
        self.httpd.shutdown()
        self.thread.join(timeout=5)
        self.httpd.server_close()


@pytest.fixture
def recorder():
    """函数级录制服务器：内联线程 + shutdown，彻底无残留进程/端口。"""
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), RecordingHandler)
    httpd.requests = []
    httpd.file_create_bodies = []
    httpd.case_add_bodies = []
    httpd.relate_bodies = []
    httpd.existing_names = []
    httpd.fail_case_add = False
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    handle = RecordingServer(httpd, thread)
    try:
        yield handle
    finally:
        handle.close()


def run_ms_sh(args, base_url, project_id=PROJECT_ID):
    """跑 v2/ms.sh，返回 CompletedProcess（不检查返回码，由各用例自己断言）。"""
    env = dict(os.environ)
    env.update({
        "METERSPHERE_BASE_URL": base_url,
        "METERSPHERE_ACCESS_KEY": FAKE_ACCESS_KEY,
        "METERSPHERE_SECRET_KEY": FAKE_SECRET_KEY,
        "METERSPHERE_PROJECT_ID": project_id,
        "METERSPHERE_VERSION": "v2",
        "METERSPHERE_WORKSPACE_ID": "",
    })
    return subprocess.run(
        ["bash", MS_SH] + list(args),
        cwd=REPO_ROOT, env=env, capture_output=True, text=True, timeout=180)


# --------------------------------------------------------------------------
# G1: 6 步编排顺序与同调用关联
# --------------------------------------------------------------------------

def test_split_create_end_to_end_same_call(recorder):
    """xmind fixture → 拆分 2 条 → 上传先于 batch-create → relateFileMetaIds 注入。"""
    proc = run_ms_sh(
        ["functional-case", "split-create", PROJECT_ID, XMIND_FIXTURE],
        recorder.base_url)
    assert proc.returncode == 0, "stdout=%s\nstderr=%s" % (proc.stdout, proc.stderr)
    assert len(recorder.case_add_bodies) == 2, (
        "应写入 2 条用例：%s" % [b.get("name") for b in recorder.case_add_bodies])
    assert len(recorder.file_create_bodies) == 1, "原文件应恰好上传一次"
    upload = recorder.file_create_bodies[0]
    assert upload["projectId"] == PROJECT_ID
    assert upload["name"] == "sample.xmind"
    order = [path for _m, path, _b in recorder.requests]
    upload_idx = order.index("/track/file/metadata/create")
    add_idx = min(i for i, p in enumerate(order) if p == "/track/test/case/add")
    assert upload_idx < add_idx, "上传必须先于 batch-create 写入"
    for received in recorder.case_add_bodies:
        assert received.get("relateFileMetaIds") == [FILE_ID], (
            "batch-create 请求体必须带 relateFileMetaIds==[fileId]：%r" % received)
        assert received.get("nodeId") == "mod-login", (
            "nodePath /登录模块 应解析为模块树节点 id：%r" % received.get("nodeId"))
    assert "split-create 完成: 拆分 2 条 / 去重跳过 0 条 / 写入 2 条 / fileId=%s" % FILE_ID \
        in proc.stdout, "stdout=%s" % proc.stdout


def test_split_create_explicit_module_id(recorder):
    """显式 moduleId 参数 → 所有草稿 nodeId==moduleId，不查模块树。"""
    proc = run_ms_sh(
        ["functional-case", "split-create", PROJECT_ID, XMIND_FIXTURE, "mod-explicit"],
        recorder.base_url)
    assert proc.returncode == 0, "stdout=%s\nstderr=%s" % (proc.stdout, proc.stderr)
    assert recorder.case_add_bodies
    for received in recorder.case_add_bodies:
        assert received.get("nodeId") == "mod-explicit"
    assert not [p for _m, p, _b in recorder.requests
                if "/case/node/list/" in p], "显式 moduleId 不应查询模块树"


def test_split_create_unresolved_nodepath_exits(recorder):
    """nodePath 在模块树 0 匹配 → 告警不自动选，退出非 0，不写入。"""
    tree = {"success": True, "data": [
        {"id": "mod-root", "name": "未规划用例", "parentId": None, "level": 1,
         "children": []}]}
    recorder.httpd.requests.clear()

    class _Handler(RecordingHandler):
        def do_GET(self):
            self.server.requests.append(("GET", self.path, self._read_body()))
            if re.match(r"^/track/case/node/list/[^/?]+$", self.path):
                self._send(200, tree)
                return
            self._send(404, {"error": "not found: %s" % self.path})

    recorder.httpd.shutdown()
    recorder.thread.join(timeout=5)
    recorder.httpd.server_close()
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
    httpd.requests = []
    httpd.file_create_bodies = []
    httpd.case_add_bodies = []
    httpd.relate_bodies = []
    httpd.existing_names = []
    httpd.fail_case_add = False
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    recorder.httpd = httpd
    recorder.thread = thread
    try:
        proc = run_ms_sh(
            ["functional-case", "split-create", PROJECT_ID, XMIND_FIXTURE],
            recorder.base_url)
        assert proc.returncode != 0
        assert "0 或多个匹配" in proc.stderr, "stderr=%s" % proc.stderr
        assert recorder.case_add_bodies == [], "不自动选模块时不应写入任何用例"
    finally:
        recorder.close()


# --------------------------------------------------------------------------
# G2: separate 降级模式
# --------------------------------------------------------------------------

def test_split_create_separate_mode_relate_per_case(recorder):
    """--link-mode separate：relate 调用次数 == 新用例数，metadataRefIds==[fileId]。"""
    proc = run_ms_sh(
        ["functional-case", "split-create", PROJECT_ID, XMIND_FIXTURE,
         "--link-mode", "separate"],
        recorder.base_url)
    assert proc.returncode == 0, "stdout=%s\nstderr=%s" % (proc.stdout, proc.stderr)
    assert len(recorder.case_add_bodies) == 2
    assert len(recorder.relate_bodies) == 2, (
        "separate 模式 relate 调用次数应等于新用例数：%s" % recorder.relate_bodies)
    for body in recorder.relate_bodies:
        assert body["belongType"] == "testcase"
        assert body["metadataRefIds"] == [FILE_ID]
    assert "separate 模式完成: 关联 2 条用例附件" in proc.stdout


# --------------------------------------------------------------------------
# G3: 查重幂等
# --------------------------------------------------------------------------

def test_split_create_dedup_skips_existing(recorder):
    """已存在同名用例跳过并计数，不重复写入。"""
    recorder.httpd.existing_names = [{"name": "登录成功"}]
    proc = run_ms_sh(
        ["functional-case", "split-create", PROJECT_ID, XMIND_FIXTURE],
        recorder.base_url)
    assert proc.returncode == 0, "stdout=%s\nstderr=%s" % (proc.stdout, proc.stderr)
    names = [b.get("name") for b in recorder.case_add_bodies]
    assert names == ["登录失败"], "已存在同名应跳过：%s" % names
    assert "去重跳过 1 条" in proc.stdout
    assert "写入 1 条" in proc.stdout


def test_split_create_all_existing_idempotent(recorder):
    """全部同名已存在 → 幂等跳过，不上传不写入。"""
    recorder.httpd.existing_names = [{"name": "登录成功"}, {"name": "登录失败"}]
    proc = run_ms_sh(
        ["functional-case", "split-create", PROJECT_ID, XMIND_FIXTURE],
        recorder.base_url)
    assert proc.returncode == 0, "stdout=%s\nstderr=%s" % (proc.stdout, proc.stderr)
    assert recorder.case_add_bodies == []
    assert recorder.file_create_bodies == [], "全部已存在时不应上传原文件"
    assert "幂等跳过" in proc.stdout


# --------------------------------------------------------------------------
# G4: 中途失败即停并报告已完成步骤
# --------------------------------------------------------------------------

def test_split_create_mid_failure_reports_completed_steps(recorder):
    """stub 对 batch-create 返回 500 → 输出已完成步骤（①-④）并退出非 0。"""
    recorder.httpd.fail_case_add = True
    proc = run_ms_sh(
        ["functional-case", "split-create", PROJECT_ID, XMIND_FIXTURE],
        recorder.base_url)
    assert proc.returncode != 0
    assert "步骤 ④/⑤ 完成: fileId=%s" % FILE_ID in proc.stdout, (
        "已完成步骤应打印到 stdout：stdout=%s" % proc.stdout)
    assert "步骤 ⑤ batch-create 失败" in proc.stderr, "stderr=%s" % proc.stderr
    assert "④ 上传 fileId=%s" % FILE_ID in proc.stderr, (
        "die 消息应携带已完成步骤：%s" % proc.stderr)


def test_split_create_requires_file(recorder):
    """缺文件参数时 die，不发任何请求。"""
    proc = run_ms_sh(["functional-case", "split-create", PROJECT_ID],
                     recorder.base_url)
    assert proc.returncode != 0
    assert "文件" in proc.stderr, "stderr=%s" % proc.stderr
    assert recorder.requests == []
