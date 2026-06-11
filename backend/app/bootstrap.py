"""Starter content for new projects: vdf record, a standard PUS TC packet
header (tcp/pcpc/pcdf) and generic verification stages (cvs), so users can
define commands without first hand-crafting the CCSDS/PUS header layout."""

from sqlalchemy.orm import Session

from . import mibstore

PUS_HEADER_ID = "PUSTC"

_PCPC = [
    {"PCPC_PNAME": "APID", "PCPC_DESC": "Application process ID", "PCPC_CODE": "U"},
    {"PCPC_PNAME": "SEQCNT", "PCPC_DESC": "Sequence counter", "PCPC_CODE": "U"},
    {"PCPC_PNAME": "PKTLEN", "PCPC_DESC": "Packet length", "PCPC_CODE": "U"},
    {"PCPC_PNAME": "ACK", "PCPC_DESC": "Acknowledgement flags", "PCPC_CODE": "U"},
    {"PCPC_PNAME": "TYPE", "PCPC_DESC": "Service type", "PCPC_CODE": "U"},
    {"PCPC_PNAME": "STYPE", "PCPC_DESC": "Service subtype", "PCPC_CODE": "U"},
]

# Standard 6-byte CCSDS TC primary header + 3-byte PUS(-A style) data field
# header. Bit offsets from the start of the packet; total header = 72 bits.
_PCDF = [
    ("Version number",        "F", 3,  0, "",       "0"),
    ("Packet type (TC=1)",    "F", 1,  3, "",       "1"),
    ("Data field hdr flag",   "F", 1,  4, "",       "1"),
    ("APID",                  "A", 11, 5, "APID",   "0"),
    ("Sequence flags",        "F", 2,  16, "",      "3"),
    ("Sequence counter",      "P", 14, 18, "SEQCNT", "0"),
    ("Packet length",         "P", 16, 32, "PKTLEN", "0"),
    ("PUS version + sec flag", "F", 4, 48, "", "1"),
    ("Acknowledgement flags", "K", 4,  52, "ACK",   "0"),
    ("Service type",          "T", 8,  56, "TYPE",  "0"),
    ("Service subtype",       "S", 8,  64, "STYPE", "0"),
]

PUS_HEADER_BITS = 72  # application data starts after this in the TC packet

_CVS = [
    {"CVS_ID": "1", "CVS_TYPE": "A", "CVS_SOURCE": "R", "CVS_START": "0",
     "CVS_INTERVAL": "60", "CVS_SPID": ""},
    {"CVS_ID": "2", "CVS_TYPE": "S", "CVS_SOURCE": "R", "CVS_START": "0",
     "CVS_INTERVAL": "60", "CVS_SPID": ""},
    {"CVS_ID": "3", "CVS_TYPE": "C", "CVS_SOURCE": "R", "CVS_START": "0",
     "CVS_INTERVAL": "120", "CVS_SPID": ""},
]


def bootstrap_project(db: Session, project_id: int, name: str):
    vdf_name = "".join(ch for ch in name.upper() if ch.isalnum())[:8] or "MIB"
    mibstore.insert_rows(db, project_id, "vdf", [{
        "VDF_NAME": vdf_name, "VDF_COMMENT": "Created with SCOS MIB Creator",
        "VDF_DOMAINID": "", "VDF_RELEASE": "0", "VDF_ISSUE": "1",
    }])
    mibstore.insert_rows(db, project_id, "tcp", [{
        "TCP_ID": PUS_HEADER_ID, "TCP_DESC": "Standard PUS TC header",
    }])
    mibstore.insert_rows(db, project_id, "pcpc", _PCPC)
    mibstore.insert_rows(db, project_id, "pcdf", [{
        "PCDF_TCNAME": PUS_HEADER_ID, "PCDF_DESC": desc, "PCDF_TYPE": ftype,
        "PCDF_LEN": str(length), "PCDF_BIT": str(bit), "PCDF_PNAME": pname,
        "PCDF_VALUE": value, "PCDF_RADIX": "D",
    } for desc, ftype, length, bit, pname, value in _PCDF])
    mibstore.insert_rows(db, project_id, "cvs", _CVS)
