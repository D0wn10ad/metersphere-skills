#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""v2 生成器（skills/scripts/v2/ms_generate.py）module_id 可选行为测试。

背景（plan Todo 1 / Scope Must-have #1）：v2 `ms_generate.py` 的三个位置参数
均声明为 `nargs='?'`，但守卫要求 module_id 必填，导致「省略模块」无法表达。
修复后约定：

- 恰好 2 个位置参数 ⇒ 视为省略 module_id，按「projectId requirement-file」
  解释，并输出占位对 `nodeId == "default-module"` + `nodePath == "/default-module"`
  （该占位对刻意触发 v2/ms.sh 的 need_resolve 检测器，再被替换为真实的
  每项目「未规划用例」节点）。
- 3 个位置参数 ⇒ 行为不变（moduleId 原样使用，nodePath = "/" + moduleId）。
- 1 个 / 0 个位置参数 ⇒ 仍以 zh-CN USAGE 退出 1。

注意：不能简单 `import ms_generate` —— 同一 pytest 进程中
tests/test_ms_generate_arguments.py 会先把 v1 的 ms_generate 放进 sys.modules
（按模块名缓存），导致这里拿到 v1（签名不同）。因此用 importlib 按文件路径
以唯一模块名加载 v2 文件。
"""
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
V2_SCRIPT = REPO_ROOT / 'skills' / 'scripts' / 'v2' / 'ms_generate.py'

_spec = importlib.util.spec_from_file_location('ms_generate_v2_under_test', V2_SCRIPT)
ms_generate = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ms_generate)


@pytest.fixture
def req_file(tmp_path):
    p = tmp_path / 'req.md'
    p.write_text('- 用户使用正确密码登录系统\n', encoding='utf-8')
    return p


def _run(*argv):
    return subprocess.run(
        [sys.executable, str(V2_SCRIPT), *map(str, argv)],
        capture_output=True, text=True,
    )


# --------------------------------------------------------------------------
# 单元层：build_functional_cases 对空 module_id 输出占位对
# --------------------------------------------------------------------------

def test_build_empty_module_emits_default_module_sentinel(req_file):
    """空 module_id ⇒ 每个元素 nodeId=default-module 且 nodePath=/default-module。"""
    cases = ms_generate.build_functional_cases(
        'PROJ1', '', req_file.read_text(encoding='utf-8'),
    )
    assert cases, '至少应产出一个用例元素'
    for c in cases:
        assert c['nodeId'] == 'default-module'
        assert c['nodePath'] == '/default-module'


def test_build_real_module_keeps_module_id(req_file):
    """3 位置参数语义不变：nodeId=MOD1，nodePath=/MOD1。"""
    cases = ms_generate.build_functional_cases(
        'PROJ1', 'MOD1', req_file.read_text(encoding='utf-8'),
    )
    assert cases
    for c in cases:
        assert c['nodeId'] == 'MOD1'
        assert c['nodePath'] == '/MOD1'


# --------------------------------------------------------------------------
# CLI 层：子进程实跑（与验收标准 (1)(2)(3) 同口径）
# --------------------------------------------------------------------------

def test_cli_two_positionals_emit_sentinel(req_file):
    """AC(1)：2 位置参数 ⇒ 全部元素 default-module 占位对。"""
    r = _run('functional-cases', 'PROJ1', req_file)
    assert r.returncode == 0, f'stdout={r.stdout}\nstderr={r.stderr}'
    cases = json.loads(r.stdout)
    assert cases
    for c in cases:
        assert c['nodeId'] == 'default-module'
        assert c['nodePath'] == '/default-module'


def test_cli_three_positionals_keep_module(req_file):
    """AC(2)：3 位置参数 ⇒ MOD1 / /MOD1。"""
    r = _run('functional-cases', 'PROJ1', 'MOD1', req_file)
    assert r.returncode == 0, f'stdout={r.stdout}\nstderr={r.stderr}'
    cases = json.loads(r.stdout)
    assert cases
    for c in cases:
        assert c['nodeId'] == 'MOD1'
        assert c['nodePath'] == '/MOD1'


def test_cli_one_positional_dies_with_usage(req_file):
    """AC(3)：1 位置参数 ⇒ 退出 1，zh-CN USAGE（module_id 交换后 requirement_file 缺失）。"""
    r = _run('functional-cases', req_file)
    assert r.returncode == 1, f'stdout={r.stdout}\nstderr={r.stderr}'
    assert '用法' in r.stderr
    assert 'requirement-file' in r.stderr


def test_cli_zero_positionals_dies_with_usage():
    """0 位置参数 ⇒ 退出 1，zh-CN USAGE。"""
    r = _run('functional-cases')
    assert r.returncode == 1, f'stdout={r.stdout}\nstderr={r.stderr}'
    assert '用法' in r.stderr


def test_cli_bad_action_dies():
    """畸形 action ⇒ zh-CN 报错退出 1。"""
    r = _run('bogus-action')
    assert r.returncode == 1
    assert '不支持的 action' in r.stderr
