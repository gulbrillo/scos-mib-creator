"""API end-to-end test: project lifecycle, wizards, validation, export/import
round trip (the exported MIB re-imported into a fresh project must export
byte-identically)."""

import io
import os
import zipfile

import pytest
from fastapi.testclient import TestClient

os.environ["DATABASE_URL"] = "sqlite:///./test_api.db"
os.environ["SECRET_KEY"] = "test-secret"

from app.db import Base, engine  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture(scope="module")
def client():
    Base.metadata.drop_all(engine)  # clean slate; startup re-creates schema + admin
    with TestClient(app) as c:
        r = c.post("/api/auth/login", json={"username": "admin", "password": "admin"})
        assert r.status_code == 200, r.text
        yield c
    engine.dispose()
    if os.path.exists("test_api.db"):
        try:
            os.remove("test_api.db")
        except PermissionError:
            pass


def zip_contents(blob: bytes) -> dict[str, bytes]:
    zf = zipfile.ZipFile(io.BytesIO(blob))
    return {i.filename: zf.read(i) for i in zf.infolist()}


def test_auth_required():
    with TestClient(app) as anon:
        assert anon.get("/api/projects").status_code == 401


def test_full_project_lifecycle(client):
    # --- create project with bootstrap content -----------------------------
    r = client.post("/api/projects", json={"name": "UnitTest MIB", "profile": "ccs5"})
    assert r.status_code == 201, r.text
    pid = r.json()["id"]
    assert r.json()["row_counts"]["tcp"] == 1     # bootstrap header present

    # --- schema and PUS helper endpoints ------------------------------------
    schema = client.get("/api/schema").json()
    assert "pcf" in schema["tables"]
    assert any(s["service"] == 17 for s in client.get("/api/pus/services").json())

    # --- TM packet wizard: HK packet with SID + 3 parameters ----------------
    r = client.post(f"/api/projects/{pid}/wizards/tm-packet", json={
        "descr": "Standard HK report", "apid": 100, "type": 3, "stype": 25,
        "pi1_val": 1, "dfh_size": 10, "interval_ms": 8000, "packet_name": "UT_HK1",
        "params": [
            {"name": "UTSID", "descr": "Structure ID", "ptc": 3, "pfc": 12,
             "is_pi1": True},
            {"name": "UTVOLT1", "descr": "Bus voltage", "ptc": 3, "pfc": 12,
             "unit": "V"},
            {"name": "UTMODE", "descr": "Unit mode", "ptc": 2, "pfc": 8},
        ]})
    assert r.status_code == 200, r.text
    spid = r.json()["spid"]
    assert r.json()["created"] == {"pcf": 3, "plf": 3, "pid": 1, "pic": 1, "tpcf": 1}
    # SID is at byte 16 (6 CCSDS + 10 DFH)
    pic = client.get(f"/api/projects/{pid}/tables/pic/rows").json()
    assert pic[0]["data"]["PIC_PI1_OFF"] == "16"
    assert pic[0]["data"]["PIC_PI1_WID"] == "16"

    # --- calibrations: textual for mode (attached), numeric for voltage -----
    r = client.post(f"/api/projects/{pid}/wizards/calibration", json={
        "kind": "txf", "ident": "UTMODES", "descr": "Unit modes", "rawfmt": "U",
        "texts": [{"from": "0", "text": "OFF"}, {"from": "1", "text": "STANDBY"},
                  {"from": "2", "text": "OPERATE"}],
        "attach": {"table": "pcf", "name": "UTMODE"}})
    assert r.status_code == 200, r.text
    r = client.post(f"/api/projects/{pid}/wizards/calibration", json={
        "kind": "caf", "ident": "UTVCAL", "descr": "Voltage cal", "unit": "V",
        "engfmt": "R", "rawfmt": "U",
        "points": [{"raw": "0", "eng": "0.0"}, {"raw": "65535", "eng": "32.0"}],
        "attach": {"table": "pcf", "name": "UTVOLT1"}})
    assert r.status_code == 200, r.text

    # --- limit check on the voltage -----------------------------------------
    r = client.post(f"/api/projects/{pid}/wizards/limit", json={
        "param": "UTVOLT1", "inter": "C", "codin": "R",
        "checks": [{"type": "S", "low": "20.0", "high": "30.0"},
                   {"type": "H", "low": "18.0", "high": "32.0"}]})
    assert r.status_code == 200, r.text

    # --- TC command wizard: mode command with verification ------------------
    r = client.post(f"/api/projects/{pid}/wizards/tc-command", json={
        "cname": "UTSETMOD", "descr": "Set unit mode", "apid": 100,
        "type": 8, "stype": 1,
        "params": [
            {"pname": "UTFID", "descr": "Function ID", "ptc": 3, "pfc": 12,
             "kind": "fixed", "value": "42"},
            {"pname": "UTTGTMOD", "descr": "Target mode", "ptc": 2, "pfc": 8,
             "kind": "editable"},
        ],
        "verification": {"acceptance": True, "completion": True}})
    assert r.status_code == 200, r.text
    assert r.json()["ack"] == 9
    assert r.json()["app_data_bits"] == 24

    # --- validation must be clean (no errors, no warnings) ------------------
    v = client.post(f"/api/projects/{pid}/validate").json()
    problems = [f for f in v["findings"] if f["severity"] in ("error", "warning")]
    assert problems == [], problems

    # --- row CRUD with optimistic concurrency -------------------------------
    rows = client.get(f"/api/projects/{pid}/tables/pcf/rows").json()
    target = rows[0]
    r = client.put(f"/api/projects/{pid}/tables/pcf/rows/{target['id']}",
                   json={"data": {**target["data"], "PCF_DESCR": "Edited"},
                         "version": target["version"]})
    assert r.status_code == 200
    r = client.put(f"/api/projects/{pid}/tables/pcf/rows/{target['id']}",
                   json={"data": target["data"], "version": target["version"]})
    assert r.status_code == 409  # stale version rejected

    # --- export -> import into fresh project -> export: identical -----------
    exp1 = client.get(f"/api/projects/{pid}/export")
    assert exp1.status_code == 200
    files1 = zip_contents(exp1.content)
    assert set(files1) >= {"pcf.dat", "pid.dat", "ccf.dat", "vdf.dat"}
    assert str(spid).encode() in files1["pid.dat"]

    r = client.post("/api/projects", json={"name": "RoundTrip", "profile": "ccs5",
                                           "bootstrap": False})
    pid2 = r.json()["id"]
    r = client.post(f"/api/projects/{pid2}/import",
                    files={"file": ("mib.zip", exp1.content, "application/zip")},
                    data={"mode": "replace-all"})
    assert r.status_code == 200, r.text
    assert r.json()["imported"] is True

    exp2 = client.get(f"/api/projects/{pid2}/export")
    files2 = zip_contents(exp2.content)
    assert files1 == files2, "round-trip export differs"

    # dry-run import must not modify anything
    before = client.get(f"/api/projects/{pid2}").json()["total_rows"]
    r = client.post(f"/api/projects/{pid2}/import",
                    files={"file": ("mib.zip", exp1.content, "application/zip")},
                    data={"mode": "append", "dry_run": "true"})
    assert r.json()["dry_run"] is True
    assert client.get(f"/api/projects/{pid2}").json()["total_rows"] == before


def test_user_management_and_roles(client):
    r = client.post("/api/users", json={"username": "viewer1", "password": "secret1"})
    assert r.status_code == 201
    r = client.post("/api/projects", json={"name": "RoleTest", "bootstrap": False})
    pid = r.json()["id"]
    r = client.post(f"/api/projects/{pid}/members",
                    json={"username": "viewer1", "role": "viewer"})
    assert r.status_code == 201

    with TestClient(app) as viewer:
        viewer.post("/api/auth/login", json={"username": "viewer1", "password": "secret1"})
        assert viewer.get(f"/api/projects/{pid}").status_code == 200
        r = viewer.post(f"/api/projects/{pid}/tables/pcf/rows", json={"data": {}})
        assert r.status_code == 403   # viewers cannot write
        assert viewer.get("/api/users").status_code == 403  # not admin
