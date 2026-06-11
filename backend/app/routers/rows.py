from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from .. import mibstore
from ..db import get_db
from ..models import MibRow, User
from ..security import get_current_user, get_project_for
from mibschema import get_registry
from mibschema.parser import EXTRA_KEY

router = APIRouter(prefix="/api/projects/{project_id}/tables", tags=["rows"])

# Count columns that the MIB declares redundantly (e.g. CAF_NCURVE = number of
# cap points). The registry hints promise these are "kept in sync
# automatically", so any manual edit of a child table re-derives the parent
# counts here. child -> (parent, parent key col, child ref col, count col)
COUNT_SYNC: dict[str, tuple[str, str, str, str]] = {
    "cap": ("caf", "CAF_NUMBR", "CAP_NUMBR", "CAF_NCURVE"),
    "txp": ("txf", "TXF_NUMBR", "TXP_NUMBR", "TXF_NALIAS"),
    "ccs": ("cca", "CCA_NUMBR", "CCS_NUMBR", "CCA_NCURVE"),
    "pas": ("paf", "PAF_NUMBR", "PAS_NUMBR", "PAF_NALIAS"),
    "prv": ("prf", "PRF_NUMBR", "PRV_NUMBR", "PRF_NRANGE"),
    "cdf": ("ccf", "CCF_CNAME", "CDF_CNAME", "CCF_NPARS"),
    "ocp": ("ocf", "OCF_NAME", "OCP_NAME", "OCF_NBOOL"),
    "css": ("csf", "CSF_NAME", "CSS_SQNAME", "CSF_ELEMS"),
    "csp": ("csf", "CSF_NAME", "CSP_SQNAME", "CSF_NFPARS"),
}


def _sync_counts(db: Session, project_id: int, child_table: str):
    if child_table not in COUNT_SYNC:
        return
    parent, pkey, cref, count_col = COUNT_SYNC[child_table]
    counts: dict[str, int] = {}
    for r in mibstore.table_rows(db, project_id, child_table):
        key = str(r.data.get(cref, "") or "")
        if key:
            counts[key] = counts.get(key, 0) + 1
    for row in mibstore.table_rows(db, project_id, parent):
        actual = counts.get(str(row.data.get(pkey, "") or ""), 0)
        current = str(row.data.get(count_col, "") or "")
        # leave an optional count empty while there are no children
        new = str(actual) if (actual > 0 or current != "") else ""
        if new != current:
            row.data = {**row.data, count_col: new}
            row.version += 1


class RowIn(BaseModel):
    data: dict


class RowUpdate(BaseModel):
    data: dict
    version: int | None = None


def _table_def(table: str):
    reg = get_registry()
    if table not in reg.tables:
        raise HTTPException(404, f"Unknown MIB table '{table}'")
    return reg.table(table)


def _clean_data(table, data: dict) -> dict:
    """Keep only known columns (+ preserved extras), normalise to strings."""
    cols = {c.name for c in table.columns}
    cleaned = {k: ("" if v is None else str(v)) for k, v in data.items() if k in cols}
    for c in table.columns:
        cleaned.setdefault(c.name, "")
    if isinstance(data.get(EXTRA_KEY), list):
        cleaned[EXTRA_KEY] = [str(v) for v in data[EXTRA_KEY]]
    return cleaned


def row_json(r: MibRow) -> dict:
    return {"id": r.id, "seq": r.seq, "version": r.version, "data": r.data}


@router.get("/{table}/rows")
def list_rows(project_id: int, table: str, db: Session = Depends(get_db),
              user: User = Depends(get_current_user)):
    get_project_for(db, project_id, user)
    _table_def(table)
    return [row_json(r) for r in mibstore.table_rows(db, project_id, table)]


@router.post("/{table}/rows", status_code=201)
def create_row(project_id: int, table: str, req: RowIn, db: Session = Depends(get_db),
               user: User = Depends(get_current_user)):
    get_project_for(db, project_id, user, write=True)
    tdef = _table_def(table)
    row = mibstore.insert_rows(db, project_id, table, [_clean_data(tdef, req.data)])[0]
    db.flush()
    _sync_counts(db, project_id, table)
    db.commit()
    return row_json(row)


@router.put("/{table}/rows/{row_id}")
def update_row(project_id: int, table: str, row_id: int, req: RowUpdate,
               db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    get_project_for(db, project_id, user, write=True)
    tdef = _table_def(table)
    row = db.get(MibRow, row_id)
    if row is None or row.project_id != project_id or row.table_name != table:
        raise HTTPException(404, "Row not found")
    if req.version is not None and req.version != row.version:
        raise HTTPException(409, "This record was modified by someone else. "
                                 "Reload it and re-apply your change.")
    row.data = _clean_data(tdef, req.data)
    row.version += 1
    db.flush()
    _sync_counts(db, project_id, table)
    db.commit()
    return row_json(row)


@router.delete("/{table}/rows/{row_id}")
def delete_row(project_id: int, table: str, row_id: int, db: Session = Depends(get_db),
               user: User = Depends(get_current_user)):
    get_project_for(db, project_id, user, write=True)
    _table_def(table)
    row = db.get(MibRow, row_id)
    if row is None or row.project_id != project_id or row.table_name != table:
        raise HTTPException(404, "Row not found")
    db.delete(row)
    db.flush()
    _sync_counts(db, project_id, table)
    db.commit()
    return {"ok": True}
