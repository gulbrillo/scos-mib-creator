"""SCOS-2000 / CCS5 MIB engine.

Pure-Python package (no web framework dependencies) implementing:
- a schema registry describing every supported MIB table (loaded from YAML),
- a parser and generator for the tab-separated ASCII MIB files,
- a validation engine (field, referential and completeness checks),
- PUS (ECSS-E-ST-70-41) helper data: PTC/PFC types and service catalog.

Authoritative reference: SCOS-2000 Database Import ICD,
EGOS-MCS-S2K-ICD-0001 issue 7.0 (docs/egos-mcs-s2k-icd-0001-v7.0.pdf).
"""

from .registry import Registry, TableDef, ColumnDef, get_registry, PROFILES
from .parser import parse_table_file, parse_mib_zip
from .generator import generate_table_file, generate_mib_zip
from .validator import validate_project, Finding

__all__ = [
    "Registry", "TableDef", "ColumnDef", "get_registry", "PROFILES",
    "parse_table_file", "parse_mib_zip",
    "generate_table_file", "generate_mib_zip",
    "validate_project", "Finding",
]
