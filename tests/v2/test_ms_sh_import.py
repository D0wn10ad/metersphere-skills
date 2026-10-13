# -*- coding: utf-8 -*-
"""C1：functional-case import 落库校验（skills/scripts/v2/ms.sh）。

钉住三件事（对应 .omo/plans/metersphere-v2-residual-fixes.md 任务 4）：

1. **HTTP 500 / success:false → 失败退出**：服务端回 500 + no_legitimate_case_tip
   时，ms.sh 必须 die（exit != 0）且 stderr 带服务端 message。

2. **success:true 但落库增量为 0 → 失败退出**：上游 getImportResponse 契约弱点
   （success 仅由 errList 为空决定，与 isUpdated/实际落库无关）——服务端回
   200 {"success":true,"errList":[],"isUpdated":false} 且不写任何用例时，
   ms.sh 必须 die（exit != 0）且 stderr 显式点名该契约弱点，不得报成功。

3. **success:true 且落库增量 > 0 → 成功**：正常导入新增 2 条用例后，
   ms.sh 必须 exit 0 且 stdout 打印 `import 完成: 新增 2 条`。

落库增量 = 导入前后两次 POST /track/test/case/list/{n}/{size}（body {projectId}）
返回的用例名集合差集。全部走本地 stub（import_stub_server.py），无真实网络。
"""
import os
import subprocess

TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(os.path.dirname(TESTS_DIR))
MS_SH = os.path.join(REPO_ROOT, "skills", "scripts", "v2", "ms.sh")

PROJECT_ID = "proj-import-c1"
FAKE_ACCESS_KEY = "fake-access-key"
FAKE_SECRET_KEY = "00112233445566778899aabbccddeeff"


def run_import(stub_server, fail_mode=None):
    """跑 functional-case import，返回 CompletedProcess（不检查返回码）。"""
    if fail_mode is not None:
        stub_server.set_fail_mode(fail_mode)
    excel = os.path.join(os.path.dirname(stub_server.state_path), "cases.xlsx")
    with open(excel, "wb") as fh:
        fh.write(b"PK\x03\x04 fake")
    env = dict(os.environ)
    env.update({
        "METERSPHERE_BASE_URL": stub_server.base_url,
        "METERSPHERE_ACCESS_KEY": FAKE_ACCESS_KEY,
        "METERSPHERE_SECRET_KEY": FAKE_SECRET_KEY,
        "METERSPHERE_PROJECT_ID": PROJECT_ID,
        "METERSPHERE_VERSION": "v2",
        "METERSPHERE_WORKSPACE_ID": "",
    })
    return subprocess.run(
        ["bash", MS_SH, "functional-case", "import", PROJECT_ID, str(excel)],
        cwd=REPO_ROOT, env=env, capture_output=True, text=True, timeout=180)


def test_import_http_500_fails_with_server_message(stub_server):
    """(a) HTTP 500 + success:false → die，stderr 带 no_legitimate_case_tip。"""
    proc = run_import(stub_server, fail_mode="import_500")
    assert proc.returncode != 0, "HTTP 500 必须失败退出：%s" % proc.stdout
    assert "no_legitimate_case_tip" in proc.stderr, (
        "stderr 应带服务端 message：%s" % proc.stderr)


def test_import_success_true_but_zero_landing_fails(stub_server):
    """(b) success:true 但落库增量为 0 → die，stderr 点名契约弱点。"""
    proc = run_import(stub_server, fail_mode="import_noop")
    assert proc.returncode != 0, "success:true 但零落库必须失败退出：%s" % proc.stdout
    assert ("契约弱点" in proc.stderr or "getImportResponse" in proc.stderr), (
        "stderr 应显式点名上游契约弱点：%s" % proc.stderr)


def test_import_success_true_with_positive_landing_ok(stub_server):
    """(c) success:true 且落库增量 > 0 → exit 0，stdout 打印新增条数。"""
    proc = run_import(stub_server)
    assert proc.returncode == 0, "正常导入应成功：stderr=%s" % proc.stderr
    assert "新增" in proc.stdout and "条" in proc.stdout, (
        "stdout 应打印 `import 完成: 新增 N 条`：%s" % proc.stdout)