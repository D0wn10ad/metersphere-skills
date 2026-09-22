#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""有状态 stub 服务器：模拟 MeterSphere v2 网关（/{serviceId}/** 剥离首段 + 服务 context /api），
用于 import-create 重复导入幂等修复的 RED→GREEN 回归测试。

语义契约（与 .omo/plans/skill-v2-import-create-fix.md T1 一致）：
- POST /api/api/definition/import：multipart 不解析，正则扫 operationId；
  drift- 保留名 → 永远返回 fresh-<k> 且不入映射（单次运行即复现「name 未匹配、回退响应 id、GET data:null」）；
  name 已在映射 → 返回 fresh-<k>（重复导入缺陷模拟：响应 id 未持久化）；
  name 不在映射 → persist-<len+1> 入映射（首次导入：响应 id 恰为持久化 id）；
  响应嵌套 {"success":true,"data":{"data":[{id,name,method}]}}（ms.sh L784 解析 data.data[]）。
- POST /api/api/definition/list/{goPage}/{pageSize}：listObject [{id,name,method}] + pageCount；
  pageSize<2 且 >1 条时强制分页 pageCount=2（多页路径，非阻塞覆盖项）。
- GET /api/api/definition/get/{id}：id ∈ 映射值 → 完整 detail（request:{}）；否则 {"success":true,"data":null}。
- POST /api/api/testcase/list/{goPage}/{pageSize}：fail_mode=="testcase_list_500" → HTTP 500；
  按 apiDefinitionId 过滤 cases → listObject 用例名。
- POST /api/api/testcase/create：**multipart 正则提取** apiDefinitionId/name（testcase/create 是
  multipart/form-data，ms.sh L842-846 -F "request=@..."）；记录 case；
  返回 {"success":true,"data":{"id":"mock-<n>"}}（ms.sh L848-859 从 data 解析 case_id）。

用法：python3 import_stub_server.py --state /tmp/opencode/import_stub_state.json [--port 18082]
健康检查：GET / → 200。收尾：kill 进程。
"""
import argparse
import json
import re
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

LOCK = threading.Lock()


def load_state(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {"names": {}, "cases": [], "fresh_counter": 0, "mock_counter": 0}


def save_state(path, state):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def fail_mode():
    try:
        with open("/tmp/opencode/import_stub_fail.json", "r", encoding="utf-8") as f:
            return json.load(f).get("mode", "")
    except (FileNotFoundError, json.JSONDecodeError):
        return ""


class StubHandler(BaseHTTPRequestHandler):
    state_path = "/tmp/opencode/import_stub_state.json"

    def log_message(self, fmt, *args):
        pass  # 静默，日志走 nohup 重定向

    def _send(self, code, payload):
        # 紧凑 JSON（separators 无空格）——真实 MeterSphere 服务器返回 {"success":true,...}，
        # ms.sh L781 grep -q '"success":true' 依赖无空格格式
        body = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _read_body(self):
        length = int(self.headers.get("Content-Length", 0))
        return self.rfile.read(length).decode("utf-8", errors="replace") if length else ""

    def do_GET(self):
        if self.path == "/":
            self._send(200, {"ok": True})
            return
        # GET /api/api/definition/get/{id}
        m = re.match(r"^/api/api/definition/get/([^/?]+)", self.path)
        if m:
            def_id = m.group(1)
            with LOCK:
                state = load_state(self.state_path)
                persisted = {v: k for k, v in state["names"].items()}
            if def_id in persisted:
                self._send(200, {"success": True, "data": {
                    "id": def_id, "name": persisted[def_id], "method": "GET",
                    "path": "/stub", "request": {}}})
            else:
                # 未持久化 id（fresh-* 或未知）→ data:null（重复导入缺陷核心）
                self._send(200, {"success": True, "data": None})
            return
        self._send(404, {"error": "not found: %s" % self.path})

    def do_POST(self):
        body = self._read_body()
        # POST /api/api/definition/import（multipart，不解析，正则扫 operationId）
        if self.path == "/api/api/definition/import":
            m = re.search(r'"operationId"\s*:\s*"([^"]*)"', body)
            name = m.group(1) if m else "Unknown endpoint"
            with LOCK:
                state = load_state(self.state_path)
                if name.startswith("drift-"):
                    # 保留名：永远 fresh，不入映射（name 未匹配复现）
                    state["fresh_counter"] += 1
                    def_id = "fresh-%d" % state["fresh_counter"]
                elif name in state["names"]:
                    # 重复导入缺陷模拟：返回未持久化的 fresh id
                    state["fresh_counter"] += 1
                    def_id = "fresh-%d" % state["fresh_counter"]
                else:
                    # 首次导入：persist id 入映射（响应 id 恰为持久化 id）
                    def_id = "persist-%d" % (len(state["names"]) + 1)
                    state["names"][name] = def_id
                save_state(self.state_path, state)
            self._send(200, {"success": True, "data": {"data": [
                {"id": def_id, "name": name, "method": "GET"}]}})
            return
        # POST /api/api/definition/list/{goPage}/{pageSize}
        m = re.match(r"^/api/api/definition/list/(\d+)/(\d+)", self.path)
        if m:
            go_page, page_size = int(m.group(1)), int(m.group(2))
            with LOCK:
                state = load_state(self.state_path)
                items = [{"id": did, "name": nm, "method": "GET"}
                         for nm, did in sorted(state["names"].items())]
            # 多页路径（非阻塞覆盖项）：pageSize<2 且 >1 条时强制 pageCount=2
            if page_size < 2 and len(items) > 1:
                page = items[(go_page - 1):go_page] if go_page <= len(items) else []
                self._send(200, {"success": True, "data": {
                    "listObject": page, "pageCount": len(items), "itemCount": len(items)}})
                return
            self._send(200, {"success": True, "data": {
                "listObject": items, "pageCount": 1, "itemCount": len(items)}})
            return
        # POST /api/api/testcase/list/{goPage}/{pageSize}
        m = re.match(r"^/api/api/testcase/list/(\d+)/(\d+)", self.path)
        if m:
            if fail_mode() == "testcase_list_500":
                self._send(500, {"error": "injected failure: testcase_list_500"})
                return
            try:
                req = json.loads(body)
            except json.JSONDecodeError:
                req = {}
            api_def_id = req.get("apiDefinitionId", "")
            with LOCK:
                state = load_state(self.state_path)
                names = [c["name"] for c in state["cases"]
                         if c.get("apiDefinitionId") == api_def_id]
            self._send(200, {"success": True, "data": {
                "listObject": [{"name": n} for n in names],
                "pageCount": 1, "itemCount": len(names)}})
            return
        # POST /api/api/testcase/create（multipart 正则提取 apiDefinitionId/name）
        if self.path == "/api/api/testcase/create":
            m_id = re.search(r'"apiDefinitionId"\s*:\s*"([^"]*)"', body)
            m_name = re.search(r'"name"\s*:\s*"([^"]*)"', body)
            api_def_id = m_id.group(1) if m_id else ""
            case_name = m_name.group(1) if m_name else ""
            with LOCK:
                state = load_state(self.state_path)
                state["mock_counter"] += 1
                case_id = "mock-%d" % state["mock_counter"]
                state["cases"].append({
                    "id": case_id, "name": case_name,
                    "apiDefinitionId": api_def_id})
                save_state(self.state_path, state)
            self._send(200, {"success": True, "data": {"id": case_id}})
            return
        self._send(404, {"error": "not found: %s" % self.path})


def main():
    parser = argparse.ArgumentParser(description="MeterSphere import-create 幂等回归 stub")
    parser.add_argument("--state", default="/tmp/opencode/import_stub_state.json")
    parser.add_argument("--port", type=int, default=18082)
    args = parser.parse_args()
    StubHandler.state_path = args.state
    # 启动前确保状态文件存在（空映射起步，不预置——预置与 RED 断言 run1 EXIT0 自相矛盾）
    save_state(args.state, load_state(args.state))
    server = ThreadingHTTPServer(("127.0.0.1", args.port), StubHandler)
    print("stub listening on 127.0.0.1:%d state=%s" % (args.port, args.state), flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
