"""Extract MIB table field definitions from the ICD text dump.

Produces docs/icd-field-summary.txt: for each table section (e.g. 'pcf'),
the ordered list of fields with type and the trailing M (mandatory) marker
when detectable. Used to build the schema registry; descriptions are
paraphrased separately.
"""
import re

text = open("docs/icd-v70-fulltext.txt", encoding="utf-8").read()
lines = text.splitlines()

# Section headers like: 3.3.2.1.1 Monitoring parameters characteristics: pcf
sec_re = re.compile(r"^(3\.3\.[\d.]+)\s+(.*?):\s*([a-z]{2,4})\s*$")
field_re = re.compile(
    r"^(\d{1,2})\s+(\*\s*)?([A-Z][A-Z0-9_]*_[A-Z0-9_]+)\s+(Char\s*\(\s*\d+\s*\)|Number\s*\(\s*\d+\s*\)|Char\(\d+\)|Number\(\d+\))(.*)$"
)

sections = []  # (line_idx, secnum, title, table)
for i, ln in enumerate(lines):
    m = sec_re.match(ln.strip())
    if m and len(m.group(1)) > 6:
        sections.append((i, m.group(1), m.group(2).strip(), m.group(3)))

out = []
for si, (start, secnum, title, table) in enumerate(sections):
    # only the second occurrence (body, not TOC) matters; body sections have
    # field rows after them. We just scan until the next section header.
    end = sections[si + 1][0] if si + 1 < len(sections) else len(lines)
    body = lines[start:end]
    fields = []
    j = 0
    while j < len(body):
        m = field_re.match(body[j].strip())
        if m:
            num, star, name, ftype, rest = m.groups()
            # find mandatory marker: scan forward until next field row or
            # page break, looking for a line that is exactly 'M' or ends ' M'
            mand = ""
            desc_first = rest.strip()
            k = j + 1
            while k < len(body):
                s = body[k].strip()
                if field_re.match(s) or s.startswith("=== PAGE"):
                    break
                if s == "M":
                    mand = "M"
                elif re.fullmatch(r".*\sM", s) and len(s) < 80:
                    pass  # ambiguous, ignore
                k += 1
            fields.append((int(num), bool(star), name, ftype.replace(" ", ""), mand, desc_first[:60]))
        j += 1
    if fields:
        out.append(f"\n## {secnum} {title}: {table}  (line {start+1})")
        for num, star, name, ftype, mand, d in fields:
            key = "*" if star else " "
            out.append(f"{num:3d} {key} {name:<16} {ftype:<11} {mand:<2} | {d}")

open("docs/icd-field-summary.txt", "w", encoding="utf-8").write("\n".join(out))
print("sections with fields:", sum(1 for o in out if o.startswith("\n##") or o.startswith("##")))
print("total lines:", len(out))
