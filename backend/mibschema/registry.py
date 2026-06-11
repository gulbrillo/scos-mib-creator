"""Schema registry: loads the YAML table definitions that drive everything
(parsing, generation, validation, and the auto-generated editor UI)."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

import yaml

REGISTRY_DIR = Path(__file__).parent / "registry"

# Export profiles. strict_lengths: exceeding the ICD field length is an error
# (SCOS-2000 importer truncates/rejects); CCS5 supports unlimited field
# lengths, so it is only a warning there.
PROFILES: dict[str, dict] = {
    "scos-7.0": {
        "label": "ESA SCOS-2000 (Database Import ICD 7.0)",
        "strict_lengths": True,
    },
    "ccs5": {
        "label": "Terma CCS5 (ICD 7.x + CCS5 extensions)",
        "strict_lengths": False,
    },
}
DEFAULT_PROFILE = "ccs5"


@dataclass
class EnumValue:
    value: str
    label: str
    help: str = ""


@dataclass
class ColumnDef:
    name: str
    label: str
    type: str  # "char" | "number"
    length: int | None = None
    key: bool = False
    mandatory: bool = False
    signed: bool = False          # numbers: negative values allowed
    hint: str = ""                # one-line tooltip
    help: str = ""                # extended help (help drawer)
    default: str | None = None
    enum: list[EnumValue] | None = None
    enum_strict: bool = True      # values outside enum are an error
    fk: str | None = None         # "table.COLUMN" the value must exist in
    pattern: str | None = None    # regex the (non-empty) value must match
    profiles: list[str] | None = None  # None = present in all profiles

    def in_profile(self, profile: str) -> bool:
        return self.profiles is None or profile in self.profiles


@dataclass
class TableDef:
    name: str
    file: str
    title: str
    domain: str
    icd: str = ""
    description: str = ""
    row_label: str = ""
    columns: list[ColumnDef] = field(default_factory=list)

    @property
    def key_columns(self) -> list[ColumnDef]:
        return [c for c in self.columns if c.key]

    def columns_for_profile(self, profile: str) -> list[ColumnDef]:
        return [c for c in self.columns if c.in_profile(profile)]

    def column(self, name: str) -> ColumnDef | None:
        for c in self.columns:
            if c.name == name:
                return c
        return None


@dataclass
class Domain:
    id: str
    title: str
    icon: str = ""
    description: str = ""
    tables: list[str] = field(default_factory=list)


class Registry:
    def __init__(self, tables: dict[str, TableDef], domains: list[Domain]):
        self.tables = tables          # insertion order = export order
        self.domains = domains

    def table(self, name: str) -> TableDef:
        return self.tables[name]

    def table_for_file(self, filename: str) -> TableDef | None:
        base = filename.lower().rsplit("/", 1)[-1]
        for t in self.tables.values():
            if t.file.lower() == base:
                return t
        return None


def _load_column(raw: dict) -> ColumnDef:
    enum = None
    if raw.get("enum"):
        enum = [EnumValue(value=str(e["value"]), label=e.get("label", str(e["value"])),
                          help=e.get("help", "")) for e in raw["enum"]]
    col = ColumnDef(
        name=raw["name"],
        label=raw.get("label", raw["name"]),
        type=raw["type"],
        length=raw.get("length"),
        key=bool(raw.get("key", False)),
        mandatory=bool(raw.get("mandatory", False)),
        signed=bool(raw.get("signed", False)),
        hint=(raw.get("hint") or "").strip(),
        help=(raw.get("help") or "").strip(),
        default=None if raw.get("default") is None else str(raw["default"]),
        enum=enum,
        enum_strict=bool(raw.get("enum_strict", True)),
        fk=raw.get("fk"),
        pattern=raw.get("pattern"),
        profiles=raw.get("profiles"),
    )
    if col.pattern:
        re.compile(col.pattern)  # fail fast on bad registry data
    return col


@lru_cache(maxsize=1)
def get_registry() -> Registry:
    domains_raw = yaml.safe_load((REGISTRY_DIR / "_domains.yaml").read_text(encoding="utf-8"))
    domains = [Domain(id=d["id"], title=d["title"], icon=d.get("icon", ""),
                      description=d.get("description", ""), tables=d.get("tables", []))
               for d in domains_raw["domains"]]

    tables: dict[str, TableDef] = {}
    # Load in the order the domains list them so exports are deterministic.
    for dom in domains:
        for tname in dom.tables:
            raw = yaml.safe_load((REGISTRY_DIR / f"{tname}.yaml").read_text(encoding="utf-8"))
            assert raw["table"] == tname, f"registry file {tname}.yaml declares table {raw['table']}"
            tables[tname] = TableDef(
                name=raw["table"],
                file=raw.get("file", f"{tname}.dat"),
                title=raw["title"],
                domain=dom.id,
                icd=str(raw.get("icd", "")),
                description=(raw.get("description") or "").strip(),
                row_label=raw.get("row_label", ""),
                columns=[_load_column(c) for c in raw["columns"]],
            )
    return Registry(tables, domains)


def registry_as_json(profile: str | None = None) -> dict:
    """Serialise the registry for the frontend (/api/schema)."""
    reg = get_registry()
    out: dict = {"profiles": {k: v["label"] for k, v in PROFILES.items()},
                 "default_profile": DEFAULT_PROFILE,
                 "domains": [], "tables": {}}
    for dom in reg.domains:
        out["domains"].append({"id": dom.id, "title": dom.title, "icon": dom.icon,
                               "description": dom.description, "tables": dom.tables})
    for t in reg.tables.values():
        out["tables"][t.name] = {
            "name": t.name, "file": t.file, "title": t.title, "domain": t.domain,
            "icd": t.icd, "description": t.description, "row_label": t.row_label,
            "key_columns": [c.name for c in t.key_columns],
            "columns": [{
                "name": c.name, "label": c.label, "type": c.type, "length": c.length,
                "key": c.key, "mandatory": c.mandatory, "signed": c.signed,
                "hint": c.hint, "help": c.help, "default": c.default,
                "enum": ([{"value": e.value, "label": e.label, "help": e.help}
                          for e in c.enum] if c.enum else None),
                "enum_strict": c.enum_strict, "fk": c.fk, "pattern": c.pattern,
                "profiles": c.profiles,
            } for c in t.columns if profile is None or c.in_profile(profile)],
        }
    return out
