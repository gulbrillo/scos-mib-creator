"""Validation engine for MIB projects.

Produces human-readable findings (with fix hints) instead of hard failures:
a MIB under construction is allowed to be temporarily inconsistent.

Three layers of checks:
1. Field level   — mandatory, format, length, enumeration, pattern.
2. Referential   — declared foreign keys (registry 'fk') + key uniqueness.
3. MIB semantics — count consistency (e.g. CAF_NCURVE vs cap rows),
                   conditional requirements and completeness advice.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, asdict

from .registry import get_registry, PROFILES, DEFAULT_PROFILE, TableDef


@dataclass
class Finding:
    severity: str          # "error" | "warning" | "info"
    table: str
    row: int | None        # 0-based row index within the table, or None
    column: str | None
    code: str
    message: str
    hint: str = ""
    row_key: str = ""      # human-readable identification of the row

    def as_dict(self) -> dict:
        return asdict(self)


NUMBER_RE = re.compile(r"^-?\d+$")


def _row_key(table: TableDef, row: dict) -> str:
    return " / ".join(str(row.get(c.name, "")) for c in table.key_columns) or ""


def _check_fields(table: TableDef, rows: list[dict], profile: str, out: list[Finding]):
    strict_len = PROFILES[profile]["strict_lengths"]
    for i, row in enumerate(rows):
        rk = _row_key(table, row)
        for col in table.columns_for_profile(profile):
            val = str(row.get(col.name, "") or "")
            if val == "":
                if col.mandatory:
                    out.append(Finding(
                        "error", table.name, i, col.name, "mandatory",
                        f"{col.name} is mandatory but empty.",
                        f"'{col.label}' must be filled in for every {table.title} record.",
                        rk))
                continue
            if col.type == "number":
                if not NUMBER_RE.match(val):
                    out.append(Finding(
                        "error", table.name, i, col.name, "number-format",
                        f"{col.name} must be an integer, got '{val}'.",
                        "Only digits (and an optional leading minus sign) are allowed.",
                        rk))
                    continue
                if not col.signed and val.startswith("-"):
                    out.append(Finding(
                        "error", table.name, i, col.name, "number-negative",
                        f"{col.name} must not be negative, got '{val}'.", "", rk))
            if col.length and len(val) > col.length:
                sev = "error" if strict_len else "warning"
                out.append(Finding(
                    sev, table.name, i, col.name, "length",
                    f"{col.name} is {len(val)} characters long; the ICD allows {col.length}.",
                    "SCOS-2000 rejects over-long fields. CCS5 tolerates them, but keep "
                    "within the ICD limit if the MIB is delivered to ESA.", rk))
            if col.enum and col.enum_strict and val not in [e.value for e in col.enum]:
                allowed = ", ".join(e.value for e in col.enum)
                out.append(Finding(
                    "error", table.name, i, col.name, "enum",
                    f"{col.name} has value '{val}' but must be one of: {allowed}.",
                    "", rk))
            if col.pattern and not re.match(col.pattern, val):
                out.append(Finding(
                    "error", table.name, i, col.name, "pattern",
                    f"{col.name} value '{val}' has an invalid format.",
                    col.hint, rk))


def _check_keys_and_fks(tables_rows: dict[str, list[dict]], profile: str, out: list[Finding]):
    reg = get_registry()
    # Value index for FK targets: (table, column) -> set of values
    index: dict[tuple[str, str], set[str]] = {}

    def values_of(tname: str, cname: str) -> set[str]:
        k = (tname, cname)
        if k not in index:
            index[k] = {str(r.get(cname, "") or "") for r in tables_rows.get(tname, [])}
            index[k].discard("")
        return index[k]

    for tname, rows in tables_rows.items():
        if tname not in reg.tables:
            continue
        table = reg.table(tname)
        # composite key uniqueness
        if table.key_columns:
            seen: dict[tuple, int] = {}
            for i, row in enumerate(rows):
                key = tuple(str(row.get(c.name, "") or "") for c in table.key_columns)
                if all(v == "" for v in key):
                    continue
                if key in seen:
                    out.append(Finding(
                        "error", tname, i, table.key_columns[0].name, "duplicate-key",
                        f"Duplicate record: key ({', '.join(key)}) already used in row {seen[key] + 1}.",
                        "Each record must have a unique key. Change the key fields or delete "
                        "the duplicate.", _row_key(table, row)))
                else:
                    seen[key] = i
        # declared foreign keys
        for col in table.columns_for_profile(profile):
            if not col.fk:
                continue
            ft, fc = col.fk.split(".")
            targets = values_of(ft, fc)
            for i, row in enumerate(rows):
                val = str(row.get(col.name, "") or "")
                if val and val not in targets:
                    ftitle = reg.table(ft).title if ft in reg.tables else ft
                    out.append(Finding(
                        "error", tname, i, col.name, "fk",
                        f"{col.name} references '{val}' but no such entry exists in "
                        f"{ft} ({ftitle}).",
                        f"Create the referenced {ftitle} record first, or fix the reference.",
                        _row_key(table, row)))


# (parent, count column, child, parent key column, child ref column)
_COUNT_CHECKS = [
    ("caf", "CAF_NCURVE", "cap", "CAF_NUMBR", "CAP_NUMBR"),
    ("txf", "TXF_NALIAS", "txp", "TXF_NUMBR", "TXP_NUMBR"),
    ("cca", "CCA_NCURVE", "ccs", "CCA_NUMBR", "CCS_NUMBR"),
    ("paf", "PAF_NALIAS", "pas", "PAF_NUMBR", "PAS_NUMBR"),
    ("prf", "PRF_NRANGE", "prv", "PRF_NUMBR", "PRV_NUMBR"),
    ("ccf", "CCF_NPARS", "cdf", "CCF_CNAME", "CDF_CNAME"),
    ("ocf", "OCF_NBOOL", "ocp", "OCF_NAME", "OCP_NAME"),
    ("csf", "CSF_ELEMS", "css", "CSF_NAME", "CSS_SQNAME"),
    ("csf", "CSF_NFPARS", "csp", "CSF_NAME", "CSP_SQNAME"),
]


def _check_counts(tables_rows: dict[str, list[dict]], out: list[Finding]):
    reg = get_registry()
    for parent, count_col, child, pkey, cref in _COUNT_CHECKS:
        prows = tables_rows.get(parent, [])
        crows = tables_rows.get(child, [])
        if not prows:
            continue
        counts: dict[str, int] = {}
        for r in crows:
            counts[str(r.get(cref, "") or "")] = counts.get(str(r.get(cref, "") or ""), 0) + 1
        ptable = reg.table(parent)
        for i, row in enumerate(prows):
            declared = str(row.get(count_col, "") or "")
            if declared == "":
                continue
            actual = counts.get(str(row.get(pkey, "") or ""), 0)
            try:
                if int(declared) != actual:
                    out.append(Finding(
                        "warning", parent, i, count_col, "count-mismatch",
                        f"{count_col} declares {declared} but {actual} matching "
                        f"record(s) exist in {child}.",
                        f"Update {count_col} (or simply leave it empty where optional) — "
                        f"importers cross-check this number.", _row_key(ptable, row)))
            except ValueError:
                pass  # number-format check already reported it


def _check_semantics(tables_rows: dict[str, list[dict]], out: list[Finding]):
    reg = get_registry()

    def rows(t):  # noqa: ANN001
        return tables_rows.get(t, [])

    # --- TM packets ---------------------------------------------------------
    pic_keys = {(r.get("PIC_TYPE", ""), r.get("PIC_STYPE", ""), r.get("PIC_APID", ""))
                for r in rows("pic")}

    def has_pic(ptype, pstype, apid):
        return ((ptype, pstype, apid) in pic_keys or (ptype, pstype, "") in pic_keys)

    tpsd_with_vpd = {r.get("VPD_TPSD", "") for r in rows("vpd")}
    spids_with_plf = {r.get("PLF_SPID", "") for r in rows("plf")}
    pid_table = reg.table("pid") if "pid" in reg.tables else None
    for i, r in enumerate(rows("pid")):
        rk = _row_key(pid_table, r) if pid_table else ""
        pi1, pi2 = r.get("PID_PI1_VAL", ""), r.get("PID_PI2_VAL", "")
        if (pi1 not in ("", "0") or pi2 not in ("", "0")) and \
                not has_pic(r.get("PID_TYPE", ""), r.get("PID_STYPE", ""), r.get("PID_APID", "")):
            out.append(Finding(
                "error", "pid", i, "PID_PI1_VAL", "pic-missing",
                f"Packet uses additional identification value(s) (PI1/PI2) but there is no "
                f"matching PIC record for type {r.get('PID_TYPE')}/{r.get('PID_STYPE')}.",
                "Add a 'Packet identification criteria' (pic) record telling the ground "
                "segment where to find the identification field (e.g. the housekeeping SID) "
                "inside packets of this type/subtype.", rk))
        tpsd = r.get("PID_TPSD", "")
        spid = r.get("PID_SPID", "")
        if tpsd not in ("", "-1") and tpsd not in tpsd_with_vpd:
            out.append(Finding(
                "warning", "pid", i, "PID_TPSD", "vpd-missing",
                f"Packet declares variable structure definition TPSD={tpsd} but no VPD "
                f"records exist for it.",
                "Define the packet layout in the 'Variable packet definition' (vpd) table, "
                "or clear PID_TPSD (-1/empty) for fixed packets.", rk))
        if tpsd in ("", "-1") and spid and spid not in spids_with_plf:
            out.append(Finding(
                "info", "pid", i, "PID_SPID", "plf-empty",
                f"Fixed packet SPID={spid} has no parameters placed in it (no plf records).",
                "Use the packet layout editor (or plf table) to place TM parameters into "
                "this packet. A packet without parameters can be identified but not decoded.",
                rk))

    # --- TM parameter calibration cross-checks ------------------------------
    caf_ids = {r.get("CAF_NUMBR", "") for r in rows("caf")}
    txf_ids = {r.get("TXF_NUMBR", "") for r in rows("txf")}
    mcf_ids = {r.get("MCF_IDENT", "") for r in rows("mcf")}
    lgf_ids = {r.get("LGF_IDENT", "") for r in rows("lgf")}
    pcf_table = reg.table("pcf") if "pcf" in reg.tables else None
    cur_pnames = {r.get("CUR_PNAME", "") for r in rows("cur")}
    for i, r in enumerate(rows("pcf")):
        rk = _row_key(pcf_table, r) if pcf_table else ""
        categ, curtx, name = r.get("PCF_CATEG", ""), r.get("PCF_CURTX", ""), r.get("PCF_NAME", "")
        if curtx:
            if categ == "S" and curtx not in txf_ids:
                out.append(Finding(
                    "error", "pcf", i, "PCF_CURTX", "calib-missing",
                    f"Status parameter '{name}' references textual calibration '{curtx}' "
                    f"which does not exist in txf.",
                    "Create the textual calibration (txf/txp) or fix PCF_CURTX.", rk))
            if categ == "N" and curtx not in (caf_ids | mcf_ids | lgf_ids):
                out.append(Finding(
                    "error", "pcf", i, "PCF_CURTX", "calib-missing",
                    f"Numeric parameter '{name}' references calibration '{curtx}' which "
                    f"exists neither in caf, mcf nor lgf.",
                    "Create the calibration curve (caf/cap, mcf or lgf) or fix PCF_CURTX.",
                    rk))
        if categ == "S" and not curtx and name not in cur_pnames:
            out.append(Finding(
                "warning", "pcf", i, "PCF_CURTX", "status-no-calib",
                f"Parameter '{name}' is marked as Status (PCF_CATEG=S) but has no textual "
                f"calibration assigned.",
                "Assign a textual calibration (PCF_CURTX -> txf) so raw values are shown "
                "as meaningful states (e.g. 0='OFF', 1='ON').", rk))
        if categ == "T" and curtx:
            out.append(Finding(
                "error", "pcf", i, "PCF_CURTX", "text-with-calib",
                f"Text parameter '{name}' (PCF_CATEG=T) must not reference a calibration.",
                "Clear PCF_CURTX for text parameters.", rk))

    # --- TC commands ---------------------------------------------------------
    cpc_by_name = {r.get("CPC_PNAME", ""): r for r in rows("cpc")}
    cdf_table = reg.table("cdf") if "cdf" in reg.tables else None
    for i, r in enumerate(rows("cdf")):
        rk = _row_key(cdf_table, r) if cdf_table else ""
        eltype = r.get("CDF_ELTYPE", "")
        if eltype in ("E", "F") and not r.get("CDF_PNAME", ""):
            out.append(Finding(
                "error", "cdf", i, "CDF_PNAME", "cdf-pname",
                "Editable/Fixed command elements must reference a command parameter "
                "(CDF_PNAME).",
                "Select the cpc parameter this element carries, or make it a fixed "
                "area (type A) with an explicit value.", rk))
        if eltype == "A" and not r.get("CDF_VALUE", ""):
            out.append(Finding(
                "error", "cdf", i, "CDF_VALUE", "cdf-area-value",
                "Fixed areas (CDF_ELTYPE=A) must carry a value in CDF_VALUE.",
                "Enter the constant value this area always contains.", rk))
        if eltype == "F" and not r.get("CDF_VALUE", ""):
            pn = r.get("CDF_PNAME", "")
            cpc_r = cpc_by_name.get(pn)
            if cpc_r is not None and not cpc_r.get("CPC_DEFVAL", "") and \
                    r.get("CDF_INTER", "") != "T":
                out.append(Finding(
                    "error", "cdf", i, "CDF_VALUE", "cdf-fixed-value",
                    f"Fixed parameter element '{pn}' has no value: CDF_VALUE is empty and "
                    f"the parameter has no default (CPC_DEFVAL).",
                    "Give the element a value, set a parameter default, or make the "
                    "element editable.", rk))

    cpc_table = reg.table("cpc") if "cpc" in reg.tables else None
    for i, r in enumerate(rows("cpc")):
        rk = _row_key(cpc_table, r) if cpc_table else ""
        categ = r.get("CPC_CATEG", "")
        if categ == "C" and not r.get("CPC_CCAREF", ""):
            out.append(Finding(
                "error", "cpc", i, "CPC_CCAREF", "cpc-cal",
                "CPC_CATEG=C (numeric calibration) requires CPC_CCAREF to reference a "
                "cca curve.", "Select the de-calibration curve, or set category to N.", rk))
        if categ == "T" and not r.get("CPC_PAFREF", ""):
            out.append(Finding(
                "error", "cpc", i, "CPC_PAFREF", "cpc-cal",
                "CPC_CATEG=T (textual calibration) requires CPC_PAFREF to reference a "
                "paf alias set.", "Select the alias set, or set category to N.", rk))

    # Commands: APID recommended
    ccf_table = reg.table("ccf") if "ccf" in reg.tables else None
    for i, r in enumerate(rows("ccf")):
        rk = _row_key(ccf_table, r) if ccf_table else ""
        if not r.get("CCF_APID", "") and not r.get("CCF_CTYPE", ""):
            out.append(Finding(
                "warning", "ccf", i, "CCF_APID", "ccf-apid",
                f"Command '{r.get('CCF_CNAME', '')}' has no APID.",
                "Every spacecraft command packet needs the APID of the on-board "
                "application that consumes it.", rk))


def validate_project(tables_rows: dict[str, list[dict]],
                     profile: str = DEFAULT_PROFILE) -> list[Finding]:
    if profile not in PROFILES:
        raise ValueError(f"Unknown profile '{profile}'")
    reg = get_registry()
    out: list[Finding] = []
    for tname, rows in tables_rows.items():
        if tname in reg.tables:
            _check_fields(reg.table(tname), rows, profile, out)
    _check_keys_and_fks(tables_rows, profile, out)
    _check_counts(tables_rows, out)
    _check_semantics(tables_rows, out)
    severity_rank = {"error": 0, "warning": 1, "info": 2}
    out.sort(key=lambda f: (severity_rank.get(f.severity, 3), f.table, f.row if f.row is not None else -1))
    return out
