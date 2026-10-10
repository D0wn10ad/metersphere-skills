# -*- coding: utf-8 -*-
"""skills/scripts/v2/ms.sh 新命令回归（todo 3）。

钉住六件事：

1. **G1 —— `functional-case import` 发 multipart 双 part。**
   v2.10 ``TestCaseController`` 的导入端点是
   ``@RequestPart("request") TestCaseImportRequest + @RequestPart("file") MultipartFile``，
   所以报文必须同时含 ``request=``（JSON）与 ``file=`` 两个 part；
   request 体只需 ``{projectId, importType, ignore:false[, versionId]}`` ——
   ``userId`` 在 excel 导入路径未被服务端使用（v2.10 实测），必须缺席。

2. **G2 —— importType 客户端预校验。**
   ``ExcelImportType`` 枚举仅 ``Create | Update``，非法值在发请求前就 die。

3. **G3 —— `functional-case template` 走 GET 模板端点，importType 进路径。**
   ``/test/case/export/template/{projectId}/{importType}``，默认 ``Create``。

4. **G4 —— `file list/get` 不再 die。**
   v2.10 ``FileMetadataController``：list = POST
   ``/file/metadata/project/{projectId}/{goPage}/{pageSize}``（body ``{}``）；
   get = GET ``/file/metadata/info/{id}``（返回文件字节流）。

5. **G5 —— `attachment unrelated` 与 relate 同形状。**
   body ``{belongId, belongType:"testcase", metadataRefIds:[…]}``，
   ``belongType`` 强制 ``"testcase"``（服务端校验非 testcase 即 invalid_parameter）。

6. **G6 —— `functional-case relate-demand` 发 ids 数组。**
   body ``{ids:[…], demandId, demandName}``；``demandId=="other"`` 时
   ``demandName`` 必填（v2.10 ``batchRelateDemand``：other 且空名直接 return）。

录制服务器在**测试进程内**跑（``ThreadingHTTPServer`` + daemon 线程），
无子进程残留、不在 /tmp 留状态文件；断言直接读内存里的 ``requests`` 记录。
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

PROJECT_ID = "proj-real-42"
FAKE_ACCESS_KEY = "fake-access-key"
FAKE_SECRET_KEY = "00112233445566778899aabbccddeeff"

TEMPLATE_BYTES = b"PK\x03\x04 fake-xlsx-template-bytes"
FILE_BYTES = b"PK\x03\x04 fake-project-file-bytes"


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

    def _send_bytes(self, code, payload):
        self.send_response(code)
        self.send_header("Content-Type", "application/octet-stream")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def _read_body(self):
        length = int(self.headers.get("Content-Length", 0))
        if not length:
            return ""
        return self.rfile.read(length).decode("utf-8", errors="replace")

    def do_GET(self):
        self.server.requests.append(("GET", self.path, self._read_body()))
        m = re.match(r"^/track/test/case/export/template/([^/]+)/([^/?]+)$",
                     self.path)
        if m:
            if m.group(2) in ("Create", "Update"):
                self._send_bytes(200, TEMPLATE_BYTES)
            else:
                self._send(200, {"success": False,
                                 "message": "importType 仅支持 Create|Update"})
            return
        m = re.match(r"^/track/file/metadata/info/([^/?]+)$", self.path)
        if m:
            self._send_bytes(200, FILE_BYTES)
            return
        if re.match(r"^/track/file/module/list/[^/?]+$", self.path):
            self._send(200, {"success": True, "data": [
                {"id": "folder-1", "name": "测试附件", "parentId": None,
                 "children": []}]})
            return
        self._send(404, {"error": "not found: %s" % self.path})

    def do_POST(self):
        body = self._read_body()
        self.server.requests.append(("POST", self.path, body))
        if self.path == "/track/test/case/import":
            received = extract_request_field(body)
            if "projectId" not in received or "importType" not in received:
                self._send(200, {"success": False,
                                 "message": "request 缺 projectId/importType",
                                 "received": received})
                return
            self.server.import_bodies.append(received)
            self._send(200, {"success": True, "data": {"errorPath": ""},
                             "received": received})
            return
        if re.match(r"^/track/file/metadata/project/[^/]+/\d+/\d+$", self.path):
            self._send(200, {"success": True, "data": {
                "listObject": [], "pageCount": 1, "itemCount": 0}})
            return
        if self.path == "/track/attachment/testcase/metadata/unrelated":
            self.server.unrelated_bodies.append(json.loads(body))
            self._send(200, {"success": True})
            return
        if self.path == "/track/test/case/batch/relate/demand":
            self.server.relate_demand_bodies.append(json.loads(body))
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
    def import_bodies(self):
        return self.httpd.import_bodies

    @property
    def unrelated_bodies(self):
        return self.httpd.unrelated_bodies

    @property
    def relate_demand_bodies(self):
        return self.httpd.relate_demand_bodies

    def bodies_for(self, path_pattern):
        """返回 path 命中正则的所有请求体（已按录制顺序）。"""
        rx = re.compile(path_pattern)
        return [body for _method, path, body in self.requests if rx.search(path)]

    def close(self):
        self.httpd.shutdown()
        self.thread.join(timeout=5)
        self.httpd.server_close()


@pytest.fixture
def recorder():
    """函数级录制服务器：内联线程 + shutdown，彻底无残留进程/端口。"""
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), RecordingHandler)
    httpd.requests = []
    httpd.import_bodies = []
    httpd.unrelated_bodies = []
    httpd.relate_demand_bodies = []
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
# G1: functional-case import 的 multipart 双 part 与 request 体
# --------------------------------------------------------------------------

def test_import_sends_multipart_double_part_and_request_body(recorder, tmp_path):
    """报文必须含 request=（JSON）与 file= 两个 part；request 体无 userId。"""
    excel = tmp_path / "cases.xlsx"
    excel.write_bytes(b"PK\x03\x04 fake")
    proc = run_ms_sh(
        ["functional-case", "import", PROJECT_ID, str(excel)],
        recorder.base_url)
    assert proc.returncode == 0, "stderr=%s" % proc.stderr
    assert len(recorder.import_bodies) == 1, (
        "import 请求应恰好录制一次：%s" % recorder.requests)
    received = recorder.import_bodies[0]
    assert received["projectId"] == PROJECT_ID
    assert received["importType"] == "Create"
    assert received["ignore"] is False
    assert "userId" not in received, (
        "userId 在 v2.10 excel 导入路径未被服务端使用，必须缺席：%r" % received)
    raw = recorder.bodies_for(r"/track/test/case/import")[0]
    assert 'name="request"' in raw, "报文缺 request part：%r" % raw[:200]
    assert 'name="file"' in raw, "报文缺 file part：%r" % raw[:200]
    assert 'filename="cases.xlsx"' in raw


def test_import_honors_import_type_and_version_id(recorder, tmp_path):
    """--import-type Update --version-id 必须进 request 体。"""
    excel = tmp_path / "cases.xlsx"
    excel.write_bytes(b"PK\x03\x04 fake")
    proc = run_ms_sh(
        ["functional-case", "import", PROJECT_ID, str(excel),
         "--import-type", "Update", "--version-id", "ver-9"],
        recorder.base_url)
    assert proc.returncode == 0, "stderr=%s" % proc.stderr
    received = recorder.import_bodies[0]
    assert received["importType"] == "Update"
    assert received["versionId"] == "ver-9"


def test_import_rejects_invalid_import_type_before_sending(recorder, tmp_path):
    """非法 importType 在发请求前 die（ExcelImportType 仅 Create|Update）。"""
    excel = tmp_path / "cases.xlsx"
    excel.write_bytes(b"PK\x03\x04 fake")
    proc = run_ms_sh(
        ["functional-case", "import", PROJECT_ID, str(excel),
         "--import-type", "Upsert"],
        recorder.base_url)
    assert proc.returncode != 0
    assert "Create|Update" in proc.stderr, "stderr=%s" % proc.stderr
    assert recorder.bodies_for(r"/track/test/case/import") == [], (
        "非法 importType 不应发出任何请求")


def test_import_rejects_missing_file(recorder, tmp_path):
    """excel 文件不存在时 die，不发请求。"""
    proc = run_ms_sh(
        ["functional-case", "import", PROJECT_ID,
         str(tmp_path / "no-such.xlsx")],
        recorder.base_url)
    assert proc.returncode != 0
    assert "不存在" in proc.stderr, "stderr=%s" % proc.stderr
    assert recorder.bodies_for(r"/track/test/case/import") == []


# --------------------------------------------------------------------------
# G2/G3: functional-case template 的路径与 importType 校验
# --------------------------------------------------------------------------

def test_template_downloads_binary_with_default_create(recorder, tmp_path):
    """默认 importType=Create，路径含 /Create，outfile 收到模板字节。"""
    outfile = tmp_path / "template.xlsx"
    proc = run_ms_sh(
        ["functional-case", "template", PROJECT_ID, "Create", str(outfile)],
        recorder.base_url)
    assert proc.returncode == 0, "stderr=%s" % proc.stderr
    assert outfile.read_bytes() == TEMPLATE_BYTES
    paths = [path for _m, path, _b in recorder.requests
             if "/test/case/export/template/" in path]
    assert paths == ["/track/test/case/export/template/%s/Create" % PROJECT_ID], (
        "模板请求路径不符：%s" % paths)
    assert "已下载" in proc.stdout


def test_template_defaults_to_create_when_import_type_omitted(recorder, tmp_path):
    """省略 importType 时默认 Create。"""
    outfile = tmp_path / "template.xlsx"
    proc = run_ms_sh(
        ["functional-case", "template", PROJECT_ID, "", str(outfile)],
        recorder.base_url)
    assert proc.returncode == 0, "stderr=%s" % proc.stderr
    paths = [path for _m, path, _b in recorder.requests
             if "/test/case/export/template/" in path]
    assert paths[-1].endswith("/Create")


def test_template_rejects_invalid_import_type(recorder):
    """非法 importType die，不发请求。"""
    proc = run_ms_sh(
        ["functional-case", "template", PROJECT_ID, "Bad"],
        recorder.base_url)
    assert proc.returncode != 0
    assert "Create|Update" in proc.stderr, "stderr=%s" % proc.stderr
    assert not [path for _m, path, _b in recorder.requests
                if "/test/case/export/template/" in path]


# --------------------------------------------------------------------------
# G4: file list / file get 不再 die
# --------------------------------------------------------------------------

def test_file_list_posts_empty_body_with_pagination(recorder):
    """file list 走 POST /file/metadata/project/{projectId}/{goPage}/{pageSize}，body {}。"""
    proc = run_ms_sh(["file", "list", PROJECT_ID, "2", "50"], recorder.base_url)
    assert proc.returncode == 0, "stderr=%s" % proc.stderr
    paths = [path for _m, path, _b in recorder.requests
             if "/file/metadata/project/" in path]
    assert paths == ["/track/file/metadata/project/%s/2/50" % PROJECT_ID], (
        "file list 路径不符：%s" % paths)
    bodies = recorder.bodies_for(r"/track/file/metadata/project/")
    assert bodies == ["{}"], "file list 请求体应为空对象：%r" % bodies


def test_file_list_defaults_pagination(recorder):
    """省略 goPage/pageSize 时默认 1/20。"""
    proc = run_ms_sh(["file", "list", PROJECT_ID], recorder.base_url)
    assert proc.returncode == 0, "stderr=%s" % proc.stderr
    paths = [path for _m, path, _b in recorder.requests
             if "/file/metadata/project/" in path]
    assert paths == ["/track/file/metadata/project/%s/1/20" % PROJECT_ID]


def test_file_list_without_project_dies_with_new_message(recorder):
    """无 projectId 时 die 新消息（不再是旧的「file 资源不支持 list/get」）。"""
    proc = run_ms_sh(["file", "list"], recorder.base_url, project_id="")
    assert proc.returncode != 0
    assert "file list 需要 projectId" in proc.stderr, "stderr=%s" % proc.stderr
    assert "file 资源不支持" not in proc.stderr, (
        "旧的 die 消息应已移除：%s" % proc.stderr)


def test_file_get_downloads_bytes(recorder, tmp_path):
    """file get 走 GET /file/metadata/info/{id}，outfile 收到文件字节流。"""
    outfile = tmp_path / "downloaded.bin"
    proc = run_ms_sh(["file", "get", "file-9", str(outfile)], recorder.base_url)
    assert proc.returncode == 0, "stderr=%s" % proc.stderr
    assert outfile.read_bytes() == FILE_BYTES
    paths = [path for _m, path, _b in recorder.requests
             if "/file/metadata/info/" in path]
    assert paths == ["/track/file/metadata/info/file-9"], (
        "file get 路径不符：%s" % paths)


def test_file_module_list_returns_folder_tree(recorder):
    """file-module list 走 GET /file/module/list/{projectId}（文件夹树，moduleId=文件夹 id）。"""
    proc = run_ms_sh(["file-module", "list", PROJECT_ID], recorder.base_url)
    assert proc.returncode == 0, "stderr=%s" % proc.stderr
    paths = [path for _m, path, _b in recorder.requests
             if "/file/module/list/" in path]
    assert paths == ["/track/file/module/list/%s" % PROJECT_ID], (
        "file-module list 路径不符：%s" % paths)
    doc = json.loads(proc.stdout)
    assert doc["data"][0]["id"] == "folder-1"
    assert doc["data"][0]["name"] == "测试附件"


def test_file_module_list_without_project_dies(recorder):
    """无 projectId 时 die（zh-CN），不发请求。"""
    proc = run_ms_sh(["file-module", "list"], recorder.base_url, project_id="")
    assert proc.returncode != 0
    assert "file-module list 需要 projectId" in proc.stderr, "stderr=%s" % proc.stderr
    assert not [p for _m, p, _b in recorder.requests
                if "/file/module/list/" in p]


# --------------------------------------------------------------------------
# G5: attachment unrelated 与 relate 同形状
# --------------------------------------------------------------------------

def test_unrelated_sends_testcase_belong_type_and_ids(recorder):
    """body {belongId, belongType:"testcase", metadataRefIds:[…]}，belongType 强制。"""
    proc = run_ms_sh(
        ["attachment", "unrelated", "case-1", "f-1", "f-2"],
        recorder.base_url)
    assert proc.returncode == 0, "stderr=%s" % proc.stderr
    assert len(recorder.unrelated_bodies) == 1
    received = recorder.unrelated_bodies[0]
    assert received["belongId"] == "case-1"
    assert received["belongType"] == "testcase", (
        "belongType 必须强制 testcase（服务端校验）：%r" % received)
    assert received["metadataRefIds"] == ["f-1", "f-2"]


def test_unrelated_requires_at_least_one_metadata_ref_id(recorder):
    """缺 metadataRefId 时 die，不发请求。"""
    proc = run_ms_sh(["attachment", "unrelated", "case-1"], recorder.base_url)
    assert proc.returncode != 0
    assert "metadataRefId" in proc.stderr, "stderr=%s" % proc.stderr
    assert recorder.unrelated_bodies == []


# --------------------------------------------------------------------------
# G6: functional-case relate-demand 发 ids 数组
# --------------------------------------------------------------------------

def test_relate_demand_sends_ids_array_and_demand_id(recorder):
    """body {ids:[…], demandId, demandName}；demandName 默认空串。"""
    proc = run_ms_sh(
        ["functional-case", "relate-demand", PROJECT_ID, "dem-1",
         "case-1", "case-2"],
        recorder.base_url)
    assert proc.returncode == 0, "stderr=%s" % proc.stderr
    assert len(recorder.relate_demand_bodies) == 1
    received = recorder.relate_demand_bodies[0]
    assert received["ids"] == ["case-1", "case-2"], (
        "ids 必须是数组：%r" % received.get("ids"))
    assert received["demandId"] == "dem-1"
    assert received["demandName"] == ""


def test_relate_demand_other_requires_demand_name(recorder):
    """demandId=="other" 且缺 --demand-name 时 die（v2.10 batchRelateDemand）。"""
    proc = run_ms_sh(
        ["functional-case", "relate-demand", PROJECT_ID, "other", "case-1"],
        recorder.base_url)
    assert proc.returncode != 0
    assert "--demand-name" in proc.stderr, "stderr=%s" % proc.stderr
    assert recorder.relate_demand_bodies == []


def test_relate_demand_other_with_demand_name(recorder):
    """demandId=="other" 且给了 --demand-name 时正常发请求。"""
    proc = run_ms_sh(
        ["functional-case", "relate-demand", PROJECT_ID, "other", "case-1",
         "--demand-name", "其他需求"],
        recorder.base_url)
    assert proc.returncode == 0, "stderr=%s" % proc.stderr
    received = recorder.relate_demand_bodies[0]
    assert received["demandId"] == "other"
    assert received["demandName"] == "其他需求"


def test_relate_demand_requires_at_least_one_case_id(recorder):
    """缺 caseId 时 die，不发请求。"""
    proc = run_ms_sh(
        ["functional-case", "relate-demand", PROJECT_ID, "dem-1"],
        recorder.base_url)
    assert proc.returncode != 0
    assert "caseId" in proc.stderr, "stderr=%s" % proc.stderr
    assert recorder.relate_demand_bodies == []


# --------------------------------------------------------------------------
# usage() 与录制服务器敏感性自证
# --------------------------------------------------------------------------

def test_usage_lists_all_new_commands(capsys):
    """usage 输出必须包含全部新命令（template/import/unrelated/relate-demand/file list/get）。"""
    proc = subprocess.run(["bash", MS_SH, "help"], cwd=REPO_ROOT,
                          capture_output=True, text=True, timeout=60)
    assert proc.returncode == 0, "stderr=%s" % proc.stderr
    out = proc.stdout
    for needle in ("functional-case template", "functional-case import",
                   "attachment unrelated", "functional-case relate-demand",
                   "file list", "file get"):
        assert needle in out, "usage 缺少 %s" % needle


def test_handler_rejects_unknown_track_paths(recorder):
    """录制服务器敏感性自证：未知 /track 路径必须 404，防止假阳性。"""
    proc = run_ms_sh(["functional-case", "template", PROJECT_ID, "Create"],
                     recorder.base_url)
    assert proc.returncode == 0
    recorder.httpd.requests.clear()
    import urllib.request
    try:
        urllib.request.urlopen(
            recorder.base_url + "/track/no/such/path", timeout=5)
        raised = False
    except urllib.error.HTTPError as exc:
        raised = exc.code == 404
    assert raised, "未知路径应返回 404"
