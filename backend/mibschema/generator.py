"""Generator: project rows -> SCOS-2000 ASCII MIB files (.dat) / zip archive."""

from __future__ import annotations

import io
import zipfile

from .parser import EXTRA_KEY
from .registry import TableDef, get_registry, PROFILES, DEFAULT_PROFILE


def generate_table_file(table: TableDef, rows: list[dict], profile: str = DEFAULT_PROFILE) -> str:
    """Render rows of one table as ICD-compliant tab-separated lines.

    Columns are emitted in ICD order, restricted to the selected profile.
    All defined columns are always emitted (the SCOS importer accepts both
    full and truncated records; emitting all avoids ambiguity). Values that
    were preserved beyond the known columns (EXTRA_KEY) are appended as-is.
    """
    cols = table.columns_for_profile(profile)
    lines = []
    for row in rows:
        values = [str(row.get(c.name, "") or "") for c in cols]
        extra = row.get(EXTRA_KEY) or []
        lines.append("\t".join(values + [str(v) for v in extra]))
    return "\n".join(lines) + ("\n" if lines else "")


def generate_mib_zip(tables_rows: dict[str, list[dict]], profile: str = DEFAULT_PROFILE,
                     include_empty: bool = True) -> bytes:
    """Build a zip archive with one .dat file per registry table.

    include_empty: also emit empty files for tables without rows — most MIB
    importers expect the complete file set to be present.
    """
    if profile not in PROFILES:
        raise ValueError(f"Unknown profile '{profile}'")
    reg = get_registry()
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for tdef in reg.tables.values():
            rows = tables_rows.get(tdef.name, [])
            if not rows and not include_empty:
                continue
            zf.writestr(tdef.file, generate_table_file(tdef, rows, profile))
    return buf.getvalue()
