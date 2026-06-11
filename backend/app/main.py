import os

from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from . import config
from .db import Base, SessionLocal, engine
from .models import User
from .routers import auth, io, projects, rows, schema, users, wizards
from .security import hash_password

app = FastAPI(title="SCOS MIB Creator", docs_url="/api/docs", openapi_url="/api/openapi.json")

for r in (auth.router, users.router, projects.router, schema.router,
          rows.router, io.router, wizards.router):
    app.include_router(r)


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.on_event("startup")
def startup():
    Base.metadata.create_all(engine)
    db = SessionLocal()
    try:
        if db.query(User).count() == 0:
            db.add(User(username=config.ADMIN_USERNAME,
                        password_hash=hash_password(config.ADMIN_PASSWORD),
                        is_admin=True))
            db.commit()
    finally:
        db.close()


# ---- static SPA (built frontend) -------------------------------------------
if config.STATIC_DIR and os.path.isdir(config.STATIC_DIR):
    app.mount("/assets", StaticFiles(directory=os.path.join(config.STATIC_DIR, "assets")),
              name="assets")
    index_file = os.path.join(config.STATIC_DIR, "index.html")

    @app.get("/{full_path:path}", include_in_schema=False)
    def spa(full_path: str):
        if full_path.startswith("api/"):
            return JSONResponse({"detail": "Not found"}, status_code=404)
        candidate = os.path.normpath(os.path.join(config.STATIC_DIR, full_path))
        if full_path and candidate.startswith(os.path.normpath(config.STATIC_DIR)) \
                and os.path.isfile(candidate):
            return FileResponse(candidate)
        return FileResponse(index_file)
