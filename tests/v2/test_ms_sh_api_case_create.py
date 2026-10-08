# -*- coding: utf-8 -*-
"""skills/scripts/v2/ms.sh 的 api-case 写入路径回归（todo 4）。

钉住两件事：

1. **G1 —— `api-case create` 必须自带 id / priority。**
   MeterSphere v2.10 的 ``ApiTestCaseService.createTest()`` 里是
   ``test.setId(request.getId()); test.setPriority(request.getPriority());``，
   而该文件**零** ``IDGenerator`` 调用 —— 服务端不再兜底，客户端不给 id 就落库失败
   （服务端 error.log 实证：``Column 'id' cannot be null``）。
   所以 ms.sh 在 ``create`` 分支里对 api-case 补默认值：**仅在缺省时**注入
   ``id`` = 新 uuid4、``priority`` = ``P1``，调用方显式给的一律保留。

2. **G2 —— `api-case generate-create --tags` 把 phabricator 票据标签写进每条用例。**
   v2.10 的 ``tags`` 是 **String**（``if (StringUtils.equals("[]", request.getTags()))``），
   因此载荷里必须是 **JSON 编码后的字符串**（``"[\"T-story\",\"T-tech\"]"``），
   而不是裸数组；不给 ``--tags`` 时 ``tags`` 键必须**整个缺席**（连 ``"[]"`` 都不许出现）。

**列表污染守卫（最重要的一条）**：``id``/``priority`` 的注入绝不能进
``normalize_json_with_defaults()`` —— 该函数还有一个调用点在 ``list`` 分支，
一旦在那里注入，``api-case list`` 的查询体就会带上 ``id``/``priority``，
可能被服务端当成**过滤条件**，静默把结果筛掉。``test_list_body_has_no_id_or_priority``
用「同一台服务器既录到 create 的 id、又录不到 list 的 id」的正反对照把这条钉死。

录制服务器在**测试进程内**跑（``ThreadingHTTPServer`` + daemon 线程），
所以既没有子进程残留，也不会在 ``/tmp/opencode`` 留状态文件；
断言直接读内存里的 ``requests`` 记录，能逐字看到 ms.sh 发出去的请求体。

全程只用回环 127.0.0.1；不读 .env、不需要真实凭据、不走外网、不碰 v1 脚本。
"""
import json
import os
import re
import socket
import subprocess
import threading
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(os.path.dirname(TESTS_DIR))
MS_SH = os.path.join(REPO_ROOT, "skills", "scripts", "v2", "ms.sh")
DEFINITION_FIXTURE = os.path.join(TESTS_DIR, "fixtures",
                                  "definition_get_c6e4293e.json")

# 生成器读 fixture 里的 data.id；ms.sh 按 definition/list 返回的 id 去 GET 详情。
with open(DEFINITION_FIXTURE, encoding="utf-8") as _fh:
    FIXTURE_DATA = json.load(_fh)["data"]
DEFINITION_ID = FIXTURE_DATA["id"]

PROJECT_ID = "proj-real-42"
# AES-128 的 key = hex(SECRET_KEY)，故 SECRET_KEY 必须是 16 字节（32 位 hex）。
FAKE_ACCESS_KEY = "fake-access-key"
FAKE_SECRET_KEY = "00112233445566778899aabbccddeeff"

MULTIPART_BOUNDARY = "----msshapicaseboundary"


def extract_request_field(body):
    """从 curl -F multipart 报文里取出 request= 字段的 JSON（与 todo1 stub 同款正则）。"""
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
        if self.path == "/":
            self._send(200, {"ok": True})
            return
        m = re.match(r"^/api/api/definition/get/([^/?]+)", self.path)
        if m:
            if m.group(1) == DEFINITION_ID:
                self._send(200, {"success": True, "data": FIXTURE_DATA})
            else:
                self._send(200, {"success": True, "data": None})
            return
        self._send(404, {"error": "not found: %s" % self.path})

    def do_POST(self):
        body = self._read_body()
        self.server.requests.append(("POST", self.path, body))
        if re.match(r"^/api/api/definition/list/\d+/\d+$", self.path):
            self._send(200, {"success": True, "data": {
                "listObject": [{"id": DEFINITION_ID, "name": FIXTURE_DATA["name"],
                                "method": FIXTURE_DATA["method"]}],
                "pageCount": 1, "itemCount": 1}})
            return
        if re.match(r"^/api/api/testcase/list/\d+/\d+$", self.path):
            # 恒定返回空列表：**结果条数不携带任何信息**，所以断言只能看录到的请求体。
            self._send(200, {"success": True, "data": {
                "listObject": [], "pageCount": 1, "itemCount": 0}})
            return
        if self.path == "/api/api/testcase/create":
            received = extract_request_field(body)
            missing = [f for f in ("id", "priority") if f not in received]
            if missing:
                # 复刻 v2.10 的绑定失败：缺 id/priority 一律拒。
                self._send(400, {"success": False,
                                 "message": "create 需要 id 与 priority",
                                 "missing": missing, "received": received})
                return
            self.server.create_bodies.append(received)
            self._send(200, {"success": True,
                             "data": {"id": "mock-%d" % (len(self.server.create_bodies) + 1)},
                             "received": received})
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
    """进程内录制服务器句柄：基址 + 已录请求 + 已录 create 载荷。"""

    def __init__(self, httpd, thread):
        self.httpd = httpd
        self.thread = thread
        self.port = httpd.server_address[1]
        self.base_url = "http://127.0.0.1:%d" % self.port

    @property
    def requests(self):
        return self.httpd.requests

    @property
    def create_bodies(self):
        return self.httpd.create_bodies

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
    httpd.create_bodies = []
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


def is_uuid4(value):
    """uuid4 形态校验：8-4-4-4-12，且 version 位为 4、variant 位为 8/9/a/b。"""
    if not isinstance(value, str):
        return False
    if not re.fullmatch(r"[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}",
                        value):
        return False
    return str(uuid.UUID(value).version) == "4"


# --------------------------------------------------------------------------
# G1: api-case create 的 id / priority 注入
# --------------------------------------------------------------------------

def test_create_injects_uuid4_id_and_priority_when_absent(recorder):
    """JSON 省略 id/priority 时，载荷必须带上真 uuid4 与 P1（否则服务端 400）。"""
    proc = run_ms_sh(
        ["api-case", "create",
         json.dumps({"name": "注入用例", "apiDefinitionId": "api-1", "request": {"method": "GET", "url": "http://x/y", "headers": [], "body": {}}})],
        recorder.base_url)
    assert proc.returncode == 0, "stderr=%s" % proc.stderr
    payload = json.loads(proc.stdout)
    assert payload["success"] is True, (
        "服务端因缺 id/priority 拒绝创建：%s" % proc.stdout)
    received = payload["received"]
    assert is_uuid4(received["id"]), "注入的 id 不是合法 uuid4：%r" % received["id"]
    assert received["priority"] == "P1"
    assert received["name"] == "注入用例"


def test_create_keeps_caller_supplied_id_and_priority(recorder):
    """调用方显式给了 id/priority 就不许覆盖（注入只在缺省时发生）。"""
    proc = run_ms_sh(
        ["api-case", "create",
         json.dumps({"id": "caller-id-1", "priority": "P0", "name": "保留用例",
                     "apiDefinitionId": "api-1", "request": {"method": "GET", "url": "http://x/y", "headers": [], "body": {}}})],
        recorder.base_url)
    assert proc.returncode == 0, "stderr=%s" % proc.stderr
    received = json.loads(proc.stdout)["received"]
    assert received["id"] == "caller-id-1"
    assert received["priority"] == "P0"


def test_create_injects_only_the_missing_field(recorder):
    """只缺 priority（或只缺 id）时，补的那一个不能碰已有的那个。"""
    proc = run_ms_sh(
        ["api-case", "create",
         json.dumps({"id": "caller-id-2", "name": "半缺用例", "apiDefinitionId": "api-1", "request": {"method": "GET", "url": "http://x/y", "headers": [], "body": {}}})],
        recorder.base_url)
    assert proc.returncode == 0, "stderr=%s" % proc.stderr
    received = json.loads(proc.stdout)["received"]
    assert received["id"] == "caller-id-2"
    assert received["priority"] == "P1"


def test_create_ids_are_fresh_per_invocation(recorder):
    """每次调用各自生成新 id（不能是写死的同一个值）。"""
    ids = set()
    for index in range(2):
        proc = run_ms_sh(
            ["api-case", "create",
             json.dumps({"name": "唯一-%d" % index, "apiDefinitionId": "api-1", "request": {"method": "GET", "url": "http://x/y", "headers": [], "body": {}}})],
            recorder.base_url)
        assert proc.returncode == 0, "stderr=%s" % proc.stderr
        ids.add(json.loads(proc.stdout)["received"]["id"])
    assert len(ids) == 2, "两次调用生成了相同的 id：%r" % ids


def test_create_injection_does_not_add_a_priority_flag(recorder):
    """计划禁止 priority 覆盖开关：--priority 必须不是被认识的 flag。"""
    proc = run_ms_sh(
        ["api-case", "create", json.dumps({"name": "x", "apiDefinitionId": "a", "request": {"method": "GET", "url": "http://x/y", "headers": [], "body": {}}}),
         "--priority", "P0"],
        recorder.base_url)
    # 多余的 --priority 不该被当成"设置优先级"的开关：注入的仍是默认 P1
    assert recorder.create_bodies, "create 未到达服务端：%s" % proc.stderr
    assert all(b["priority"] == "P1" for b in recorder.create_bodies)


# --------------------------------------------------------------------------
# 列表污染守卫（最重要）
# --------------------------------------------------------------------------

def test_list_body_has_no_id_or_priority(recorder):
    """api-case list 的查询体绝不能出现 id/priority（否则会静默过滤结果）。"""
    proc = run_ms_sh(["api-case", "list", json.dumps({"keyword": "登录"})],
                     recorder.base_url)
    assert proc.returncode == 0, "stderr=%s" % proc.stderr
    bodies = recorder.bodies_for(r"^/api/api/testcase/list/")
    assert bodies, "list 请求未到达服务端：%s" % proc.stdout
    body = json.loads(bodies[-1])
    assert "id" not in body, "list 查询体被污染进了 id：%s" % body
    assert "priority" not in body, "list 查询体被污染进了 priority：%s" % body
    # 对照：normalize 仍然照常补默认字段，证明断言不是因为"什么都没补"而空过
    assert body["projectId"] == PROJECT_ID
    assert body["keyword"] == "登录"
    assert body["protocols"] == ["HTTP"]


def test_recorder_is_sensitive_enough_to_catch_id_in_a_body(recorder):
    """正反对照：同一台服务器能录到 create 体的 id ⇒ 上面那条 list 断言不是空过。"""
    proc = run_ms_sh(
        ["api-case", "create",
         json.dumps({"name": "对照用例", "apiDefinitionId": "api-1", "request": {"method": "GET", "url": "http://x/y", "headers": [], "body": {}}})],
        recorder.base_url)
    assert proc.returncode == 0, "stderr=%s" % proc.stderr
    created = recorder.create_bodies[-1]
    assert isinstance(created, dict)
    assert is_uuid4(created["id"]), "录制器没录到 create 体的 id：%r" % created


def test_keyword_list_path_also_stays_clean(recorder):
    """关键词形态（default_list_payload 而非 normalize）同样不得带 id/priority。"""
    proc = run_ms_sh(["api-case", "list", "登录"], recorder.base_url)
    assert proc.returncode == 0, "stderr=%s" % proc.stderr
    body = json.loads(recorder.bodies_for(r"^/api/api/testcase/list/")[-1])
    assert "id" not in body and "priority" not in body, body


# --------------------------------------------------------------------------
# G2: generate-create --tags
# --------------------------------------------------------------------------

def test_generate_create_injects_tags_as_json_encoded_string(recorder):
    """--tags 的值必须是 JSON 编码字符串（v2.10 的 tags 是 String），不是裸数组。"""
    proc = run_ms_sh(
        ["api-case", "generate-create", "--tags", "T-story,T-tech",
         PROJECT_ID, DEFINITION_ID],
        recorder.base_url)
    assert proc.returncode == 0, "stderr=%s" % proc.stderr
    assert recorder.create_bodies, "没有用例创建成功：%s / %s" % (proc.stdout, proc.stderr)
    assert len(recorder.create_bodies) >= 1
    for body in recorder.create_bodies:
        assert "tags" in body, "生成的用例载荷缺少 tags 键：%r" % body.get("name")
        raw = body["tags"]
        assert isinstance(raw, str), (
            "tags 必须是 JSON 编码的字符串，收到 %r（类型 %s）" % (raw, type(raw).__name__))
        assert json.loads(raw) == ["T-story", "T-tech"]


def test_generate_create_tags_accepts_space_separated_values(recorder):
    """一个值里用空格分隔也算多个标签。"""
    proc = run_ms_sh(
        ["api-case", "generate-create", "--tags", "T-a T-b", PROJECT_ID, DEFINITION_ID],
        recorder.base_url)
    assert proc.returncode == 0, "stderr=%s" % proc.stderr
    assert recorder.create_bodies
    assert json.loads(recorder.create_bodies[0]["tags"]) == ["T-a", "T-b"]


def test_generate_create_tags_flag_is_repeatable(recorder):
    """--tags 可重复出现，标签累积去重。"""
    proc = run_ms_sh(
        ["api-case", "generate-create", "--tags", "T-a", "--tags", "T-b,T-a",
         PROJECT_ID, DEFINITION_ID],
        recorder.base_url)
    assert proc.returncode == 0, "stderr=%s" % proc.stderr
    assert recorder.create_bodies
    assert json.loads(recorder.create_bodies[0]["tags"]) == ["T-a", "T-b"]


def test_generate_create_tags_equals_form(recorder):
    """--tags=VALUE 也认（等价写法）。"""
    proc = run_ms_sh(
        ["api-case", "generate-create", "--tags=T-eq", PROJECT_ID, DEFINITION_ID],
        recorder.base_url)
    assert proc.returncode == 0, "stderr=%s" % proc.stderr
    assert recorder.create_bodies
    assert json.loads(recorder.create_bodies[0]["tags"]) == ["T-eq"]


def test_generate_create_strips_tags_before_reading_project_id(recorder):
    """--tags 必须在位置参数赋值前被剥离：projectId 不能被读成字面量 "--tags"。"""
    proc = run_ms_sh(
        ["api-case", "generate-create", "--tags", "T-story", PROJECT_ID],
        recorder.base_url)
    assert proc.returncode == 0, "stderr=%s" % proc.stderr
    list_bodies = recorder.bodies_for(r"^/api/api/definition/list/")
    assert list_bodies, "定义列表请求未发生：%s / %s" % (proc.stdout, proc.stderr)
    body = json.loads(list_bodies[-1])
    assert body["projectId"] == PROJECT_ID, (
        "projectId 被 --tags 顶掉了（写入可能瞄准错误项目）：%r" % body["projectId"])
    assert body["projectId"] != "--tags"


def test_generate_create_without_tags_omits_the_key(recorder):
    """不给 --tags 时，tags 键必须整个缺席（连 "[]" 或 null 都不许出现）。"""
    proc = run_ms_sh(
        ["api-case", "generate-create", PROJECT_ID, DEFINITION_ID],
        recorder.base_url)
    assert proc.returncode == 0, "stderr=%s" % proc.stderr
    assert recorder.create_bodies, "没有用例创建成功：%s / %s" % (proc.stdout, proc.stderr)
    for body in recorder.create_bodies:
        assert "tags" not in body, (
            "未传 --tags 却出现了 tags 键：%r" % body.get("tags"))
    # 关键词形态也不许凭空造 tags
    for body in recorder.bodies_for(r"^/api/api/testcase/list/"):
        assert "tags" not in json.loads(body)


def test_generate_create_keeps_id_and_priority_defaults(recorder):
    """--tags 不能挤掉既有的 id/priority 注入。"""
    proc = run_ms_sh(
        ["api-case", "generate-create", "--tags", "T-x", PROJECT_ID, DEFINITION_ID],
        recorder.base_url)
    assert proc.returncode == 0, "stderr=%s" % proc.stderr
    assert recorder.create_bodies
    for body in recorder.create_bodies:
        assert is_uuid4(body["id"]), "生成载荷缺 uuid4 id：%r" % body.get("id")
        assert body["priority"] == "P1"


def test_generate_create_tags_does_not_leak_into_import_paths(recorder, tmp_path):
    """--tags 只能影响 generate-create：import-create 走的是同一批用例载荷但不得带 tags。"""
    spec = tmp_path / "openapi.json"
    spec.write_text(json.dumps({
        "openapi": "3.0.0", "info": {"title": "t", "version": "1"},
        "paths": {"/api/books/{id}": {"get": {
            "operationId": "getBookById", "parameters": [
                {"name": "id", "in": "path", "required": True,
                 "schema": {"type": "string"}}]}}},
    }), encoding="utf-8")
    proc = run_ms_sh(
        ["api", "import-create", PROJECT_ID, str(spec)],
        recorder.base_url)
    assert proc.returncode in (0, 1), "stderr=%s" % proc.stderr
    for body in recorder.create_bodies:
        assert "tags" not in body, "import-create 载荷被污染进 tags：%r" % body


# --------------------------------------------------------------------------
# 畸形输入（--tags 的边界）
# --------------------------------------------------------------------------

def test_tags_without_value_hijacks_project_id_into_a_tag(recorder):
    """--tags 后面紧跟 projectId：**命令会成功**，projectId 被吃成标签、定义 id 被顶成 projectId。

    旧注释断言"没有 projectId → 必须报错"，**与实测相反**。ms.sh 的真实推导：
      - 1264-1266 建 ``api_case_tags_raw`` / ``api_case_args`` 两个数组；
      - 1272-1276 的 ``--tags`` 分支**无条件**把 ``$2`` 收成标签值（1274 ``+=("$2")`` + 1275 ``shift 2``），
        1273 的 ``[[ $# -ge 2 ]]`` 只能挡"--tags 是最后一个参数"，挡不住"后继值其实是位置参数"；
      - 于是本例 ``PROJECT_ID`` 进标签，``api_case_args`` 只剩 ``(DEFINITION_ID)``；
      - 1303 ``project_id="${api_case_args[0]:-${METERSPHERE_PROJECT_ID:-}}"`` 取到 **DEFINITION_ID**
        （非空），1304 的守卫因此放行 → 定义列表与后续写入全部瞄向"拿定义 id 当项目 id"。

    这里钉的是**可观察事实**（成功退出 + projectId 被劫持 + PROJECT_ID 降级成标签），
    没有任何 ``if <被测条件>`` 式的对冲分支，故不存在空过。
    """
    proc = run_ms_sh(
        ["api-case", "generate-create", "--tags", PROJECT_ID, DEFINITION_ID],
        recorder.base_url)
    assert proc.returncode == 0, (
        "实测该形态是成功退出；若 ms.sh 行为已变更请同步改写本用例：rc=%s stderr=%s"
        % (proc.returncode, proc.stderr))
    assert "错误" not in proc.stderr, "意外报错：%s" % proc.stderr

    # 可观察证据 1：ms.sh 自己打印的"项目"就是被顶替后的 DEFINITION_ID（ms.sh:632）。
    assert "共发现 1 个接口定义（项目 %s）" % DEFINITION_ID in proc.stdout, (
        "ms.sh 打印的项目不是被劫持的 DEFINITION_ID：%s" % proc.stdout)

    # 可观察证据 2：定义列表请求的 projectId 是 DEFINITION_ID，而不是调用方给的 PROJECT_ID。
    list_bodies = recorder.bodies_for(r"^/api/api/definition/list/")
    assert list_bodies, "定义列表请求未发生：%s / %s" % (proc.stdout, proc.stderr)
    listed = json.loads(list_bodies[-1])
    assert listed["projectId"] == DEFINITION_ID, (
        "projectId 未被 --tags 劫持成 DEFINITION_ID（实际 %r）" % listed["projectId"])
    assert listed["projectId"] != PROJECT_ID, (
        "定义列表竟然仍用调用方给的 projectId：%r" % listed["projectId"])

    # 可观察证据 3：确实写出了用例，且每条都带着被降级成标签的 PROJECT_ID。
    assert recorder.create_bodies, "没有用例创建成功：%s / %s" % (proc.stdout, proc.stderr)
    for body in recorder.create_bodies:
        assert json.loads(body["tags"]) == [PROJECT_ID], (
            "PROJECT_ID 没有被降级成标签：%r" % body.get("tags"))
        assert body["apiDefinitionId"] == DEFINITION_ID, (
            "用例挂到了非预期的定义上：%r" % body.get("apiDefinitionId"))


def test_tags_at_end_of_arguments_fails(recorder):
    """--tags 是最后一个参数（真·没有后继值）：必须以中文错误退出。"""
    proc = run_ms_sh(
        ["api-case", "generate-create", PROJECT_ID, "--tags"],
        recorder.base_url)
    assert proc.returncode != 0, "缺标签值竟然成功了：%s" % proc.stdout
    assert "tags" in proc.stderr and "错误" in proc.stderr, (
        "缺标签值的报错必须是中文且点名 --tags：%s" % proc.stderr)
    assert not recorder.create_bodies, "报错前竟然写入了用例"


def test_tags_empty_value_fails(recorder):
    """--tags '' （空值）：必须以中文错误退出，且一个请求都不许发出去。

    实测：1272-1276 的 ``--tags`` 分支先 ``+=("$2")`` + ``shift 2``，空串被收成唯一标签值；
    1273 的 ``[[ $# -ge 2 ]]`` 在此**不触发**（``$#`` 仍为 4，判据是"有没有后继值"而非"值是否为空"）；
    真正拦它的是 1288-1298 的归一化 python 里 ``if not tags: sys.exit(1)``（1295-1296），
    外层 1299-1301 的 ``die``（1300）打出中文报错。
    """
    proc = run_ms_sh(
        ["api-case", "generate-create", "--tags", "", PROJECT_ID, DEFINITION_ID],
        recorder.base_url)
    assert proc.returncode == 1, (
        "空标签值本该报错退出（exit 1），却成功了：stdout=%s stderr=%s"
        % (proc.stdout, proc.stderr))
    assert "错误" in proc.stderr, "报错必须是中文：%s" % proc.stderr
    assert "--tags" in proc.stderr, "报错必须点名 --tags：%s" % proc.stderr
    assert "标签" in proc.stderr, "报错必须点明标签非法：%s" % proc.stderr
    # 报错发生在任何网络动作之前：既不能列定义，更不能创建用例。
    assert not recorder.requests, "报错前竟然发起了请求：%r" % (recorder.requests,)
    assert not recorder.create_bodies, "报错前竟然写入了用例：%r" % (recorder.create_bodies,)


def test_tags_only_separators_fails(recorder):
    """--tags ',,' （只有分隔符没有实际标签）：不得生成 "[]"。"""
    proc = run_ms_sh(
        ["api-case", "generate-create", "--tags", ",,", PROJECT_ID, DEFINITION_ID],
        recorder.base_url)
    for body in recorder.create_bodies:
        raw = body.get("tags")
        assert raw is None or json.loads(raw), "生成了空标签：%r" % raw


def test_tags_help_still_prints_usage(recorder):
    """--tags 与 --help 混排时仍走 usage（flag 剥离不能吞掉帮助）。"""
    proc = run_ms_sh(
        ["api-case", "generate-create", "--tags", "T-a", "--help"], recorder.base_url)
    assert proc.returncode == 0, "stderr=%s" % proc.stderr
    assert "用法" in proc.stdout
    assert not recorder.create_bodies


def test_unknown_flag_is_not_mistaken_for_tags(recorder):
    """未知 flag 不得被当成标签来源：它只能落回位置参数，不许凭空生成 tags。"""
    proc = run_ms_sh(
        ["api-case", "generate-create", "--nope", "T-x", PROJECT_ID, DEFINITION_ID],
        recorder.base_url)
    for body in recorder.create_bodies:
        assert "tags" not in body, (
            "未知 flag --nope 竟被当成标签来源：%r" % body.get("tags"))
    if proc.returncode == 0:
        assert not any("tags" in json.loads(b) for b in recorder.bodies_for(
            r"^/api/api/definition/list/"))


# --------------------------------------------------------------------------
# 计划禁项
# --------------------------------------------------------------------------

def test_no_api_case_update_verb_exists():
    """计划禁止 api-case update：不许新增该 verb（--help 里也不许出现）。"""
    usage = subprocess.run(["bash", MS_SH, "help"],
                           capture_output=True, text=True, timeout=60).stdout
    assert "api-case update" not in usage
    proc = subprocess.run(["bash", MS_SH, "api-case", "update", "{}"],
                          capture_output=True, text=True, timeout=60)
    assert proc.returncode != 0
    assert "不支持的 action" in proc.stderr, proc.stderr


def test_v1_scripts_untouched_by_tags_and_injection():
    """G1/G2 只属于 v2：v1 的 ms.sh 不得出现本次新增的 flag/注入文案。"""
    v1 = os.path.join(REPO_ROOT, "skills", "scripts", "ms.sh")
    with open(v1, encoding="utf-8") as fh:
        text = fh.read()
    assert "--tags" not in text, "v1 ms.sh 不该有 --tags"
    assert "generate_create_api_cases" not in text, "v1 ms.sh 不该有 v2 私有函数"


# --------------------------------------------------------------------------
# 新增：api-case create 的 request 校验（fail-fast）
# --------------------------------------------------------------------------

def test_create_rejects_missing_request(recorder):
    """payload 无 request 时必须拒绝，且不发出 HTTP 请求"""
    proc = run_ms_sh(
        ["api-case", "create",
         json.dumps({"name": "缺request", "apiDefinitionId": "api-1"})],
        recorder.base_url)
    assert proc.returncode != 0
    assert "request" in proc.stderr
    assert "generate-create" in proc.stderr
    assert len(recorder.requests) == 0


def test_create_rejects_null_request(recorder):
    """request 为 null 时必须拒绝"""
    proc = run_ms_sh(
        ["api-case", "create",
         json.dumps({"name": "null-request", "apiDefinitionId": "api-1", "request": None})],
        recorder.base_url)
    assert proc.returncode != 0
    assert "request" in proc.stderr
    assert len(recorder.requests) == 0


def test_create_rejects_empty_string_request(recorder):
    """request 为空字符串时必须拒绝"""
    proc = run_ms_sh(
        ["api-case", "create",
         json.dumps({"name": "empty-request", "apiDefinitionId": "api-1", "request": ""})],
        recorder.base_url)
    assert proc.returncode != 0
    assert "request" in proc.stderr
    assert len(recorder.requests) == 0


def test_create_rejects_empty_dict_request(recorder):
    """request 为空 dict 时也应拒绝（无效）"""
    proc = run_ms_sh(
        ["api-case", "create",
         json.dumps({"name": "empty-dict-request", "apiDefinitionId": "api-1", "request": {}})],
        recorder.base_url)
    assert proc.returncode != 0
    assert "request" in proc.stderr
    assert len(recorder.requests) == 0


def test_create_accepts_valid_request(recorder):
    """payload 带有效 request 时应正常通过"""
    proc = run_ms_sh(
        ["api-case", "create",
         json.dumps({"name": "有效request", "apiDefinitionId": "api-1",
                     "request": {"method": "GET", "url": "http://x/y", "headers": [], "body": {}}})],
        recorder.base_url)
    assert proc.returncode == 0
    assert len(recorder.create_bodies) >= 1
