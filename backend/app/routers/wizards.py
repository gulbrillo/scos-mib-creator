"""Wizard endpoints: create coherent multi-table MIB content in one atomic
operation (packet + parameters + layout; command + arguments + verification;
calibrations; limit checks). All derived fields (SPIDs, bit offsets, counts,
PIC criteria) are computed here so users never juggle them by hand."""

import math

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from .. import mibstore
from ..bootstrap import PUS_HEADER_BITS, bootstrap_project
from ..db import get_db
from ..models import User
from ..security import get_current_user, get_project_for
from mibschema.pus.types import bit_width

router = APIRouter(prefix="/api/projects/{project_id}/wizards", tags=["wizards"])

CCSDS_PRIMARY_BYTES = 6


# ---------------------------------------------------------------- TM packet

class PacketParam(BaseModel):
    name: str
    descr: str = ""
    ptc: int
    pfc: int
    unit: str = ""
    is_pi1: bool = False     # this field carries the identification value (e.g. SID)


class PacketWizard(BaseModel):
    descr: str
    apid: int
    type: int
    stype: int
    spid: int | None = None
    pi1_val: int | None = None
    dfh_size: int = 10
    has_time: bool = True
    interval_ms: int | None = None
    packet_name: str = ""
    has_pec: bool = True
    params: list[PacketParam] = Field(default_factory=list)


def _param_width(db: Session, project_id: int, p: PacketParam) -> int:
    existing = mibstore.find_value_rows(db, project_id, "pcf", "PCF_NAME", p.name)
    if existing:
        d = existing[0].data
        ptc, pfc = int(d.get("PCF_PTC") or p.ptc), int(d.get("PCF_PFC") or p.pfc)
    else:
        ptc, pfc = p.ptc, p.pfc
    w = bit_width(ptc, pfc)
    if not w:
        raise HTTPException(400, f"Parameter '{p.name}': PTC {ptc}/PFC {pfc} has no "
                                 f"fixed width and cannot be placed in a fixed packet.")
    return w


@router.post("/tm-packet")
def tm_packet(project_id: int, req: PacketWizard, db: Session = Depends(get_db),
              user: User = Depends(get_current_user)):
    get_project_for(db, project_id, user, write=True)
    created = {"pcf": 0, "plf": 0, "pid": 0, "pic": 0, "tpcf": 0}

    spids = {int(v) for v in mibstore.column_values(db, project_id, "pid", "PID_SPID")}
    spid = req.spid or (max(spids) + 1 if spids else 1000)
    if spid in spids:
        raise HTTPException(409, f"SPID {spid} is already in use.")

    existing_pcf = mibstore.column_values(db, project_id, "pcf", "PCF_NAME")
    cursor = (CCSDS_PRIMARY_BYTES + req.dfh_size) * 8
    pi1_off_bits: int | None = None
    pi1_wid: int | None = None
    plf_rows, pcf_rows = [], []
    for p in req.params:
        width = _param_width(db, project_id, p)
        if p.is_pi1:
            if cursor % 8 != 0:
                raise HTTPException(400, f"Identification field '{p.name}' must start "
                                         f"on a byte boundary (currently bit {cursor}).")
            pi1_off_bits, pi1_wid = cursor, width
        if p.name not in existing_pcf:
            pcf_rows.append({
                "PCF_NAME": p.name, "PCF_DESCR": p.descr, "PCF_PID": "",
                "PCF_UNIT": p.unit, "PCF_PTC": str(p.ptc), "PCF_PFC": str(p.pfc),
                "PCF_WIDTH": "", "PCF_VALID": "", "PCF_RELATED": "",
                "PCF_CATEG": "N", "PCF_NATUR": "R", "PCF_CURTX": "",
                "PCF_INTER": "F", "PCF_USCON": "N", "PCF_DECIM": "",
                "PCF_PARVAL": "", "PCF_SUBSYS": "", "PCF_VALPAR": "",
                "PCF_SPTYPE": "", "PCF_CORR": "", "PCF_OBTID": "",
                "PCF_DARC": "", "PCF_ENDIAN": "",
            })
            existing_pcf.add(p.name)
        plf_rows.append({
            "PLF_NAME": p.name, "PLF_SPID": str(spid),
            "PLF_OFFBY": str(cursor // 8), "PLF_OFFBI": str(cursor % 8),
            "PLF_NBOCC": "", "PLF_LGOCC": "", "PLF_TIME": "", "PLF_TDOCC": "",
        })
        cursor += width

    pid_row = {
        "PID_TYPE": str(req.type), "PID_STYPE": str(req.stype), "PID_APID": str(req.apid),
        "PID_PI1_VAL": "" if req.pi1_val is None else str(req.pi1_val),
        "PID_PI2_VAL": "", "PID_SPID": str(spid), "PID_DESCR": req.descr,
        "PID_UNIT": "", "PID_TPSD": "-1", "PID_DFHSIZE": str(req.dfh_size),
        "PID_TIME": "Y" if req.has_time else "N",
        "PID_INTER": "" if not req.interval_ms else str(req.interval_ms),
        "PID_VALID": "Y", "PID_CHECK": "0", "PID_EVENT": "N", "PID_EVID": "",
    }

    if req.pi1_val is not None:
        if pi1_off_bits is None:
            raise HTTPException(400, "A PI1 value is set but no parameter is marked as "
                                     "the identification field (is_pi1).")
        # one PIC record per (type, subtype); create if absent
        pic_rows = mibstore.table_rows(db, project_id, "pic")
        if not any(r.data.get("PIC_TYPE") == str(req.type)
                   and r.data.get("PIC_STYPE") == str(req.stype) for r in pic_rows):
            mibstore.insert_rows(db, project_id, "pic", [{
                "PIC_TYPE": str(req.type), "PIC_STYPE": str(req.stype),
                "PIC_PI1_OFF": str(pi1_off_bits // 8), "PIC_PI1_WID": str(pi1_wid),
                "PIC_PI2_OFF": "-1", "PIC_PI2_WID": "0", "PIC_APID": "",
            }])
            created["pic"] = 1

    size_bytes = math.ceil(cursor / 8) + (2 if req.has_pec else 0)
    tpcf_row = {"TPCF_SPID": str(spid),
                "TPCF_NAME": (req.packet_name or "")[:12], "TPCF_SIZE": str(size_bytes)}

    if pcf_rows:
        mibstore.insert_rows(db, project_id, "pcf", pcf_rows)
    mibstore.insert_rows(db, project_id, "pid", [pid_row])
    if plf_rows:
        mibstore.insert_rows(db, project_id, "plf", plf_rows)
    mibstore.insert_rows(db, project_id, "tpcf", [tpcf_row])
    created.update(pcf=len(pcf_rows), plf=len(plf_rows), pid=1, tpcf=1)
    db.commit()
    return {"spid": spid, "size_bytes": size_bytes, "created": created}


# ---------------------------------------------------------------- TC command

class CommandParam(BaseModel):
    pname: str = ""
    descr: str = ""
    ptc: int = 3
    pfc: int = 4
    kind: str = "editable"   # editable | fixed | area
    bits: int | None = None  # only for areas
    value: str = ""
    inter: str = "R"
    unit: str = ""
    defval: str = ""


class CommandVerification(BaseModel):
    acceptance: bool = True
    start: bool = False
    completion: bool = True


class CommandWizard(BaseModel):
    cname: str
    descr: str
    descr2: str = ""
    apid: int
    type: int
    stype: int
    critical: bool = False
    pktid: str = ""
    params: list[CommandParam] = Field(default_factory=list)
    verification: CommandVerification = Field(default_factory=CommandVerification)


def _dispfmt(ptc: int) -> str:
    return {4: "I", 5: "R", 8: "A", 9: "T", 10: "D"}.get(ptc, "U")


@router.post("/tc-command")
def tc_command(project_id: int, req: CommandWizard, db: Session = Depends(get_db),
               user: User = Depends(get_current_user)):
    get_project_for(db, project_id, user, write=True)
    cname = req.cname.strip()
    if not cname:
        raise HTTPException(400, "Command name must not be empty")
    if mibstore.find_value_rows(db, project_id, "ccf", "CCF_CNAME", cname):
        raise HTTPException(409, f"Command '{cname}' already exists.")

    pktid = req.pktid
    if not pktid:
        tcps = mibstore.table_rows(db, project_id, "tcp")
        if not tcps:
            raise HTTPException(400, "No TC packet header defined yet. Create one first "
                                     "(Project page -> 'Create standard PUS header').")
        pktid = tcps[0].data["TCP_ID"]

    existing_cpc = mibstore.column_values(db, project_id, "cpc", "CPC_PNAME")
    cpc_rows, cdf_rows = [], []
    cursor = 0
    for p in req.params:
        if p.kind == "area":
            if not p.bits or not p.value:
                raise HTTPException(400, "Fixed areas need a bit length and a value.")
            cdf_rows.append({
                "CDF_CNAME": cname, "CDF_ELTYPE": "A", "CDF_DESCR": p.descr,
                "CDF_ELLEN": str(p.bits), "CDF_BIT": str(cursor), "CDF_GRPSIZE": "",
                "CDF_PNAME": "", "CDF_INTER": p.inter or "R", "CDF_VALUE": p.value,
                "CDF_TMID": "",
            })
            cursor += p.bits
            continue
        if not p.pname.strip():
            raise HTTPException(400, "Command parameters need a name.")
        width = bit_width(p.ptc, p.pfc)
        if not width:
            raise HTTPException(400, f"Parameter '{p.pname}': PTC {p.ptc}/PFC {p.pfc} "
                                     f"has variable width; enter the layout manually in cdf "
                                     f"for variable-length arguments.")
        if p.pname not in existing_cpc:
            cpc_rows.append({
                "CPC_PNAME": p.pname, "CPC_DESCR": p.descr,
                "CPC_PTC": str(p.ptc), "CPC_PFC": str(p.pfc),
                "CPC_DISPFMT": _dispfmt(p.ptc), "CPC_RADIX": "D", "CPC_UNIT": p.unit,
                "CPC_CATEG": "N", "CPC_PRFREF": "", "CPC_CCAREF": "", "CPC_PAFREF": "",
                "CPC_INTER": "R", "CPC_DEFVAL": p.defval, "CPC_CORR": "",
                "CPC_OBTID": "", "CPC_ENDIAN": "",
            })
            existing_cpc.add(p.pname)
        cdf_rows.append({
            "CDF_CNAME": cname, "CDF_ELTYPE": "E" if p.kind == "editable" else "F",
            "CDF_DESCR": "", "CDF_ELLEN": str(width), "CDF_BIT": str(cursor),
            "CDF_GRPSIZE": "", "CDF_PNAME": p.pname, "CDF_INTER": p.inter or "R",
            "CDF_VALUE": p.value, "CDF_TMID": "",
        })
        cursor += width

    ack = (1 if req.verification.acceptance else 0) \
        + (2 if req.verification.start else 0) \
        + (8 if req.verification.completion else 0)
    ccf_row = {
        "CCF_CNAME": cname, "CCF_DESCR": req.descr, "CCF_DESCR2": req.descr2,
        "CCF_CTYPE": "", "CCF_CRITICAL": "Y" if req.critical else "N",
        "CCF_PKTID": pktid, "CCF_TYPE": str(req.type), "CCF_STYPE": str(req.stype),
        "CCF_APID": str(req.apid), "CCF_NPARS": str(len(cdf_rows)),
        "CCF_PLAN": "N", "CCF_EXEC": "Y", "CCF_ILSCOPE": "N", "CCF_ILSTAGE": "C",
        "CCF_SUBSYS": "", "CCF_HIPRI": "N", "CCF_MAPID": "", "CCF_DEFSET": "",
        "CCF_RAPID": "", "CCF_ACK": str(ack), "CCF_SUBSCHEDID": "",
    }

    # verification stages: reuse a service-1 stage of the right type, else create
    cvp_rows = []
    wanted = [("A", req.verification.acceptance), ("S", req.verification.start),
              ("C", req.verification.completion)]
    cvs_rows = mibstore.table_rows(db, project_id, "cvs")
    cvs_ids = [int(r.data["CVS_ID"]) for r in cvs_rows if str(r.data.get("CVS_ID", "")).lstrip("-").isdigit()]
    next_id = (max(cvs_ids) + 1) if cvs_ids else 1
    created_cvs = 0
    for stage_type, enabled in wanted:
        if not enabled:
            continue
        match = next((r for r in cvs_rows
                      if r.data.get("CVS_TYPE") == stage_type
                      and r.data.get("CVS_SOURCE") == "R"), None)
        if match:
            stage_id = match.data["CVS_ID"]
        else:
            stage_id = str(next_id)
            next_id += 1
            mibstore.insert_rows(db, project_id, "cvs", [{
                "CVS_ID": stage_id, "CVS_TYPE": stage_type, "CVS_SOURCE": "R",
                "CVS_START": "0", "CVS_INTERVAL": "120" if stage_type == "C" else "60",
                "CVS_SPID": "",
            }])
            created_cvs += 1
        cvp_rows.append({"CVP_TASK": cname, "CVP_TYPE": "C", "CVP_CVSID": str(stage_id)})

    if cpc_rows:
        mibstore.insert_rows(db, project_id, "cpc", cpc_rows)
    mibstore.insert_rows(db, project_id, "ccf", [ccf_row])
    if cdf_rows:
        mibstore.insert_rows(db, project_id, "cdf", cdf_rows)
    if cvp_rows:
        mibstore.insert_rows(db, project_id, "cvp", cvp_rows)
    db.commit()
    return {"cname": cname, "ack": ack, "app_data_bits": cursor,
            "created": {"cpc": len(cpc_rows), "cdf": len(cdf_rows), "ccf": 1,
                        "cvp": len(cvp_rows), "cvs": created_cvs}}


# ---------------------------------------------------------------- calibration

class CalPoint(BaseModel):
    raw: str = ""
    eng: str = ""


class CalText(BaseModel):
    from_: str = Field("", alias="from")
    to: str = ""
    text: str = ""

    model_config = {"populate_by_name": True}


class CalRange(BaseModel):
    min: str = ""
    max: str = ""


class CalAttach(BaseModel):
    table: str  # pcf | cpc
    name: str


class CalibrationWizard(BaseModel):
    kind: str            # caf | txf | mcf | lgf | cca | paf | prf
    ident: str
    descr: str = ""
    unit: str = ""
    engfmt: str = "R"
    rawfmt: str = "U"
    radix: str = "D"
    inter: str = "F"
    points: list[CalPoint] = Field(default_factory=list)
    texts: list[CalText] = Field(default_factory=list)
    ranges: list[CalRange] = Field(default_factory=list)
    coeffs: list[str] = Field(default_factory=list)
    attach: CalAttach | None = None


@router.post("/calibration")
def calibration(project_id: int, req: CalibrationWizard, db: Session = Depends(get_db),
                user: User = Depends(get_current_user)):
    get_project_for(db, project_id, user, write=True)
    ident = req.ident.strip()
    if not ident:
        raise HTTPException(400, "Calibration name must not be empty")
    k = req.kind
    key_col = {"caf": "CAF_NUMBR", "txf": "TXF_NUMBR", "mcf": "MCF_IDENT",
               "lgf": "LGF_IDENT", "cca": "CCA_NUMBR", "paf": "PAF_NUMBR",
               "prf": "PRF_NUMBR"}.get(k)
    if key_col is None:
        raise HTTPException(400, f"Unknown calibration kind '{k}'")
    if mibstore.find_value_rows(db, project_id, k, key_col, ident):
        raise HTTPException(409, f"A {k} calibration named '{ident}' already exists.")

    if k == "caf":
        if len(req.points) < 2:
            raise HTTPException(400, "A numerical calibration needs at least 2 points.")
        mibstore.insert_rows(db, project_id, "caf", [{
            "CAF_NUMBR": ident, "CAF_DESCR": req.descr, "CAF_ENGFMT": req.engfmt,
            "CAF_RAWFMT": req.rawfmt, "CAF_RADIX": req.radix, "CAF_UNIT": req.unit,
            "CAF_NCURVE": str(len(req.points)), "CAF_INTER": req.inter}])
        mibstore.insert_rows(db, project_id, "cap", [
            {"CAP_NUMBR": ident, "CAP_XVALS": p.raw, "CAP_YVALS": p.eng}
            for p in req.points])
    elif k == "cca":
        if len(req.points) < 2:
            raise HTTPException(400, "A de-calibration curve needs at least 2 points.")
        mibstore.insert_rows(db, project_id, "cca", [{
            "CCA_NUMBR": ident, "CCA_DESCR": req.descr, "CCA_ENGFMT": req.engfmt,
            "CCA_RAWFMT": req.rawfmt, "CCA_RADIX": req.radix, "CCA_UNIT": req.unit,
            "CCA_NCURVE": str(len(req.points))}])
        mibstore.insert_rows(db, project_id, "ccs", [
            {"CCS_NUMBR": ident, "CCS_XVALS": p.eng, "CCS_YVALS": p.raw}
            for p in req.points])
    elif k == "txf":
        if not req.texts:
            raise HTTPException(400, "A textual calibration needs at least one entry.")
        mibstore.insert_rows(db, project_id, "txf", [{
            "TXF_NUMBR": ident, "TXF_DESCR": req.descr, "TXF_RAWFMT": req.rawfmt,
            "TXF_NALIAS": str(len(req.texts))}])
        mibstore.insert_rows(db, project_id, "txp", [
            {"TXP_NUMBR": ident, "TXP_FROM": t.from_, "TXP_TO": t.to or t.from_,
             "TXP_ALTXT": t.text} for t in req.texts])
    elif k == "paf":
        if not req.texts:
            raise HTTPException(400, "An alias set needs at least one entry.")
        mibstore.insert_rows(db, project_id, "paf", [{
            "PAF_NUMBR": ident, "PAF_DESCR": req.descr, "PAF_RAWFMT": req.rawfmt,
            "PAF_NALIAS": str(len(req.texts))}])
        mibstore.insert_rows(db, project_id, "pas", [
            {"PAS_NUMBR": ident, "PAS_ALTXT": t.text, "PAS_ALVAL": t.from_}
            for t in req.texts])
    elif k in ("mcf", "lgf"):
        coeffs = (req.coeffs + ["", "", "", "", ""])[:5]
        if not coeffs[0]:
            raise HTTPException(400, "Coefficient A0 is required.")
        prefix = k.upper()
        mibstore.insert_rows(db, project_id, k, [{
            f"{prefix}_IDENT": ident, f"{prefix}_DESCR": req.descr,
            f"{prefix}_POL1": coeffs[0], f"{prefix}_POL2": coeffs[1],
            f"{prefix}_POL3": coeffs[2], f"{prefix}_POL4": coeffs[3],
            f"{prefix}_POL5": coeffs[4]}])
    elif k == "prf":
        if not req.ranges:
            raise HTTPException(400, "A range set needs at least one range.")
        mibstore.insert_rows(db, project_id, "prf", [{
            "PRF_NUMBR": ident, "PRF_DESCR": req.descr, "PRF_INTER": req.inter
            if req.inter in ("R", "E") else "R",
            "PRF_DSPFMT": req.engfmt if req.engfmt in ("A", "I", "U", "R", "T", "D") else "U",
            "PRF_RADIX": req.radix, "PRF_NRANGE": str(len(req.ranges)),
            "PRF_UNIT": req.unit}])
        mibstore.insert_rows(db, project_id, "prv", [
            {"PRV_NUMBR": ident, "PRV_MINVAL": r.min, "PRV_MAXVAL": r.max}
            for r in req.ranges])

    attached = False
    if req.attach:
        rows = mibstore.find_value_rows(db, project_id, req.attach.table,
                                        "PCF_NAME" if req.attach.table == "pcf" else "CPC_PNAME",
                                        req.attach.name)
        if not rows:
            raise HTTPException(404, f"Cannot attach: {req.attach.table} record "
                                     f"'{req.attach.name}' not found.")
        row = rows[0]
        data = dict(row.data)
        if req.attach.table == "pcf":
            data["PCF_CURTX"] = ident
            data["PCF_CATEG"] = "S" if k == "txf" else "N"
        else:
            if k == "cca":
                data["CPC_CCAREF"], data["CPC_CATEG"] = ident, "C"
            elif k == "paf":
                data["CPC_PAFREF"], data["CPC_CATEG"] = ident, "T"
            elif k == "prf":
                data["CPC_PRFREF"] = ident
            else:
                raise HTTPException(400, f"A {k} calibration cannot be attached to a "
                                         f"command parameter.")
        row.data = data
        row.version += 1
        attached = True
    db.commit()
    return {"ident": ident, "kind": k, "attached": attached}


# ---------------------------------------------------------------- limit check

class LimitCheck(BaseModel):
    type: str = "S"          # S | H | D | E | C
    low: str = ""
    high: str = ""
    rlchk: str = ""
    valpar: str = ""


class LimitWizard(BaseModel):
    param: str
    nbchck: int = 1
    inter: str = "C"         # C | U
    codin: str = "I"         # I | R | A
    checks: list[LimitCheck]


@router.post("/limit")
def limit(project_id: int, req: LimitWizard, db: Session = Depends(get_db),
          user: User = Depends(get_current_user)):
    get_project_for(db, project_id, user, write=True)
    if not req.checks:
        raise HTTPException(400, "At least one check is required.")
    if not mibstore.find_value_rows(db, project_id, "pcf", "PCF_NAME", req.param):
        raise HTTPException(404, f"Parameter '{req.param}' not found in pcf.")
    if mibstore.find_value_rows(db, project_id, "ocf", "OCF_NAME", req.param):
        raise HTTPException(409, f"Parameter '{req.param}' already has limit checks. "
                                 f"Edit them in the TM limit checks editor.")
    mibstore.insert_rows(db, project_id, "ocf", [{
        "OCF_NAME": req.param, "OCF_NBCHCK": str(req.nbchck),
        "OCF_NBOOL": str(len(req.checks)), "OCF_INTER": req.inter,
        "OCF_CODIN": req.codin}])
    mibstore.insert_rows(db, project_id, "ocp", [{
        "OCP_NAME": req.param, "OCP_POS": str(i + 1), "OCP_TYPE": c.type,
        "OCP_LVALU": c.low, "OCP_HVALU": c.high, "OCP_RLCHK": c.rlchk,
        "OCP_VALPAR": c.valpar} for i, c in enumerate(req.checks)])
    db.commit()
    return {"param": req.param, "checks": len(req.checks)}


# ------------------------------------------------------------- PUS TC header

@router.post("/pus-header")
def pus_header(project_id: int, db: Session = Depends(get_db),
               user: User = Depends(get_current_user)):
    """Create the standard PUS TC header set (tcp/pcpc/pcdf + cvs stages) in a
    project that does not have one yet (e.g. created without bootstrap)."""
    project = get_project_for(db, project_id, user, write=True)
    if mibstore.table_rows(db, project_id, "tcp"):
        raise HTTPException(409, "A TC packet header already exists in this project.")
    bootstrap_project(db, project_id, project.name)
    # bootstrap also writes a vdf record; drop the duplicate if one existed
    vdf = mibstore.table_rows(db, project_id, "vdf")
    for extra in vdf[1:]:
        db.delete(extra)
    db.commit()
    return {"ok": True, "header_bits": PUS_HEADER_BITS}
