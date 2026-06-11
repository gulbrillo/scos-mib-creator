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
    db.commit()
    return {"ok": True}
