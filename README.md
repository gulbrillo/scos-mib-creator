# SCOS MIB Creator

A modern, web-based editor for **SCOS-2000 / Terma CCS5 MIB databases** — the
tab-separated ASCII files (`pcf.dat`, `pid.dat`, `ccf.dat`, …) that configure ESA
ground systems for telemetry decoding and telecommand encoding.

Built for unit/instrument teams who have never worked with SCOS-2000, CCS5, PUS
or a MIB before: every field has a tooltip and extended help (paraphrased from
the ICD), wizards create coherent multi-table content with all offsets computed
automatically, and a validation engine explains every problem with a fix hint.

## Features

- **Guided editing** — domain-oriented navigation (TM packets, TM parameters,
  calibrations, TC commands, verification, sequences…), registry-driven forms
  with tooltips, per-field help drawer with ICD section references, and
  dropdowns for every enumerated value and cross-table reference.
- **Wizards** — *New TM packet* (pid + pic + tpcf + plf + pcf with a live byte
  map), *New TC command* (ccf + cpc + cdf + verification with PUS ack flags),
  *New calibration* (all 7 kinds, attachable to parameters), *New limit check*.
- **PUS-aware** — service catalog (ECSS-E-ST-70-41) with pre-filled
  types/subtypes, a PTC/PFC type picker that translates "unsigned 16-bit
  integer" into the right codes, and a built-in "MIB 101" guide.
- **Round-trip import/export** — import an existing MIB (zip of `.dat` files,
  with dry-run analysis), edit it in the GUI, export it again. Unknown vendor
  columns are preserved byte-exactly.
- **Validation** — field formats, lengths, enumerations, key uniqueness,
  cross-table references, count consistency (`CAF_NCURVE` vs. points, …) and
  MIB-semantic checks (missing PIC criteria, dangling calibrations, …), each
  with severity and a "how to fix it" hint.
- **Export profiles** — ESA SCOS-2000 ICD 7.0, or CCS5 (ICD 7.x + Terma
  extension columns such as `PID_PFIELD`/`PID_CORR`; field-length violations
  downgraded to warnings).
- **Multi-user** — built-in accounts, per-project roles (owner / editor /
  viewer), optimistic-concurrency protection against conflicting edits.

## Quick start

```bash
docker compose up -d --build
```

Then open **http://localhost:8082/** and sign in with the initial
administrator account (`admin` / `admin` unless overridden — **change it
immediately** via the Users page, or set environment variables first).

Configuration (environment variables, see `docker-compose.yml`):

| Variable | Default | Purpose |
|---|---|---|
| `POSTGRES_PASSWORD` | `mibcreator` | Database password |
| `SECRET_KEY` | *(change it!)* | Signs session cookies — set a long random string |
| `ADMIN_USERNAME` / `ADMIN_PASSWORD` | `admin` / `admin` | Initial admin account (first start only) |

Data lives in the `dbdata` Docker volume; `docker compose down` keeps it,
`docker compose down -v` wipes it.

## Apache reverse-proxy vhost

The container serves UI and API on a single port (8082), so a plain proxy
works — no path rewriting needed (the SPA uses hash-based routing):

```apache
<VirtualHost *:443>
    ServerName mib.example.org
    # ... SSL config ...

    ProxyPreserveHost On
    ProxyPass        / http://127.0.0.1:8082/
    ProxyPassReverse / http://127.0.0.1:8082/
    # MIB archives can be a few MB
    LimitRequestBody 104857600
</VirtualHost>
```

## Documentation

- **In-app**: the *MIB & PUS guide* page (top navigation) and the per-field
  help everywhere.
- [docs/user-guide.md](docs/user-guide.md) — walkthrough for first-time users.
- [docs/egos-mcs-s2k-icd-0001-v7.0.pdf](docs/egos-mcs-s2k-icd-0001-v7.0.pdf) —
  the authoritative SCOS-2000 Database Import ICD (issue 7.0, © ESA), from
  which the schema registry was transcribed.

## Architecture

```
docker-compose.yml      postgres:16 (db) + single web container (port 8082)
backend/
  mibschema/            pure-Python MIB engine (no web dependencies)
    registry/*.yaml     45 MIB tables, 320 columns: types, keys, enums,
                        FKs, tooltips, help text — drives EVERYTHING
    parser.py           .dat -> rows (lossless, preserves unknown columns)
    generator.py        rows -> .dat per export profile
    validator.py        field / referential / semantic checks
    pus/                PTC-PFC catalog (ICD Appendix A) + PUS services
  app/                  FastAPI: auth, projects, generic row CRUD,
                        import/export, validation, wizards; serves the SPA
frontend/               Vue 3 + TypeScript + PrimeVue SPA
```

The single source of truth is the **schema registry**: adding a table or a
vendor column means editing a YAML file — the editor UI, parser, generator and
validator all follow automatically. MIB rows are stored generically
(`project_id, table_name, seq, JSONB data`) so imports survive round trips
losslessly, and half-finished databases are always storable (consistency is
the validator's job, not the schema's).

## Development

```bash
# backend (Python 3.12+)
cd backend
python -m venv .venv && .venv/Scripts/pip install -r requirements-dev.txt
.venv/Scripts/python -m pytest            # 13 tests incl. full round-trip e2e
.venv/Scripts/python -m uvicorn app.main:app --port 8080 --reload

# frontend (Node 20+)
cd frontend
npm install
npm run dev                                # http://localhost:5173, proxies /api
```

`docs/extract_fields.py` / `extract_enums.py` are the helpers used to
transcribe the ICD PDF into the registry — useful when a new ICD issue lands.

## License

MIT (see LICENSE). The ICD PDF in `docs/` is © European Space Agency and
included for reference only.
