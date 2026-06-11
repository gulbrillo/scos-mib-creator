"""Extract per-field enumerated value lines from the ICD text dump.

For each field of each table section, prints lines that look like enum value
definitions ('X' - meaning) plus 'Default:'-style hints. Output is a compact
reference (docs/icd-enum-summary.txt) used while writing the schema registry.
"""
import re

lines = open("docs/icd-v70-fulltext.txt", encoding="utf-8").read().splitlines()

sec_re = re.compile(r"^(3\.3\.[\d.]+)\s+(.*?):\s*([a-z]{2,4})\s*$")
field_re = re.compile(
    r"^(\d{1,2})\s*(\*\s*)?([A-Z][A-Z0-9_]*_[A-Z0-9_]+)\s+(Char\s*\(\s*\d+\s*\)|Number\s*\(\s*\d+\s*\)|Char|Number)\b(.*)$"
)
# enum lines like: ‘R’ – raw   or  'A' - ascii  (PDF uses curly quotes)
enum_re = re.compile(r"^[‘'\"]([A-Za-z0-9]{1,3})[’'\"]\s*[–\-—=]\s*(.{0,100})")
noise_re = re.compile(r"^(Ref\.:|Issue:|Date:|SCOS-2000 Database|ESA/OPS-GIC|=== PAGE|Fi\. Nr|Def$|Ma/$)")

sections = [(i, m.group(3)) for i, ln in enumerate(lines)
            if (m := sec_re.match(ln.strip())) and len(m.group(1)) > 6]

out = []
for si, (start, table) in enumerate(sections):
    end = sections[si + 1][0] if si + 1 < len(sections) else len(lines)
    body = lines[start:end]
    cur_field = None
    buf = []
    started = False
    for ln in body:
        s = ln.strip()
        if noise_re.match(s):
            continue
        fm = field_re.match(s)
        if fm:
            started = True
            cur_field = fm.group(3)
            out.append(f"\n[{table}] {cur_field} {fm.group(4)}")
            continue
        if not started or not cur_field:
            continue
        em = enum_re.match(s)
        if em:
            out.append(f"    {em.group(1)!r}: {em.group(2).strip()}")
        elif re.search(r"[Dd]efault(s| value| is|:)|left [Nn]ull|[Ii]f not (specified|set)", s) and len(s) < 110:
            out.append(f"    ~ {s}")

open("docs/icd-enum-summary.txt", "w", encoding="utf-8").write("\n".join(out))
print("lines:", len(out))
