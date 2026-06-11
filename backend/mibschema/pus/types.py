"""SCOS-2000 parameter types (PTC/PFC), per Appendix A of the MIB ICD.

The PTC (Parameter Type Code) selects the kind of value; the PFC (Parameter
Format Code) selects the size/encoding variant. This module is the single
source for the PTC/PFC picker in the UI and for bit-width computations used
by the packet/command layout builders.
"""

from __future__ import annotations

# Catalog entries:
#   ptc        : the PTC value
#   name       : engineer-friendly name
#   help       : guidance for newcomers
#   pfc        : "fixed" list of {pfc,bits,label} OR "rule" with formula
#   tm / tc    : usable on the monitoring (TM) / commanding (TC) side
PTC_CATALOG: list[dict] = [
    {
        "ptc": 1, "name": "Boolean", "tm": True, "tc": True,
        "help": "A single bit: 0 = False, 1 = True. Use for on/off flags.",
        "pfc": [{"pfc": 0, "bits": 1, "label": "1 bit"}],
    },
    {
        "ptc": 2, "name": "Enumerated", "tm": True, "tc": True,
        "help": "An unsigned integer whose values stand for named states "
                "(e.g. 0=IDLE, 1=ACQUIRING, 2=ERROR). Combine with a textual "
                "calibration so operators see the state names. Width 1-32 bits = PFC.",
        "pfc_rule": {"min": 1, "max": 32, "bits": "pfc",
                     "label": "PFC = number of bits (1-32)"},
    },
    {
        "ptc": 3, "name": "Unsigned integer", "tm": True, "tc": True,
        "help": "Non-negative whole numbers. Pick the PFC matching the field "
                "width in your packet layout. The most common sizes: 8 bits = PFC 4, "
                "16 bits = PFC 12, 32 bits = PFC 14.",
        "pfc": [{"pfc": n, "bits": n + 4, "label": f"{n + 4} bits"} for n in range(13)]
               + [{"pfc": 13, "bits": 24, "label": "24 bits"},
                  {"pfc": 14, "bits": 32, "label": "32 bits"},
                  {"pfc": 15, "bits": 48, "label": "48 bits (not supported by SCOS-2000)"},
                  {"pfc": 16, "bits": 64, "label": "64 bits (not supported by SCOS-2000)"}],
    },
    {
        "ptc": 4, "name": "Signed integer", "tm": True, "tc": True,
        "help": "Whole numbers including negatives (two's complement). Same PFC "
                "scheme as unsigned integers: 8 bits = PFC 4, 16 bits = PFC 12, "
                "32 bits = PFC 14.",
        "pfc": [{"pfc": n, "bits": n + 4, "label": f"{n + 4} bits"} for n in range(13)]
               + [{"pfc": 13, "bits": 24, "label": "24 bits"},
                  {"pfc": 14, "bits": 32, "label": "32 bits"},
                  {"pfc": 15, "bits": 48, "label": "48 bits (not supported by SCOS-2000)"},
                  {"pfc": 16, "bits": 64, "label": "64 bits (not supported by SCOS-2000)"}],
    },
    {
        "ptc": 5, "name": "Real (floating point)", "tm": True, "tc": True,
        "help": "Floating-point numbers. PFC 1 = IEEE 754 single (32 bit), "
                "PFC 2 = IEEE 754 double (64 bit). PFC 3/4 are MIL-STD-1750A "
                "formats used by some on-board computers.",
        "pfc": [{"pfc": 1, "bits": 32, "label": "32-bit IEEE single"},
                {"pfc": 2, "bits": 64, "label": "64-bit IEEE double"},
                {"pfc": 3, "bits": 32, "label": "32-bit MIL-STD-1750A"},
                {"pfc": 4, "bits": 48, "label": "48-bit MIL-STD-1750A (TC only)"}],
    },
    {
        "ptc": 6, "name": "Bit string", "tm": True, "tc": False,
        "help": "A raw group of bits (1-32), handled by SCOS-2000 as an unsigned "
                "integer of that width. TM only. PFC = number of bits; PFC 0 "
                "(variable length) is not supported by SCOS-2000.",
        "pfc_rule": {"min": 1, "max": 32, "bits": "pfc",
                     "label": "PFC = number of bits (1-32)"},
    },
    {
        "ptc": 7, "name": "Octet string (bytes)", "tm": True, "tc": True,
        "help": "A block of raw bytes. PFC = number of octets for fixed length; "
                "PFC 0 = variable length (command parameters only). Useful for "
                "memory dumps or opaque payloads, e.g. a raw MIL-1553 message.",
        "pfc_rule": {"min": 0, "max": 4096, "bits": "pfc*8",
                     "label": "PFC = number of bytes (0 = variable, TC only)"},
    },
    {
        "ptc": 8, "name": "Character string (ASCII)", "tm": True, "tc": True,
        "help": "ASCII text. PFC = number of characters for fixed length; PFC 0 = "
                "variable length (command parameters only). TM text parameters "
                "need PCF_CATEG=T.",
        "pfc_rule": {"min": 0, "max": 4096, "bits": "pfc*8",
                     "label": "PFC = number of characters (0 = variable, TC only)"},
    },
    {
        "ptc": 9, "name": "Absolute time", "tm": True, "tc": True,
        "help": "A time stamp. CUC formats encode seconds (coarse) and sub-seconds "
                "(fine) since the mission epoch; CDS formats encode day/ms-of-day. "
                "Pick the variant matching your on-board time format.",
        "pfc": [{"pfc": 1, "bits": 48, "label": "CDS, day + ms (6 bytes, TC only in SCOS<5)"},
                {"pfc": 2, "bits": 64, "label": "CDS, day + ms + microseconds (8 bytes, TC only)"}]
               + [{"pfc": pfc, "bits": 8 * octets,
                   "label": f"CUC, {coarse} byte(s) coarse + {fine} byte(s) fine ({octets} bytes)"}
                  for pfc, coarse, fine, octets in [
                      (3, 1, 0, 1), (4, 1, 1, 2), (5, 1, 2, 3), (6, 1, 3, 4),
                      (7, 2, 0, 2), (8, 2, 1, 3), (9, 2, 2, 4), (10, 2, 3, 5),
                      (11, 3, 0, 3), (12, 3, 1, 4), (13, 3, 2, 5), (14, 3, 3, 6),
                      (15, 4, 0, 4), (16, 4, 1, 5), (17, 4, 2, 6), (18, 4, 3, 7)]]
               + [{"pfc": 30, "bits": 64, "label": "Unix time, 4 bytes s + 4 bytes µs (not in PUS)"}],
    },
    {
        "ptc": 10, "name": "Relative time", "tm": True, "tc": True,
        "help": "A time duration (CUC format): coarse seconds + fine sub-seconds.",
        "pfc": [{"pfc": pfc, "bits": 8 * octets,
                 "label": f"CUC, {coarse} byte(s) coarse + {fine} byte(s) fine ({octets} bytes)"}
                for pfc, coarse, fine, octets in [
                    (3, 1, 0, 1), (4, 1, 1, 2), (5, 1, 2, 3), (6, 1, 3, 4),
                    (7, 2, 0, 2), (8, 2, 1, 3), (9, 2, 2, 4), (10, 2, 3, 5),
                    (11, 3, 0, 3), (12, 3, 1, 4), (13, 3, 2, 5), (14, 3, 3, 6),
                    (15, 4, 0, 4), (16, 4, 1, 5), (17, 4, 2, 6), (18, 4, 3, 7)]],
    },
    {
        "ptc": 11, "name": "Deduced", "tm": True, "tc": True,
        "help": "Advanced: the actual type is taken at runtime from another "
                "(preceding) parameter in the same packet — used for generic "
                "'parameter ID + value' packets like PUS service 20. PFC 0 = "
                "variable width; PFC>0 fixes the width (TC only).",
        "pfc_rule": {"min": 0, "max": 64, "bits": "pfc",
                     "label": "PFC 0 = deduced width; >0 = fixed width in bits (TC only)"},
    },
    {
        "ptc": 13, "name": "Saved synthetic", "tm": True, "tc": False,
        "help": "Advanced, ground-only: a synthetic parameter whose computed value "
                "is archived. Requires PCF_NATUR=S and PCF_RELATED.",
        "pfc": [{"pfc": 0, "bits": 0, "label": "n/a"}],
    },
]


def bit_width(ptc: int, pfc: int) -> int | None:
    """Width in bits of a PTC/PFC pair, or None if variable/unknown."""
    for entry in PTC_CATALOG:
        if entry["ptc"] != ptc:
            continue
        if "pfc" in entry:
            for v in entry["pfc"]:
                if v["pfc"] == pfc:
                    return v["bits"] or None
            return None
        rule = entry["pfc_rule"]
        if not (rule["min"] <= pfc <= rule["max"]):
            return None
        if rule["bits"] == "pfc":
            return pfc or None
        if rule["bits"] == "pfc*8":
            return (pfc * 8) or None
    return None


def ptcpfc_catalog_json() -> list[dict]:
    return PTC_CATALOG
