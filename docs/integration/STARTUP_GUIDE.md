# Run Revelio + WitnessTrace locally

The primary application is React/Vite. `npm run dev` starts three loopback-only processes: React at **5182**, the authenticated Revelio gateway at **8021**, and WitnessTrace at **8022**. It refuses occupied ports and never kills existing listeners. Ports 8000 and 8001 are not used.

## Install

From the final checkout (Python 3.14 and Node 22 were tested):

```bash
npm ci
python3 -m venv witness-backend/.venv
witness-backend/.venv/bin/python -m pip install -r witness-backend/requirements-test.txt
```

The WitnessTrace runtime lock includes FastAPI, Pydantic, Pillow and ReportLab; its test requirements add httpx, pytest and Playwright. The same environment runs the gateway. Do not install the legacy `backend/requirements.txt` into this environment: it is retained for the separately supported old Revelio renderer and has older pins. This checkout's development environment may use ignored virtual-environment symlinks; they are not required on another machine.

The existing authenticated Codex CLI must be available in PATH for AI generation. Keep its normal authenticated home. Do not configure a different image provider. Installation/health alone does not establish current quota or image-tool availability. One real successful generation is recorded in `I3_VERTICAL_SLICE.md`; the regression verifier uses labelled synthetic patterns.

```bash
npm run dev
```

Open <http://127.0.0.1:5182/register>, create a local account, then use `/app`. Subsequent visits use `/login`. Account passwords and sessions are stored by the original Revelio authentication service. All signed-in users share this local WitnessTrace collection; this is not a public multi-tenant deployment.

## Persistent storage

Default runtime root: `~/.local/share/revelio-witness/`, outside Git. It contains `accounts/`, `data/`, `outputs/`, and `work/`. Set `REVELIO_RUNTIME_DIR` before starting to choose another external root. Individual overrides are `REVELIO_DATA_DIR` (accounts), `WITNESSTRACE_DATA_DIR`, `WITNESSTRACE_OUTPUTS_DIR` and `WITNESSTRACE_WORK_DIR`.

Existing case stores were deliberately not copied or overwritten. To use an existing collection, first make a matching SQLite online backup and file backup, stop its owning service using its own normal procedure, and set the three WitnessTrace directories to that collection's matching paths. Never run two owners against the same case store. Do not use a database without its associated case images, reports and editable projects. Ports 8000/8001 and their existing services are outside this launcher's management.

Cases, immutable original testimony, sourced addenda, drafts, selected/preferred versions, lineage, edits, enhancement parameters, reviewed layouts, report files and hashes are backend records. Browser storage holds interface preferences and selected case IDs. Save drafts/edits before refreshing. Unsaved canvas state survives hash navigation and tool switching, but a full refresh needs a saved revision.

## Independent processes

For debugging, export the storage variables above in each terminal, then:

```bash
# WitnessTrace
./witness-backend/start.sh

# Session service and gateway, same installed environment
WITNESSTRACE_GATEWAY_TARGET=http://127.0.0.1:8022 \
witness-backend/.venv/bin/python -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8021

# React
REVELIO_API_URL=http://127.0.0.1:8021 REVELIO_GATEWAY_URL=http://127.0.0.1:8021 \
npm run dev:web -- --host 127.0.0.1 --port 5182 --strictPort
```

`npm run build` builds the integrated application by default. `npm run preview -- --port 5182 --strictPort` needs the same API URL overrides and both APIs running. `VITE_WITNESSTRACE_LOCAL=0` explicitly opts into the preserved legacy frontend; `npm run dev:legacy` retains its historical launcher and port defaults, so do not use it in this shared-port environment.

## Verification

```bash
witness-backend/.venv/bin/python -m pytest -q backend/tests
(cd witness-backend && .venv/bin/python -m pytest -q)
npm run test:adapter
npm run lint
npm run build
witness-backend/.venv/bin/python -m playwright install chromium
witness-backend/.venv/bin/python docs/integration/evidence/final/verify_browser.py
witness-backend/.venv/bin/python scripts/tests/verify_startup.py
```

The browser verifier refuses occupied 5182/8021/8022, creates disposable external synthetic storage, uses a clearly labelled geometric-image CLI fixture, and stops only its own processes. It refuses `--live-once`; no additional real generation is needed for regression checks. Evidence is written under `docs/integration/evidence/final/` and is synthetic only.

## Stop and roll back

Ctrl-C stops only the launcher's children. It preserves storage. A generation interrupted by shutdown can be recorded failed; completed records survive restart. Backend generation cancellation/resumption is not invented.

To inspect the pre-final implementation, create another clean worktree at `4d3b17f` or revert the final integration commits on a separate recovery branch. Do not reset/clean the dirty b worktree. Code rollback does not require deleting databases. Restore runtime backups only with the owning service stopped and after preserving the current database, sidecars and associated files. No remote push or history rewrite is part of rollback.
