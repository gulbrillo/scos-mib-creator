"""MIB engine tests: registry sanity, parser/generator round trip, validator."""

from mibschema import (generate_table_file, get_registry, parse_table_file,
                       validate_project)
from mibschema.generator import generate_mib_zip
from mibschema.parser import parse_mib_zip
from mibschema.pus.types import bit_width
from mibschema.registry import PROFILES


def synthetic_row(table, n: int) -> dict:
    """Build a plausible row for any table: unique-ish keys, valid enums."""
    row = {}
    for col in table.columns:
        if col.enum:
            row[col.name] = col.enum[0].value
        elif col.type == "number":
            row[col.name] = str(n)
        else:
            row[col.name] = f"V{n}"[: col.length or 8]
    return row


def test_registry_loads():
    reg = get_registry()
    assert len(reg.tables) >= 40
    for t in reg.tables.values():
        assert t.columns, t.name
        assert t.key_columns or t.name in ("psv",), f"{t.name} has no key columns"
        for c in t.columns:
            assert c.type in ("char", "number"), f"{t.name}.{c.name}"


def test_round_trip_every_table():
    reg = get_registry()
    for profile in PROFILES:
        for t in reg.tables.values():
            rows = [synthetic_row(t, i) for i in range(3)]
            text = generate_table_file(t, rows, profile)
            parsed, issues = parse_table_file(t, text)
            assert not [i for i in issues if i.severity == "error"]
            # restrict comparison to the profile's columns (others come back empty)
            for orig, back in zip(rows, parsed):
                for c in t.columns_for_profile(profile):
                    assert back[c.name] == orig[c.name], f"{t.name}.{c.name} ({profile})"


def test_zip_round_trip():
    reg = get_registry()
    tables = {t.name: [synthetic_row(t, i) for i in range(2)] for t in reg.tables.values()}
    blob = generate_mib_zip(tables, profile="ccs5")
    parsed, issues = parse_mib_zip(blob)
    assert not [i for i in issues if i.severity == "error"]
    assert set(parsed) == set(tables)
    blob2 = generate_mib_zip(parsed, profile="ccs5")
    parsed2, _ = parse_mib_zip(blob2)
    assert parsed2 == parsed


def test_parser_tolerates_missing_trailing_fields():
    reg = get_registry()
    pcf = reg.table("pcf")
    # ICD: trailing optional fields may be omitted (19-field PCF records)
    line = "\t".join(["P1", "desc", "", "", "3", "12"] + [""] * 13)
    rows, issues = parse_table_file(pcf, line + "\n")
    assert rows[0]["PCF_NAME"] == "P1"
    assert rows[0]["PCF_ENDIAN"] == ""  # absent trailing column -> empty
    assert not issues


def test_parser_preserves_extra_fields():
    reg = get_registry()
    vdf = reg.table("vdf")
    rows, issues = parse_table_file(vdf, "NAME\tcmt\t\t0\t1\tEXTRA1\tEXTRA2\n")
    assert rows[0]["__extra__"] == ["EXTRA1", "EXTRA2"]
    assert any(i.severity == "warning" for i in issues)
    out = generate_table_file(vdf, rows, "scos-7.0")
    assert out.rstrip("\n").endswith("EXTRA1\tEXTRA2")


def test_validator_field_checks():
    findings = validate_project({"pcf": [
        {"PCF_NAME": "", "PCF_PTC": "3", "PCF_PFC": "12", "PCF_CATEG": "N",
         "PCF_NATUR": "R"},                                        # missing name
        {"PCF_NAME": "TOOLONGNAME99", "PCF_PTC": "x", "PCF_PFC": "12",
         "PCF_CATEG": "Z", "PCF_NATUR": "R"},                      # long, NaN, bad enum
    ]}, profile="scos-7.0")
    codes = {f.code for f in findings}
    assert {"mandatory", "length", "number-format", "enum"} <= codes


def test_validator_lengths_are_warnings_on_ccs5():
    rows = {"pcf": [{"PCF_NAME": "TOOLONGNAME99", "PCF_PTC": "3", "PCF_PFC": "12",
                     "PCF_CATEG": "N", "PCF_NATUR": "R"}]}
    strict = [f for f in validate_project(rows, "scos-7.0") if f.code == "length"]
    loose = [f for f in validate_project(rows, "ccs5") if f.code == "length"]
    assert strict[0].severity == "error"
    assert loose[0].severity == "warning"


def test_validator_fk_and_duplicates():
    findings = validate_project({
        "caf": [{"CAF_NUMBR": "CAL1", "CAF_ENGFMT": "R", "CAF_RAWFMT": "U",
                 "CAF_NCURVE": "5"}],
        "cap": [{"CAP_NUMBR": "CAL1", "CAP_XVALS": "0", "CAP_YVALS": "0"},
                {"CAP_NUMBR": "CAL1", "CAP_XVALS": "0", "CAP_YVALS": "1"},  # dup key
                {"CAP_NUMBR": "NOPE", "CAP_XVALS": "1", "CAP_YVALS": "1"}],  # bad fk
    })
    codes = {f.code for f in findings}
    assert {"fk", "duplicate-key", "count-mismatch"} <= codes


def test_validator_semantics():
    findings = validate_project({
        "pid": [{"PID_TYPE": "3", "PID_STYPE": "25", "PID_APID": "100",
                 "PID_PI1_VAL": "1", "PID_SPID": "1000", "PID_DFHSIZE": "10"}],
        "pcf": [{"PCF_NAME": "STAT1", "PCF_PTC": "2", "PCF_PFC": "8",
                 "PCF_CATEG": "S", "PCF_NATUR": "R", "PCF_CURTX": "MISSING"}],
    })
    codes = {f.code for f in findings}
    assert "pic-missing" in codes        # PI1 used without pic record
    assert "calib-missing" in codes      # status calib does not exist


def test_bit_width():
    assert bit_width(3, 4) == 8
    assert bit_width(3, 12) == 16
    assert bit_width(3, 14) == 32
    assert bit_width(4, 12) == 16
    assert bit_width(5, 1) == 32
    assert bit_width(5, 2) == 64
    assert bit_width(2, 12) == 12
    assert bit_width(7, 4) == 32
    assert bit_width(9, 18) == 56
    assert bit_width(7, 0) is None   # variable length
    assert bit_width(99, 0) is None
