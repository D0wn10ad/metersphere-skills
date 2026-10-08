# -*- coding: utf-8 -*-
"""import_stub_server.py 的可复用 harness 用例。

分两组：
1. 特征化（characterization）——钉住 stub **既有**可观察行为，任何改动都不许破坏：
   紧凑 JSON、health 端点、`"success":true` 字面量、既有 `testcase_list_500` 注入模式、
   以及"手工用 --state/--port 独立跑"的可用性。
2. 新增故障注入模式——为后续 ms.sh shell 行为回归准备的 api-case create 失败/回显路径。

全程只用回环 127.0.0.1，不需要任何凭据、不读 .env、不走外网。
"""
import json
import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from conftest import (  # noqa: E402
    StubServer,
    find_free_port,
    http_request,
    port_is_closed,
    spawn_stub_server,
    terminate_stub_server,
)

STUB_SCRIPT = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                           "import_stub_server.py")

# 模拟 ms.sh L842-846 的 curl -F "request=@file;type=application/json" 报文
MULTIPART_BOUNDARY = "----stubtestboundary"


def multipart_request_field(payload, name="request"):
    """构造 curl -F 形态的 multipart 报文（stub 侧是纯正则扫描，不做解析）。"""
    return (
        "--%s\r\n"
        'Content-Disposition: form-data; name="%s"; filename="tmp.json"\r\n'
        "Content-Type: application/json\r\n"
        "\r\n"
        "%s\r\n"
        "--%s--\r\n" % (MULTIPART_BOUNDARY, name, payload, MULTIPART_BOUNDARY)
    )


# --------------------------------------------------------------------------
# 1. 特征化：钉住既有行为（这些用例在 stub 未改动时就必须绿）
# --------------------------------------------------------------------------

def test_standalone_cli_still_runnable(tmp_path):
    """手工用法必须原样可用：python3 import_stub_server.py --state X --port N。"""
    state_path = str(tmp_path / "standalone_state.json")
    port = find_free_port()
    proc = subprocess.Popen(
        [sys.executable, STUB_SCRIPT, "--state", state_path, "--port", str(port)],
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    handle = StubServer(proc, port, state_path, None, None)
    try:
        from conftest import wait_until_serving
        wait_until_serving(port, proc)
        status, text = handle.request("GET", "/")
        assert status == 200
        # 逐字比对：证明紧凑 JSON（无空格分隔）——ms.sh 的 grep 依赖这一点
        assert text == '{"ok":true}'
        assert json.loads(text) == {"ok": True}
        # --state 指向的文件必须被创建出来（空映射起步）
        assert os.path.exists(state_path)
        assert json.loads(open(state_path, encoding="utf-8").read())["names"] == {}
    finally:
        terminate_stub_server(handle)


def test_json_is_compact_so_ms_sh_grep_succeeds(stub_server):
    """ms.sh 用 `grep -q '"success":true'` 判定成功 → 必须是无空格紧凑 JSON。"""
    payload = '{"name":"compact-check","priority":"P0"}'
    status, text = stub_server.request(
        "POST", "/api/api/testcase/create",
        body=multipart_request_field(payload),
        headers={"Content-Type": "multipart/form-data; boundary=%s" % MULTIPART_BOUNDARY})
    assert status == 200
    # 字面量必须逐字命中，且不得出现 ", " / ": " 之类的分隔空格
    assert '"success":true' in text
    assert '", "' not in text and '": ' not in text


def test_import_route_returns_persisted_id_on_first_import(stub_server):
    """既有语义：首次导入返回的 id 恰为持久化 id（ms.sh 依赖它做 GET 校验）。"""
    body = multipart_request_field(
        '{"paths":[{"operationId":"getUserById","method":"GET"}]}')
    status, text = stub_server.request(
        "POST", "/api/api/definition/import",
        body=body,
        headers={"Content-Type": "multipart/form-data; boundary=%s" % MULTIPART_BOUNDARY})
    assert status == 200
    payload = json.loads(text)
    def_id = payload["data"]["data"][0]["id"]
    assert def_id == "persist-1"

    status, text = stub_server.request("GET", "/api/api/definition/get/%s" % def_id)
    assert status == 200
    detail = json.loads(text)["data"]
    assert detail is not None
    assert detail["name"] == "getUserById"


def test_unknown_definition_id_returns_data_null(stub_server):
    """既有语义：未持久化的 id → {"success":true,"data":null}（重复导入缺陷核心）。"""
    status, text = stub_server.request("GET", "/api/api/definition/get/fresh-9")
    assert status == 200
    assert json.loads(text) == {"success": True, "data": None}


def test_existing_fail_mode_testcase_list_500_is_unchanged(stub_server):
    """既有故障注入模式必须逐字保持：只有 testcase/list 回 500，其余路由照常 200。"""
    stub_server.set_fail_mode("testcase_list_500")
    status, text = stub_server.request(
        "POST", "/api/api/testcase/list/1/10", body='{"apiDefinitionId":"persist-1"}')
    assert status == 500
    assert json.loads(text) == {"error": "injected failure: testcase_list_500"}

    # 同模式下 create 路由必须仍然 200 —— 老模式绝不能溢出到别的路由
    status, _ = stub_server.request(
        "POST", "/api/api/testcase/create",
        body=multipart_request_field('{"name":"still-ok","priority":"P1"}'),
        headers={"Content-Type": "multipart/form-data; boundary=%s" % MULTIPART_BOUNDARY})
    assert status == 200

    # 清掉模式后 list 恢复 200
    stub_server.clear_fail_mode()
    status, text = stub_server.request(
        "POST", "/api/api/testcase/list/1/10", body='{"apiDefinitionId":"persist-1"}')
    assert status == 200
    assert json.loads(text)["success"] is True


# --------------------------------------------------------------------------
# 2. 新增故障注入模式（api-case create 专用）
# --------------------------------------------------------------------------

def test_new_mode_api_case_create_500_affects_only_create_route(stub_server):
    """新模式 api_case_create_500：只有 api-case create 回 500，其它路由不受影响。"""
    stub_server.set_fail_mode("api_case_create_500")

    status, text = stub_server.request(
        "POST", "/api/api/testcase/create",
        body=multipart_request_field('{"name":"boom","priority":"P0"}'),
        headers={"Content-Type": "multipart/form-data; boundary=%s" % MULTIPART_BOUNDARY})
    assert status == 500
    assert json.loads(text) == {"error": "injected failure: api_case_create_500"}

    # 非 create 路由必须全部 200
    for method, path, body in (
        ("GET", "/", None),
        ("GET", "/api/api/definition/get/persist-1", None),
        ("POST", "/api/api/definition/list/1/10", "{}"),
        ("POST", "/api/api/testcase/list/1/10", '{"apiDefinitionId":"persist-1"}'),
    ):
        status, _ = stub_server.request(method, path, body=body)
        assert status == 200, "%s %s 应保持 200，实际 %d" % (method, path, status)

    # 失败不应把 case 写进状态（不产生副作用）
    assert stub_server.read_state()["cases"] == []


def test_new_mode_create_body_echo_rejects_missing_id_or_priority(stub_server):
    """新模式 create_body_echo：缺 id/priority 的 create body 会被拒，且回显收到的报文。"""
    stub_server.set_fail_mode("create_body_echo")

    status, text = stub_server.request(
        "POST", "/api/api/testcase/create",
        body=multipart_request_field('{"name":"missing-both"}'),
        headers={"Content-Type": "multipart/form-data; boundary=%s" % MULTIPART_BOUNDARY})
    assert status == 400
    payload = json.loads(text)
    assert payload["success"] is False
    assert sorted(payload["missing"]) == ["id", "priority"]
    # 必须回显收到的请求体，测试才能对"服务端到底看见了什么"下断言
    assert payload["received"] == {"name": "missing-both"}

    # 只缺 priority
    status, text = stub_server.request(
        "POST", "/api/api/testcase/create",
        body=multipart_request_field('{"id":"api-1","name":"missing-priority"}'),
        headers={"Content-Type": "multipart/form-data; boundary=%s" % MULTIPART_BOUNDARY})
    assert status == 400
    assert json.loads(text)["missing"] == ["priority"]

    # 只缺 id
    status, text = stub_server.request(
        "POST", "/api/api/testcase/create",
        body=multipart_request_field('{"name":"missing-id","priority":"P2"}'),
        headers={"Content-Type": "multipart/form-data; boundary=%s" % MULTIPART_BOUNDARY})
    assert status == 400
    assert json.loads(text)["missing"] == ["id"]

    # 字段齐全 → 200 且同样回显
    status, text = stub_server.request(
        "POST", "/api/api/testcase/create",
        body=multipart_request_field(
            '{"id":"api-1","name":"complete","priority":"P0"}'),
        headers={"Content-Type": "multipart/form-data; boundary=%s" % MULTIPART_BOUNDARY})
    assert status == 200
    payload = json.loads(text)
    assert payload["success"] is True
    assert re.match(r"^mock-\d+$", payload["data"]["id"])
    assert payload["received"] == {"id": "api-1", "name": "complete", "priority": "P0"}


# --------------------------------------------------------------------------
# 3. harness 自身的可复用性 / 隔离性
# --------------------------------------------------------------------------

def test_fixture_uses_ephemeral_port_not_hardcoded_18082(stub_server):
    """端口必须每次临时分配：跑满 3 次互不相同，且都不是硬编码的 18082。"""
    ports = []
    for _ in range(3):
        handle = spawn_stub_server(
            state_path=os.path.join(
                str(stub_server.state_path).rsplit("/", 1)[0], "state-%d.json" % len(ports)),
            fail_path=stub_server.fail_path)
        try:
            assert handle.port != 18082
            ports.append(handle.port)
            status, _ = handle.request("GET", "/")
            assert status == 200
        finally:
            terminate_stub_server(handle)
    assert len(set(ports)) == 3, "端口重复：%r" % ports
    assert all(port_is_closed(p) for p in ports)


def test_no_state_leaks_between_runs(stub_server, tmp_path):
    """同名重复导入在两个"独立 run"里必须各自从零起步（tmp_path 隔离）。"""
    body = multipart_request_field(
        '{"paths":[{"operationId":"listOrders","method":"GET"}]}')
    headers = {"Content-Type": "multipart/form-data; boundary=%s" % MULTIPART_BOUNDARY}

    def one_run(handle):
        status, text = handle.request(
            "POST", "/api/api/definition/import", body=body, headers=headers)
        assert status == 200
        return json.loads(text)["data"]["data"][0]["id"]

    first = one_run(stub_server)
    second = one_run(stub_server)
    assert first == "persist-1"
    assert second == "fresh-1", (
        "同一次 run 内重复导入必须返回未持久化的 fresh id（既有缺陷语义）")

    # 新的一次 run（自带 state 文件）必须重新从 persist-1 起步 —— 无状态泄漏
    fresh = spawn_stub_server(
        state_path=str(tmp_path / "second_run_state.json"),
        fail_path=str(tmp_path / "second_run_fail.json"))
    try:
        assert one_run(fresh) == "persist-1"
        assert fresh.read_state()["names"] == {"listOrders": "persist-1"}
        assert fresh.read_state()["fresh_counter"] == 0
    finally:
        terminate_stub_server(fresh)

    # 顺带确认本 run 的故障注入文件也在 tmp_path 内
    assert stub_server.fail_path.startswith(str(tmp_path))
    assert stub_server.state_path.startswith(str(tmp_path))


def test_teardown_kills_child_and_frees_port(stub_server):
    """teardown 必须真的杀掉子进程并释放端口——这里显式自证一次。"""
    port = stub_server.port
    proc = stub_server.proc
    assert proc.poll() is None, "用例执行期间 stub 应仍在运行"
    assert not port_is_closed(port)

    terminate_stub_server(stub_server)

    assert proc.poll() is not None
    assert port_is_closed(port), "端口 %d 未释放" % port


def test_malformed_body_does_not_crash_server(stub_server):
    """畸形/空 body 打到 create 路由：不得崩服务，且返回受控响应。"""
    headers = {"Content-Type": "multipart/form-data; boundary=%s" % MULTIPART_BOUNDARY}
    for bad_body in ("", "not json at all", "{", "\x00\x01binary"):
        status, text = stub_server.request(
            "POST", "/api/api/testcase/create", body=bad_body, headers=headers)
        assert status == 200, "畸形 body 应返回受控响应，实际 %d" % status
        assert json.loads(text)["success"] is True

    # 未知路由 404，服务仍存活
    status, _ = stub_server.request("POST", "/api/api/nope")
    assert status == 404
    status, text = stub_server.request("GET", "/")
    assert status == 200