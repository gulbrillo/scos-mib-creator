"""Consistency audits: the registry must be self-consistent, and everything
the tool generates itself (bootstrap starter content) must validate cleanly
under the strict ESA profile — the tool must never produce findings about
its own output."""

from app.bootstrap import _CVS, _PCDF, _PCPC, PUS_HEADER_ID
from mibschema import get_registry, validate_project


def test_registry_lint():
    reg = get_registry()
    problems = []
    for t in reg.tables.values():
        for c in t.columns:
            if c.default is not None:
                if c.length and len(c.default) > c.length:
                    problems.append(f"{t.name}.{c.name}: default longer than field")
                if c.enum and c.enum_strict and c.default not in [e.value for e in c.enum]:
                    problems.append(f"{t.name}.{c.name}: default {c.default!r} not in enum")
            if c.enum:
                for e in c.enum:
                    if c.length and len(e.value) > c.length:
                        problems.append(f"{t.name}.{c.name}: enum value {e.value!r} too long")
            if c.mandatory and not (c.hint or c.help):
                problems.append(f"{t.name}.{c.name}: mandatory but no hint/help")
    assert problems == []


def test_bootstrap_content_strictly_valid():
    rows = {
        "vdf": [{"VDF_NAME": "TESTPROJ", "VDF_COMMENT": "Created with SCOS MIB Creator",
                 "VDF_DOMAINID": "", "VDF_RELEASE": "0", "VDF_ISSUE": "1"}],
        "tcp": [{"TCP_ID": PUS_HEADER_ID, "TCP_DESC": "Standard PUS TC header"}],
        "pcpc": _PCPC,
        "pcdf": [{"PCDF_TCNAME": PUS_HEADER_ID, "PCDF_DESC": d, "PCDF_TYPE": ft,
                  "PCDF_LEN": str(length), "PCDF_BIT": str(bit), "PCDF_PNAME": pn,
                  "PCDF_VALUE": v, "PCDF_RADIX": "D"}
                 for d, ft, length, bit, pn, v in _PCDF],
        "cvs": _CVS,
    }
    findings = [f for f in validate_project(rows, "scos-7.0")
                if f.severity in ("error", "warning")]
    assert findings == [], [f"{f.table}.{f.column}: {f.message}" for f in findings]


def test_pcdf_header_layout_is_contiguous():
    """The starter TC header must cover bits 0..71 without gaps or overlaps."""
    fields = sorted(_PCDF, key=lambda f: f[3])
    cursor = 0
    for _desc, _ftype, length, bit, _pname, _value in fields:
        assert bit == cursor, f"gap/overlap at bit {cursor}"
        cursor += length
    assert cursor == 72  # 6-byte CCSDS primary + 3-byte PUS secondary header
