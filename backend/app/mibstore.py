"""Helpers to read/write MIB rows for a project."""

from sqlalchemy import func
from sqlalchemy.orm import Session

from .models import MibRow


def table_rows(db: Session, project_id: int, table: str) -> list[MibRow]:
    return (db.query(MibRow)
            .filter_by(project_id=project_id, table_name=table)
            .order_by(MibRow.seq, MibRow.id).all())


def project_tables_dict(db: Session, project_id: int) -> dict[str, list[dict]]:
    """All rows of a project as {table: [data, ...]} for validation/export."""
    rows = (db.query(MibRow).filter_by(project_id=project_id)
            .order_by(MibRow.table_name, MibRow.seq, MibRow.id).all())
    out: dict[str, list[dict]] = {}
    for r in rows:
        out.setdefault(r.table_name, []).append(r.data)
    return out


def next_seq(db: Session, project_id: int, table: str) -> int:
    m = (db.query(func.max(MibRow.seq))
         .filter_by(project_id=project_id, table_name=table).scalar())
    return (m or 0) + 1


def insert_rows(db: Session, project_id: int, table: str, datas: list[dict]) -> list[MibRow]:
    seq = next_seq(db, project_id, table)
    rows = []
    for i, data in enumerate(datas):
        row = MibRow(project_id=project_id, table_name=table, seq=seq + i, data=data)
        db.add(row)
        rows.append(row)
    return rows


def replace_table(db: Session, project_id: int, table: str, datas: list[dict]):
    (db.query(MibRow).filter_by(project_id=project_id, table_name=table)
     .delete(synchronize_session=False))
    insert_rows(db, project_id, table, datas)


def clear_project(db: Session, project_id: int):
    db.query(MibRow).filter_by(project_id=project_id).delete(synchronize_session=False)


def find_value_rows(db: Session, project_id: int, table: str, column: str,
                    value: str) -> list[MibRow]:
    return [r for r in table_rows(db, project_id, table)
            if str(r.data.get(column, "")) == str(value)]


def column_values(db: Session, project_id: int, table: str, column: str) -> set[str]:
    return {str(r.data.get(column, "")) for r in table_rows(db, project_id, table)
            if str(r.data.get(column, "")) != ""}
