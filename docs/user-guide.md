# SCOS MIB Creator — User Guide

This guide walks a first-time user from an empty project to a delivered MIB.
It assumes no prior knowledge of SCOS-2000, CCS5, PUS or MIB databases — read
the in-app **MIB & PUS guide** (top navigation) for the concepts behind the
steps.

## 1. Sign in & users

An administrator account is created on first start (default `admin`/`admin` —
change the password immediately). Administrators create further accounts on
the **Users** page and can see every project. Regular users only see projects
they are members of, with one of three roles:

| Role | Can do |
|---|---|
| Viewer | Read everything, export |
| Editor | Edit MIB content, import/export, run wizards |
| Owner | Everything, plus settings, members, delete |

## 2. Create a project

One project = one MIB database. Keep **starter content** enabled: it creates

- the database version record (`vdf`),
- a standard PUS TC packet header (`tcp`/`pcpc`/`pcdf`) — the CCSDS + PUS
  header layout every command needs, so you never have to define bit fields of
  the primary header by hand,
- three generic verification stages (`cvs`) for acceptance / start /
  completion via PUS service 1.

Choose the **export profile**: *CCS5* if the MIB feeds a Terma CCS5-based
EGSE/SIS (recommended; tolerant lengths + Terma extension columns), or
*ESA SCOS-2000 ICD 7.0* for strict ESA deliveries. You can switch any time and
even export both — the profile only affects export and validation strictness.

## 3. Follow the dashboard checklist

The project dashboard shows a 7-step checklist with links. The typical order:

### 3.1 Define TM parameters (`pcf`)

Everything your unit reports is a parameter: name (max 8 chars, project
naming convention if you have one), description, type. The **type** is a
PTC/PFC pair — use the *Type picker* if you don't know the codes; "unsigned
16-bit integer" is PTC 3 / PFC 12.

You can also skip this and let the packet wizard create parameters inline.

### 3.2 Build TM packets (packet wizard)

For each housekeeping/event packet:

1. Pick the PUS service — housekeeping reports are (3,25).
2. Enter your unit's APID and, for HK, the SID that identifies this packet.
3. Set the data field header size (bytes between the CCSDS header and your
   data — mission-specific, ask your system team; often 10–16).
4. List the fields of the packet body **in on-board order**. For HK packets
   the first field is usually the 16-bit SID — the "Add SID field" button
   does this and marks it as the identification field.
5. Watch the live byte map; offsets and total size are computed for you.

The wizard creates `pid`, `pic` (where the ground finds the SID), `tpcf` and
`plf` records, plus any new `pcf` parameters.

### 3.3 Add calibrations (calibration wizard)

- **Status texts** (`txf`) for mode/flag parameters: 0=OFF, 1=ON…
- **Numeric curves** (`caf`), **polynomials** (`mcf`) or **logarithmic**
  (`lgf`) for analog channels.
- For **command arguments**: alias sets (`paf`), de-calibration curves
  (`cca`), range sets (`prf`).

"Attach to a parameter" wires the calibration to the right `pcf`/`cpc` record
and sets the category fields consistently.

### 3.4 Define TC commands (command wizard)

1. Name (max 8 chars) + description + APID.
2. PUS service — unit commands are usually (8,1) *perform function*: add the
   fixed 16-bit Function ID first (button provided), then your arguments.
3. Choose argument kinds: *editable* (operator enters a value), *fixed*
   (locked value) or *fixed area* (constant bytes).
4. Tick the verification stages to wait for; this also sets the PUS
   acknowledgement flags (`CCF_ACK`).

### 3.5 Add limit checks (limit wizard)

Pick a parameter, choose calibrated or raw limits, then define soft (warning)
and hard (alarm) ranges — or the expected state for status parameters.

## 4. Validate

**Validation** (sidebar) checks the whole database: formats, mandatory
fields, lengths (strict for the ESA profile), enumerations, duplicate keys,
broken references, count fields, missing PIC criteria, dangling calibrations
and more. Every finding carries a hint; click it to open the affected table.
Fix all *errors* before exporting; review *warnings* before an ESA delivery.

## 5. Export / deliver

**Import/Export → Download MIB**: a zip with the complete set of `.dat`
files (empty tables included by default — importers expect the full set).
Feed it to your CCS5/SIS configuration, or deliver it to ESA for integration
into the spacecraft global MIB.

## 6. Import an existing MIB

**Import/Export → Import** accepts a zip of `.dat` files. Run the **dry run**
first: it lists the tables found and any parsing notes without changing
anything. Unknown columns (vendor extensions) are preserved and re-exported
byte-identically; unknown files (e.g. display tables) are skipped with a note.

Import modes:

- *Replace tables contained in the archive* — default; other tables keep
  their content.
- *Replace the entire project* — clean re-import.
- *Append* — adds rows to existing tables (watch for duplicate keys in
  validation afterwards).

## 7. Editing raw tables

Every MIB table is directly editable under **MIB tables** in the sidebar —
the wizards are conveniences, not a cage. Each editor shows the ICD section,
a description of the table's role, tooltips on every column header and a help
drawer (question-mark icons) with the paraphrased ICD text, allowed values
and examples. References to other tables are dropdowns listing the existing
records.

If two people edit the same record, the second save is rejected with a clear
message (optimistic concurrency) — reload the record and re-apply.
