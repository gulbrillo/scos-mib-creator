"""Parser for SCOS-2000 ASCII MIB files (tab-separated .dat files)."""

from __future__ import annotations

import io
import zipfile
from dataclasses import dataclass

from .registry import TableDef, get_registry

# Key under which values beyond the last known column are preserved, so an
# import -> export round trip is lossless even for unknown vendor extensions.
EXTRA_KEY = "__extra__"


@dataclass
class ParseIssue:
    severity: str  # "error" | "warning" | "info"
    table: str
    line: int | None
    message: str


def parse_table_file(table: TableDef, text: str) -> tuple[list[dict], list[ParseIssue]]:
    """Parse one .dat file into a list of row dicts (column name -> string).

    Per ICD section 2.3: one record per line, fields separated by a single
    TAB; null fields contain only the separator; trailing optional fields may
    be omitted entirely.
    """
    rows: list[dict] = []
    issues: list[ParseIssue] = []
    # Import maps against the union of all profiles' columns so that e.g. a
    # CCS5-extended file loads fine into any project.
    cols = table.columns
    for lineno, raw_line in enumerate(text.split("\n"), start=1):
        line = raw_line.rstrip("\r")
        if line.strip() == "":
            continue
        values = line.split("\t")
        if len(values) > len(cols):
            issues.append(ParseIssue(
                "warning", table.name, lineno,
                f"{table.file}: line {lineno} has {len(values)} fields but only "
                f"{len(cols)} are defined for '{table.name}'; extra values are "
                f"preserved and re-exported as-is."))
        row: dict = {}
        for i, col in enumerate(cols):
            row[col.name] = values[i].strip() if i < len(values) else ""
        if len(values) > len(cols):
            row[EXTRA_KEY] = [v.strip() for v in values[len(cols):]]
        rows.append(row)
    return rows, issues


def parse_mib_zip(data: bytes) -> tuple[dict[str, list[dict]], list[ParseIssue]]:
    """Parse a zip archive of .dat files into {table_name: rows}.

    Files are recognised by their (case-insensitive) base name, e.g. pcf.dat.
    Unknown files are reported and skipped. Directory structure is ignored.
    """
    reg = get_registry()
    tables: dict[str, list[dict]] = {}
    issues: list[ParseIssue] = []
    try:
        zf = zipfile.ZipFile(io.BytesIO(data))
    except zipfile.BadZipFile as exc:
        return {}, [ParseIssue("error", "", None, f"Not a valid zip archive: {exc}")]

    for info in zf.infolist():
        if info.is_dir():
            continue
        base = info.filename.rsplit("/", 1)[-1]
        if not base.lower().endswith(".dat"):
            issues.append(ParseIssue("info", "", None,
                                     f"Ignoring non-MIB file '{info.filename}'."))
            continue
        tdef = reg.table_for_file(base)
        if tdef is None:
            issues.append(ParseIssue(
                "warning", "", None,
                f"Ignoring '{info.filename}': not a MIB table supported by this tool "
                f"(display tables and vendor-specific files are not imported)."))
            continue
        try:
            text = zf.read(info).decode("utf-8")
        except UnicodeDecodeError:
            text = zf.read(info).decode("latin-1")
            issues.append(ParseIssue("info", tdef.name, None,
                                     f"{base}: not valid UTF-8, decoded as Latin-1."))
        rows, file_issues = parse_table_file(tdef, text)
        if tdef.name in tables:
            issues.append(ParseIssue("warning", tdef.name, None,
                                     f"Duplicate file for table '{tdef.name}' in archive; "
                                     f"using the last one found."))
        tables[tdef.name] = rows
        issues.extend(file_issues)
    if not tables:
        issues.append(ParseIssue("error", "", None,
                                 "No recognisable MIB .dat files found in the archive."))
    return tables, issues
