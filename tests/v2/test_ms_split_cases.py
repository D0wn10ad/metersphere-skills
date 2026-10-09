# -*- coding: utf-8 -*-
"""skills/scripts/v2/ms_split_cases.py 拆分器回归（todo 4）。

钉住四件事：

1. **G1 —— 四种格式的拆分语义。**
   xlsx 按 MeterSphere 导入模板列序（TestCaseImportFiled：用例名称→所属模块→标签→
   前置条件→步骤描述→预期结果→编辑模式→备注→用例等级）；xmind 按 v2.10
   ``XmindCaseParser`` 语义（``tc:``/``tc-P1:`` 用例节点、``pc:``/``rc:``/``tag:``
   子节点、非 tc 节点累积模块路径）；docx 标题层级+表格；pdf 行式启发。

2. **G2 —— 缺富依赖优雅降级。**
   xlsx/docx/pdf 缺依赖时报错必须含安装提示（``pip install <pkg>``）；
   xmind 走 stdlib zipfile+json，无富依赖。

3. **G3 —— 缺关键列/关键节点跳过并告警计数。**
   每条草稿必含 name/nodePath/priority/steps；缺关键列的行跳过且 stderr 有告警。

4. **G4 —— 输出 v2 字段契约。**
   禁 v3-only 字段（moduleId/customNum/maintainer/customFields/aiCreate）；
   tags 为 JSON 数组字符串（服务端契约）。

fixture 文件在 tests/v2/fixtures/（sample.xlsx/xmind/docx/pdf），随仓库分发；
全程不调用网络；报错全 zh-CN。
"""
import json
import subprocess
import sys
from importlib import import_module
from pathlib import Path

import pytest

TESTS_DIR = Path(__file__).resolve().parent
REPO_ROOT = TESTS_DIR.parent.parent
SPLITTER = REPO_ROOT / "skills" / "scripts" / "v2" / "ms_split_cases.py"
FIXTURES = TESTS_DIR / "fixtures"

V3_ONLY_FIELDS = ("moduleId", "customNum", "maintainer", "customFields", "aiCreate")


def run_splitter(*args):
    return subprocess.run(
        [sys.executable, str(SPLITTER)] + list(args),
        cwd=REPO_ROOT, capture_output=True, text=True, timeout=120)


def load_drafts(proc):
    return json.loads(proc.stdout)


# --------------------------------------------------------------------------
# G1: 四种格式的拆分语义
# --------------------------------------------------------------------------

def test_split_xlsx_fixture_template_columns():
    """xlsx：模板列序解析，多行步骤合并，tags 为 JSON 数组字符串。"""
    proc = run_splitter(str(FIXTURES / "sample.xlsx"))
    assert proc.returncode == 0, "stderr=%s" % proc.stderr
    drafts = load_drafts(proc)
    assert len(drafts) == 2, "应拆出 2 条用例（缺名行告警跳过）：%s" % drafts
    first = drafts[0]
    assert first["name"] == "登录成功"
    assert first["nodePath"] == "默认模块/登录"
    assert first["priority"] == "P1"
    assert first["caseEditType"] == "STEP"
    assert first["precondition"] == "用户已注册"
    assert first["tags"] == '["冒烟", "登录"]'
    assert [s["desc"] for s in first["steps"]] == ["输入正确密码", "点击登录按钮"]
    assert first["steps"][0] == {"num": 1, "desc": "输入正确密码", "result": "跳转首页"}
    second = drafts[1]
    assert second["name"] == "登录失败"
    assert second["priority"] == "P2"
    assert second["remark"] == "连续 5 次锁定"


def test_split_xmind_fixture_tc_p1_priority():
    """xmind：tc-P1 前缀 → priority=P1；pc:/rc:/tag: 子节点；模块路径累积。"""
    proc = run_splitter(str(FIXTURES / "sample.xmind"))
    assert proc.returncode == 0, "stderr=%s" % proc.stderr
    drafts = load_drafts(proc)
    assert len(drafts) == 2, "应拆出 2 条用例（tc 空名节点告警跳过）：%s" % drafts
    first = drafts[0]
    assert first["name"] == "登录成功"
    assert first["priority"] == "P1", "tc-P1 前缀必须解析为 P1：%r" % first["priority"]
    assert first["nodePath"] == "/登录模块"
    assert first["precondition"] == "用户已注册"
    assert first["tags"] == '["冒烟", "登录"]'
    assert first["steps"] == [{"num": 1, "desc": "输入正确密码", "result": "跳转首页"}]
    second = drafts[1]
    assert second["name"] == "登录失败"
    assert second["priority"] == "P0"
    assert second["remark"] == "连续 5 次锁定"
    assert second["steps"] == [{"num": 1, "desc": "输入错误密码", "result": "提示错误"}]


def test_split_docx_fixture_headings_and_table():
    """docx：Heading 1 → 模块路径、Heading 3 → 用例（tc 前缀剥离）、表格 → 步骤。"""
    proc = run_splitter(str(FIXTURES / "sample.docx"))
    assert proc.returncode == 0, "stderr=%s" % proc.stderr
    drafts = load_drafts(proc)
    assert len(drafts) == 2
    first = drafts[0]
    assert first["name"] == "登录成功"
    assert first["nodePath"] == "/登录模块"
    assert first["precondition"] == "用户已注册"
    assert [s["desc"] for s in first["steps"]] == ["输入正确密码", "点击登录按钮"]
    assert first["steps"][0]["result"] == "跳转首页"
    second = drafts[1]
    assert second["name"] == "登录失败", "tc-P2 前缀必须剥离：%r" % second["name"]
    assert second["priority"] == "P2"
    assert second["remark"] == "连续 5 次锁定"


def test_split_pdf_fixture_line_heuristics():
    """pdf：markdown 式标题 → 模块路径、tc:/tc-P1: 行 → 用例、其余行 → 步骤。"""
    proc = run_splitter(str(FIXTURES / "sample.pdf"))
    assert proc.returncode == 0, "stderr=%s" % proc.stderr
    drafts = load_drafts(proc)
    assert len(drafts) == 2
    first = drafts[0]
    assert first["name"] == "login success"
    assert first["nodePath"] == "/Login Module"
    assert first["priority"] == "P0"
    assert [s["desc"] for s in first["steps"]] == ["enter correct password",
                                                   "expect redirect to home"]
    second = drafts[1]
    assert second["name"] == "login failure lockout"
    assert second["priority"] == "P1"


def test_format_auto_infers_by_extension():
    """--format auto（默认）按扩展名推断四种格式。"""
    for fmt in ("xlsx", "xmind", "docx", "pdf"):
        drafts = split_file_safe(FIXTURES / ("sample." + fmt))
        assert len(drafts) == 2, "%s auto 推断失败：%s" % (fmt, drafts)


def split_file_safe(path):
    from importlib import import_module
    sys.path.insert(0, str(SPLITTER.parent))
    try:
        mod = import_module("ms_split_cases")
        return mod.split_file(str(path), "auto")
    finally:
        sys.path.pop(0)


# --------------------------------------------------------------------------
# G2: 缺富依赖优雅降级
# --------------------------------------------------------------------------

@pytest.mark.parametrize("fmt,pip_name", [("xlsx", "openpyxl"),
                                          ("docx", "python-docx"),
                                          ("pdf", "pdfplumber")])
def test_missing_rich_dep_error_contains_install_hint(monkeypatch, fmt, pip_name):
    """缺富依赖时报错含安装提示（pip install <pkg>），不发网络请求。"""
    import builtins
    real_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name == pip_name or name == RICH_MODULE[fmt]:
            raise ImportError("No module named '%s'" % name)
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    sys.path.insert(0, str(SPLITTER.parent))
    try:
        mod = import_module("ms_split_cases")
        with pytest.raises(ValueError) as exc:
            mod.split_file(str(FIXTURES / ("sample." + fmt)), fmt)
        assert "pip install %s" % pip_name in str(exc.value), (
            "%s 缺依赖报错缺安装提示：%s" % (fmt, exc.value))
    finally:
        sys.path.pop(0)


RICH_MODULE = {"xlsx": "openpyxl", "docx": "docx", "pdf": "pdfplumber"}


def test_xmind_needs_no_rich_deps(monkeypatch):
    """xmind 走 stdlib zipfile+json：屏蔽全部富依赖仍可解析。"""
    import builtins
    real_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name in ("openpyxl", "docx", "pdfplumber"):
            raise ImportError("No module named '%s'" % name)
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    sys.path.insert(0, str(SPLITTER.parent))
    try:
        mod = import_module("ms_split_cases")
        drafts = mod.split_file(str(FIXTURES / "sample.xmind"), "xmind")
        assert len(drafts) == 2
    finally:
        sys.path.pop(0)


# --------------------------------------------------------------------------
# G3: 缺关键列/关键节点跳过并告警计数
# --------------------------------------------------------------------------

def test_xlsx_missing_name_row_warns_with_count():
    """有内容但缺用例名称的行跳过，stderr 有告警计数。"""
    proc = run_splitter(str(FIXTURES / "sample.xlsx"))
    assert proc.returncode == 0
    assert "跳过 1 条草稿" in proc.stderr, "stderr=%s" % proc.stderr
    assert "共跳过 1 条草稿" in proc.stderr


def test_xmind_empty_tc_node_warns():
    """tc 前缀但用例名为空的节点跳过并告警。"""
    proc = run_splitter(str(FIXTURES / "sample.xmind"))
    assert proc.returncode == 0
    assert "tc 前缀但用例名为空" in proc.stderr, "stderr=%s" % proc.stderr


# --------------------------------------------------------------------------
# G4: 输出 v2 字段契约 + CLI 行为
# --------------------------------------------------------------------------

@pytest.mark.parametrize("fmt", ["xlsx", "xmind", "docx", "pdf"])
def test_no_v3_only_fields_in_output(fmt):
    """输出禁 v3-only 字段（moduleId/customNum/maintainer/customFields/aiCreate）。"""
    proc = run_splitter(str(FIXTURES / ("sample." + fmt)))
    assert proc.returncode == 0, "stderr=%s" % proc.stderr
    for draft in load_drafts(proc):
        for field in V3_ONLY_FIELDS:
            assert field not in draft, (
                "%s 输出了 v3-only 字段 %s：%r" % (fmt, field, draft))


def test_cli_json_output_valid():
    """CLI stdout 输出合法 JSON 数组（验收命令原样）。"""
    proc = run_splitter(str(FIXTURES / "sample.xlsx"))
    assert proc.returncode == 0, "stderr=%s" % proc.stderr
    drafts = json.loads(proc.stdout)
    assert isinstance(drafts, list) and len(drafts) == 2


def test_cli_out_file_writes_json():
    """-o 写 JSON 文件并输出「已拆分」计数清单。"""
    out = FIXTURES / "_split_out_tmp.json"
    try:
        proc = run_splitter(str(FIXTURES / "sample.xmind"), "-o", str(out))
        assert proc.returncode == 0, "stderr=%s" % proc.stderr
        assert "已拆分 2 条草稿" in proc.stdout
        drafts = json.loads(out.read_text(encoding="utf-8"))
        assert len(drafts) == 2
    finally:
        out.unlink(missing_ok=True)


def test_cli_project_id_injection():
    """--project-id 注入每条草稿的 projectId。"""
    proc = run_splitter(str(FIXTURES / "sample.xlsx"),
                        "--project-id", "proj-split-1")
    assert proc.returncode == 0, "stderr=%s" % proc.stderr
    for draft in load_drafts(proc):
        assert draft["projectId"] == "proj-split-1"


def test_unknown_extension_error_mentions_format_flag():
    """无法按扩展名识别时报错提示 --format。"""
    proc = run_splitter(str(FIXTURES / "definition_get_c6e4293e.json"))
    assert proc.returncode != 0
    assert "--format" in proc.stderr, "stderr=%s" % proc.stderr


def test_missing_file_error():
    """文件不存在时报错（zh-CN）。"""
    proc = run_splitter(str(FIXTURES / "no-such.xlsx"))
    assert proc.returncode != 0
    assert "文件不存在" in proc.stderr, "stderr=%s" % proc.stderr
