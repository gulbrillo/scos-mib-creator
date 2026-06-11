import re
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import Response
from sqlalchemy.orm import Session

from .. import mibstore
from ..db import get_db
from ..models import User
from ..security import get_current_user, get_project_for
from mibschema import generate_mib_zip, parse_mib_zip, validate_project
from mibschema.registry import PROFILES

router = APIRouter(prefix="/api/projects/{project_id}", tags=["io"])


@router.post("/import")
async def import_mib(project_id: int,
                     file: UploadFile = File(...),
                     mode: str = Form("replace-tables"),
                     dry_run: bool = Form(False),
                     db: Session = Depends(get_db),
                     user: User = Depends(get_current_user)):
    """Import a zip of .dat files.

    mode:
      replace-all    - wipe the whole project, then load the archive
      replace-tables - replace only the tables present in the archive
      append         - append archive rows to existing tables
    """
    get_project_for(db, project_id, user, write=True)
    if mode not in ("replace-all", "replace-tables", "append"):
        raise HTTPException(400, "Invalid import mode")
    data = await file.read()
    tables, issues = parse_mib_zip(data)
    counts = {t: len(rows) for t, rows in tables.items()}
    has_error = any(i.severity == "error" for i in issues)
    if not dry_run and tables and not has_error:
        if mode == "replace-all":
            mibstore.clear_project(db, project_id)
        for tname, rows in tables.items():
            if mode in ("replace-all", "replace-tables"):
                mibstore.replace_table(db, project_id, tname, rows)
            else:
                mibstore.insert_rows(db, project_id, tname, rows)
        db.commit()
    return {
        "imported": bool(tables) and not has_error and not dry_run,
        "dry_run": dry_run,
        "counts": counts,
        "issues": [{"severity": i.severity, "table": i.table, "line": i.line,
                    "message": i.message} for i in issues],
    }


@router.get("/export")
def export_mib(project_id: int, profile: str | None = None, include_empty: bool = True,
               db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    project = get_project_for(db, project_id, user)
    profile = profile or project.profile
    if profile not in PROFILES:
        raise HTTPException(400, f"Unknown profile '{profile}'")
    tables = mibstore.project_tables_dict(db, project_id)
    blob = generate_mib_zip(tables, profile=profile, include_empty=include_empty)
    safe = re.sub(r"[^A-Za-z0-9_-]+", "_", project.name).strip("_") or "mib"
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M")
    return Response(
        content=blob, media_type="application/zip",
        headers={"Content-Disposition":
                 f'attachment; filename="{safe}-mib-{profile}-{stamp}.zip"'})


@router.post("/validate")
def validate(project_id: int, db: Session = Depends(get_db),
             user: User = Depends(get_current_user)):
    project = get_project_for(db, project_id, user)
    tables = mibstore.project_tables_dict(db, project_id)
    findings = validate_project(tables, profile=project.profile)
    summary = {"error": 0, "warning": 0, "info": 0}
    for f in findings:
        summary[f.severity] = summary.get(f.severity, 0) + 1
    return {"summary": summary, "findings": [f.as_dict() for f in findings]}
