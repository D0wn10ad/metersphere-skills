# -*- coding: utf-8 -*-
"""pytest 夹具：把 tests/v2/import_stub_server.py 变成可复用的 MeterSphere v2 网关替身。

存在的理由：import_stub_server.py 原本只能手工跑（``--state``/``--port``），
没有任何自动化用例消费它，于是 ``skills/scripts/v2/ms.sh`` 的 shell 行为无法回归。
本模块把它包成 fixture，后续 todo 即可对着一个"活的"（本地回环）假服务器跑端到端断言。

设计约束（勿破坏）：
- 端口由内核临时分配（bind 0 探测），绝不硬编码 18082 —— 重复运行/并行运行不互相踩踏。
- 状态文件与故障注入文件全部落在 pytest 的 tmp_path 下，函数级作用域 → 运行间零状态泄漏。
- 仅回环 127.0.0.1；不读 .env、不需要任何凭据、无外网出口。
- teardown 必须"证明"子进程真的死了，且端口不再接受连接（而不是假定）。
"""
import json
import os
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request

import pytest

TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
STUB_SCRIPT = os.path.join(TESTS_DIR, "import_stub_server.py")

READY_TIMEOUT_S = 20.0
READY_INTERVAL_S = 0.05
TEARDOWN_TIMEOUT_S = 5.0
SPAWN_ATTEMPTS = 5


def find_free_port():
    """向内核要一个当前空闲的回环端口（bind 0 由内核分配），返回端口号。"""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])
    finally:
        sock.close()


def port_is_closed(port):
    """True 表示该端口已不再接受连接（= 服务器确实没了，而非仅靠进程判断）。"""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.settimeout(0.5)
        return sock.connect_ex(("127.0.0.1", port)) != 0
    finally:
        sock.close()


def wait_until_serving(port, proc, timeout=READY_TIMEOUT_S):
    """轮询 GET / 直到服务真的接受连接；子进程提前退出必须立刻炸出来。"""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if proc.poll() is not None:
            raise RuntimeError("stub 子进程提前退出（returncode=%s）" % proc.returncode)
        try:
            with urllib.request.urlopen("http://127.0.0.1:%d/" % port, timeout=0.5) as resp:
                if resp.status == 200:
                    return
        except (urllib.error.URLError, OSError):
            time.sleep(READY_INTERVAL_S)
    raise RuntimeError("stub 在 %.1fs 内未就绪（port=%d）" % (timeout, port))


def http_request(port, method, path, body=None, headers=None, timeout=10.0):
    """发一个回环请求，返回 (status, raw_text)。

    连 4xx/5xx 也照实返回状态码与原始报文 —— 测试要断言的就是这些原始可观察量。
    """
    if isinstance(body, str):
        body = body.encode("utf-8")
    req = urllib.request.Request(
        "http://127.0.0.1:%d%s" % (port, path),
        data=body,
        method=method,
        headers=headers or {},
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read().decode("utf-8", errors="replace")


class StubServer(object):
    """已拉起的 stub 句柄：基址 + 故障注入开关 + 状态读取 + 子进程引用。"""

    def __init__(self, proc, port, state_path, fail_path, log_path):
        self.proc = proc
        self.port = port
        self.base_url = "http://127.0.0.1:%d" % port
        self.state_path = state_path
        self.fail_path = fail_path
        self.log_path = log_path

    def __str__(self):
        return self.base_url

    def request(self, method, path, body=None, headers=None):
        """便捷包装：直接对本 stub 发请求，拿 (status, raw_text)。"""
        return http_request(self.port, method, path, body=body, headers=headers)

    def set_fail_mode(self, mode):
        """切换故障注入模式。stub 在每次请求时现读该文件，故可中途切换。"""
        with open(self.fail_path, "w", encoding="utf-8") as fh:
            json.dump({"mode": mode}, fh, ensure_ascii=False)

    def clear_fail_mode(self):
        self.set_fail_mode("")

    def read_state(self):
        with open(self.state_path, encoding="utf-8") as fh:
            return json.load(fh)

    def read_log(self):
        try:
            with open(self.log_path, encoding="utf-8", errors="replace") as fh:
                return fh.read()
        except FileNotFoundError:
            return ""


def _terminate(proc, timeout=TEARDOWN_TIMEOUT_S):
    """停掉子进程（先 terminate 再 kill），返回 True 表示确实已退出。"""
    if proc.poll() is not None:
        return True
    proc.terminate()
    try:
        proc.wait(timeout=timeout)
        return True
    except subprocess.TimeoutExpired:
        proc.kill()
        try:
            proc.wait(timeout=timeout)
            return True
        except subprocess.TimeoutExpired:
            return False


def spawn_stub_server(state_path, fail_path=None, port=None, log_path=None):
    """以子进程方式拉起 stub，返回正在运行的 StubServer。

    端口探测 → 启动 → 就绪等待 → 若期间端口被抢占（bind 失败）则换一个端口重试，
    消除"探测端口"与"子进程 bind"之间的竞态。
    """
    last_error = None
    for _ in range(SPAWN_ATTEMPTS):
        chosen = port if port is not None else find_free_port()
        assert port_is_closed(chosen), "端口 %d 在启动前已被占用" % chosen
        cmd = [sys.executable, STUB_SCRIPT, "--state", state_path,
               "--port", str(chosen)]
        if fail_path is not None:
            cmd += ["--fail", fail_path]
        if log_path:
            log_fh = open(log_path, "ab")
        else:
            log_fh = None
        try:
            proc = subprocess.Popen(
                cmd, stdout=log_fh or subprocess.DEVNULL,
                stderr=subprocess.STDOUT,
            )
        finally:
            if log_fh is not None:
                log_fh.close()
        try:
            wait_until_serving(chosen, proc)
            return StubServer(proc, chosen, state_path, fail_path, log_path)
        except RuntimeError as exc:
            # 启动失败必须不留孤儿：先杀掉，再决定是重试还是放弃。
            _terminate(proc)
            last_error = exc
            if port is not None:
                raise
    raise AssertionError("stub 连续 %d 次启动失败：%s" % (SPAWN_ATTEMPTS, last_error))


def terminate_stub_server(handle):
    """teardown：终止子进程，并断言进程已消失且端口已关闭。"""
    proc = handle.proc
    stopped = _terminate(proc)
    assert stopped, "stub 子进程 pid=%s 未响应 terminate/kill" % proc.pid
    assert proc.poll() is not None, "stub 子进程 pid=%s 仍在运行" % proc.pid
    assert port_is_closed(handle.port), (
        "端口 %d 仍在接受连接：stub 服务器泄漏（pid=%s）" % (handle.port, proc.pid))


@pytest.fixture
def stub_server(tmp_path):
    """函数级 stub：每次用例独享端口 + 状态文件 + 故障注入文件。"""
    state_path = str(tmp_path / "stub_state.json")
    fail_path = str(tmp_path / "stub_fail.json")
    log_path = str(tmp_path / "stub.log")
    handle = spawn_stub_server(state_path, fail_path=fail_path, log_path=log_path)
    try:
        yield handle
    finally:
        terminate_stub_server(handle)


@pytest.fixture
def stub_base_url(stub_server):
    """只要基址字符串的用例用这个。"""
    return stub_server.base_url