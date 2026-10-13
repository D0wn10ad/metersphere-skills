"""Structural characterization tests for the MeterSphere import .xlsx fixtures.

Two fixtures are asserted here (copied verbatim from the real-world import pair,
never modified):

* ``import_case_bad_layout.xlsx``  -- the ORIGINAL (bad) workbook: inline strings,
  no merged cells, no shared-string table.
* ``import_case_documented.xlsx``  -- the REFORMATTED (documented) workbook:
  shared strings + merged cells.

Both describe the same 40 data rows / 11 columns and share the identical header
row. The xlsx container is opened with the stdlib ``zipfile`` + XML parsing so the
test carries **no third-party dependency**.

These tests are intentionally structural (they characterize the layout difference
that the importer must tolerate) rather than value checks on every cell.
"""

from __future__ import annotations

import posixpath
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

import pytest

FIXTURES = Path(__file__).resolve().parent / "fixtures"
BAD = FIXTURES / "import_case_bad_layout.xlsx"
DOCUMENTED = FIXTURES / "import_case_documented.xlsx"

# Order matters: this is the exact header row both fixtures carry.
EXPECTED_HEADERS = [
    "Name",
    "Module",
    "Tag",
    "Prerequisite",
    "Step description",
    "Step result",
    "Edit Model",
    "Remark",
    "Case status",
    "Maintainer",
    "Priority",
]

MAIN_NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
REL_NS = "http://schemas.openxmlformats.org/package/2006/relationships"
OFFICE_REL_NS = (
    "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
)

Q = f"{{{MAIN_NS}}}"


# --------------------------------------------------------------------------- #
# helpers
# --------------------------------------------------------------------------- #
def _normalize_zip_target(target: str) -> str:
    """Resolve an OPC relationship target to an archive member path."""
    target = target.lstrip("/")
    # A relationship may point outside xl/ using ../; collapse it safely.
    normalized = posixpath.normpath(posixpath.join("xl/_rels", target))
    return normalized.lstrip("./")


def first_sheet_path(zf: zipfile.ZipFile) -> str:
    """Locate the first worksheet's XML member, robustly.

    Primary path: parse ``xl/workbook.xml`` for the first ``<sheet>`` element,
    follow its ``r:id`` through ``xl/_rels/workbook.xml.rels``. Falls back to the
    conventional ``xl/worksheets/sheet1.xml`` if anything is missing.
    """
    try:
        workbook = ET.fromstring(zf.read("xl/workbook.xml"))
        sheet = workbook.find(f"{Q}sheets/{Q}sheet")
        if sheet is not None:
            rid = sheet.get(f"{{{OFFICE_REL_NS}}}id")
            rels = ET.fromstring(zf.read("xl/_rels/workbook.xml.rels"))
            for rel in rels.findall(f"{{{REL_NS}}}Relationship"):
                if rel.get("Id") == rid:
                    path = _normalize_zip_target(rel.get("Target", ""))
                    if path in zf.namelist():
                        return path
    except (KeyError, ET.ParseError, AttributeError):
        pass
    return "xl/worksheets/sheet1.xml"


def sheet_xml(zf: zipfile.ZipFile, path: str | None = None) -> str:
    return zf.read(path or first_sheet_path(zf)).decode("utf-8")


def _shared_strings(zf: zipfile.ZipFile) -> list[str]:
    """Return the shared-string table (rich runs flattened), or [] if absent."""
    if "xl/sharedStrings.xml" not in zf.namelist():
        return []
    sst = ET.fromstring(zf.read("xl/sharedStrings.xml"))
    out: list[str] = []
    for si in sst.findall(f"{Q}si"):
        out.append("".join(t.text or "" for t in si.iter(f"{Q}t")))
    return out


def _cell_text(cell: ET.Element, shared: list[str]) -> str:
    """Resolve a cell's display text from inline strings, shared strings, or v."""
    ctype = cell.get("t")
    if ctype == "inlineStr":
        return "".join(t.text or "" for t in cell.iter(f"{Q}t"))
    if ctype == "s":
        v = cell.find(f"{Q}v")
        if v is not None and v.text is not None:
            return shared[int(v.text)]
        return ""
    v = cell.find(f"{Q}v")
    return v.text or "" if v is not None else ""


def header_cells(zf: zipfile.ZipFile) -> list[str]:
    """Return the text of the cells in row 1 (the header row)."""
    root = ET.fromstring(sheet_xml(zf))
    sheet_data = root.find(f"{Q}sheetData")
    assert sheet_data is not None, "worksheet has no <sheetData>"
    first_row = sheet_data.find(f"{Q}row")
    assert first_row is not None, "worksheet has no rows"
    shared = _shared_strings(zf)
    return [_cell_text(c, shared) for c in first_row.findall(f"{Q}c")]


# --------------------------------------------------------------------------- #
# 1. fixtures exist and open as zip archives
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("fixture", [BAD, DOCUMENTED], ids=["bad", "documented"])
def test_fixture_exists_and_is_zip(fixture: Path) -> None:
    assert fixture.is_file(), f"missing fixture: {fixture}"
    assert zipfile.is_zipfile(fixture), f"not a zip archive: {fixture}"
    with zipfile.ZipFile(fixture) as zf:
        assert "xl/worksheets/sheet1.xml" in zf.namelist() or first_sheet_path(zf)


# --------------------------------------------------------------------------- #
# 2. both fixtures carry the same 11 header cells
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("fixture", [BAD, DOCUMENTED], ids=["bad", "documented"])
def test_header_row_matches_expected(fixture: Path) -> None:
    with zipfile.ZipFile(fixture) as zf:
        assert header_cells(zf) == EXPECTED_HEADERS


def test_headers_are_identical_between_fixtures() -> None:
    with zipfile.ZipFile(BAD) as bad, zipfile.ZipFile(DOCUMENTED) as doc:
        assert header_cells(bad) == header_cells(doc)


# --------------------------------------------------------------------------- #
# 3. merged cells: absent in bad, present in documented
# --------------------------------------------------------------------------- #
def test_bad_layout_has_no_merged_cells() -> None:
    with zipfile.ZipFile(BAD) as zf:
        xml = sheet_xml(zf)
    assert "<mergeCells" not in xml


def test_documented_layout_has_merged_cells() -> None:
    with zipfile.ZipFile(DOCUMENTED) as zf:
        xml = sheet_xml(zf)
    assert "<mergeCells" in xml


# --------------------------------------------------------------------------- #
# 4. string storage: inline in bad, shared in documented
# --------------------------------------------------------------------------- #
def test_bad_layout_uses_inline_strings() -> None:
    with zipfile.ZipFile(BAD) as zf:
        xml = sheet_xml(zf)
        assert 't="inlineStr"' in xml
        assert "xl/sharedStrings.xml" not in zf.namelist()


def test_documented_layout_uses_shared_strings() -> None:
    with zipfile.ZipFile(DOCUMENTED) as zf:
        names = zf.namelist()
        assert "xl/sharedStrings.xml" in names
        assert 't="s"' in sheet_xml(zf)
