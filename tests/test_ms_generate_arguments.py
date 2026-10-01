#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""v1 生成器（skills/scripts/ms_generate.py）的 `arguments` 参数组扫描测试。

背景：MeterSphere 的接口定义 request 载荷里，路径/查询参数可能存放在
`arguments` 字段而不是 `query`（v2 线尤为明显，见 README §8.6 覆盖说明）。
v1 生成器原先只扫描 `query` / `rest`，因此仅存在于 `arguments` 的定义只会
得到「成功场景」一个变体。本文件锁定修复后的期望行为。
"""
import copy
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'skills' / 'scripts'))

import ms_generate  # noqa: E402


MINIMAL_SPEC = {
    'openapi': '3.0.0',
    'info': {'title': 't', 'version': '1'},
    'paths': {
        '/test': {
            'get': {
                'summary': '测试接口',
                'parameters': [
                    {'name': 'token', 'in': 'query', 'required': True,
                     'schema': {'type': 'string'}},
                ],
                'responses': {'200': {'description': 'ok'}},
            }
        }
    },
}


def _entry(key='token', required=True, param_type='string'):
    """构造一个 MeterSphere 风格的参数条目（与 build_http_request 产出形状一致）。"""
    return {
        'key': key,
        'value': 'test',
        'enable': True,
        'description': None,
        'paramType': param_type,
        'required': required,
        'minLength': None,
        'maxLength': None,
        'encode': False,
    }


def _request_with_arguments(entries=None):
    """构造仅在 `arguments` 中携带参数的 request（模拟定义详情回读）。"""
    req = ms_generate.build_http_request(
        'get', '/test', '测试接口', MINIMAL_SPEC['paths']['/test']['get'],
    )
    # build_http_request 会把 in:query 放进 query；这里模拟「参数存于 arguments」的形态
    req['query'] = []
    req['rest'] = []
    if entries is not None:
        req['arguments'] = entries
    return req


@pytest.fixture
def api_import_with_request(monkeypatch):
    """让 build_openapi_import 收到一个由调用方指定 request 的接口定义。"""
    captured = {}

    def _factory(request_obj):
        def fake_build_http_request(method, path, summary, operation):
            captured['req'] = request_obj
            return copy.deepcopy(request_obj)

        monkeypatch.setattr(ms_generate, 'build_http_request', fake_build_http_request)

        def run():
            captured.clear()
            return ms_generate.build_openapi_import(
                'p1', 'm1', __import__('json').dumps(MINIMAL_SPEC),
            )

        return run

    return _factory


# --------------------------------------------------------------------------
# 基线特征测试：记录修复前的可观测行为（arguments-only -> 仅 1 个变体）
# --------------------------------------------------------------------------

# --------------------------------------------------------------------------
# 基线对照与修复后的期望行为（fail-first）
# --------------------------------------------------------------------------

def test_baseline_query_only_produces_three_scenarios(api_import_with_request):
    """基线对照：仅 query 有参数时 3 个变体（该路径修复前后均正常）。"""
    req = _request_with_arguments([])
    req['query'] = [_entry()]
    cases = api_import_with_request(req)()['cases'][0]
    assert len(cases) == 3
    assert [c['name'].split('-')[-1] for c in cases] == ['成功场景', '必填缺失', '边界场景']


def test_arguments_only_produces_three_scenarios(api_import_with_request):
    """FIXED：仅 arguments 有必填参数时必须生成全部 3 个变体。"""
    cases = api_import_with_request(_request_with_arguments([_entry()]))()['cases'][0]
    assert len(cases) == 3
    assert [c['name'].split('-')[-1] for c in cases] == ['成功场景', '必填缺失', '边界场景']


def test_arguments_required_is_blanked_in_missing_variant(api_import_with_request):
    """FIXED：「必填缺失」变体必须把 arguments 中的必填参数置空。"""
    cases = api_import_with_request(_request_with_arguments([_entry()]))()['cases'][0]
    miss = next(c for c in cases if c['name'].endswith('-必填缺失'))
    assert miss['request']['arguments'][0]['value'] == ''


def test_arguments_string_param_is_padded_in_edge_variant(api_import_with_request):
    """FIXED：「边界场景」变体必须把 arguments 中的 string 参数填成 128 个字符。"""
    cases = api_import_with_request(_request_with_arguments([_entry()]))()['cases'][0]
    edge = next(c for c in cases if c['name'].endswith('-边界场景'))
    assert edge['request']['arguments'][0]['value'] == 'X' * 128


def test_each_group_gets_one_blanked_entry(api_import_with_request):
    """v1 既有语义：`break` 在内层循环，故每组各置空一个必填项，而非全局首个。"""
    req = _request_with_arguments([_entry(key='from-args')])
    req['query'] = [_entry(key='from-query')]
    cases = api_import_with_request(req)()['cases'][0]
    miss = next(c for c in cases if c['name'].endswith('-必填缺失'))
    assert miss['request']['query'][0]['value'] == ''
    assert miss['request']['arguments'][0]['value'] == ''


def test_arguments_group_absent_still_yields_three_for_query():
    """arguments 键完全缺失时行为不变（query-only 回归保护）。"""
    req = ms_generate.build_http_request(
        'get', '/test', '测试接口', MINIMAL_SPEC['paths']['/test']['get'],
    )
    assert 'arguments' not in req
    cases = ms_generate.build_case_variants_for_api('测试接口', req, True, True)
    assert len(cases) == 3


# --------------------------------------------------------------------------
# 健壮性：arguments 的畸形取值不得导致崩溃（adversarial: malformed_input）
# --------------------------------------------------------------------------

@pytest.mark.parametrize('bad_value', [None, {}, 'not-a-list', 0, []])
def test_arguments_malformed_group_does_not_crash(api_import_with_request, bad_value):
    """FIXED + 健壮性：arguments 为 None/字典/字符串/数字/空列表时不得抛异常。"""
    req = _request_with_arguments(None)
    req['arguments'] = bad_value
    result = api_import_with_request(req)()
    assert result['cases']  # 至少产出成功场景


@pytest.mark.parametrize('bad_entry', [
    {},                                   # 缺 name / 缺 required / 缺 paramType
    {'name': None, 'type': None},         # 显式 null
    {'required': True},                   # 只有必填标记，无 paramType
    {'paramType': 'string'},              # 只有类型，无 required
])
def test_arguments_malformed_entry_does_not_crash(api_import_with_request, bad_entry):
    """FIXED + 健壮性：arguments 条目缺 name / type 为 null 时不得抛异常。"""
    cases = api_import_with_request(_request_with_arguments([bad_entry]))()['cases'][0]
    assert len(cases) >= 1
    assert cases[0]['name'].endswith('-成功场景')


def test_arguments_with_non_dict_entries_does_not_crash(api_import_with_request):
    """FIXED + 健壮性：arguments 里混入非 dict 条目时不得抛 AttributeError。"""
    cases = api_import_with_request(
        _request_with_arguments(['oops', 42, None, _entry()]),
    )()['cases'][0]
    assert len(cases) == 3