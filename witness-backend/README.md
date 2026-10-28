# Preserved WitnessTrace backend

Imported selectively from branch `b` at `49f63ee4e242efe0c5aa4aef0a524652e75cfd5a` for integration phase I2. This is the existing Phase 08 FastAPI application, store modules and imperative editing engines. It is an independent preservation/reference service; the Revelio React application is **not connected to it yet**. The original `backend/` remains Revelio's reference API.

## Install and start independently

Use Python 3.14 (the verified environment), SQLite from Python, and a single process. ReportLab provides its packaged Vera fonts; PDF text checks require `pdftotext` (Fedora `poppler-utils`). No GPU/model download is needed. New AI generations require the installed, authenticated Codex CLI and its built-in image tool.

```bash
cd witness-backend
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-runtime-lock.txt
./start.sh
```

The launcher binds **127.0.0.1:8022** by default and refuses ports 8000/8001, including zero-padded forms. It does not stop existing listeners. If 8022 is occupied, choose another authorized free port with `WITNESSTRACE_PORT`; do not terminate unrelated processes. Stop this foreground service with Ctrl+C. Do not run multiple workers: the generation guard is process-local.

Health: `http://127.0.0.1:8022/api/health`. The standalone original workbench and static assets remain available for preservation verification. That workbench is not the final integrated frontend.

## Private storage and paths

`start.sh` applies umask 077 and defaults to a **new** private runtime under `${XDG_DATA_HOME:-$HOME/.local/share}/witnesstrace-integration/`:

| Variable | Launcher default | Content |
|---|---|---|
| `WITNESSTRACE_DATA_DIR` | runtime/data | witness.sqlite3, case images, saved projects/operation records, reports/exports |
| `WITNESSTRACE_OUTPUTS_DIR` | runtime/outputs | Validated CLI output copies, including legacy unassociated outputs |
| `WITNESSTRACE_WORK_DIR` | runtime/work | Per-job CLI working directories and worker replies |

Explicit absolute directories may override these variables. Do not point tests at the user's original/migrated data. No existing 11/13-case database was copied, replaced or opened for these tests. Authorized data handover is later work. Keep DB plus images/exports together; use SQLite's backup API and matching file backups, and never restore beneath a running service.

Direct `uvicorn app:app` without the launcher retains the original module-relative `data/`, `outputs/`, `work/` defaults; they are ignored but are not the recommended private deployment layout. For manual invocation, set all three environment variables and use this directory as app-dir, for example:

```bash
WITNESSTRACE_DATA_DIR=/absolute/private/runtime/data \
WITNESSTRACE_OUTPUTS_DIR=/absolute/private/runtime/outputs \
WITNESSTRACE_WORK_DIR=/absolute/private/runtime/work \
.venv/bin/python -m uvicorn app:app --app-dir . --host 127.0.0.1 --port 8022
```

`static/` resolves from this module's directory independently of launch cwd. Case image/report paths remain relative to the existing case data root. No database schema migration or provider change was introduced.

## Generation contract

FastAPI → original single generation worker → authenticated `codex exec` subprocess → new image validation → saved output → SQLite case revision → polling/display. The worker argv/stdin, prompt, environment filtering, timeout and image-attribution/validation functions are unchanged. `CODEX_BIN`, `CODEX_HOME` and `CODEX_GENERATION_TIMEOUT` retain their original meanings. Do not put Codex auth data or API keys in the repository/browser. Health only detects the executable, not successful authentication, quota or image-tool access. Check `codex login status` privately; do not publish its raw output.

Generation is text-only probabilistic interpretation; refinement does not supply parent pixels, and identity consistency is not guaranteed. Multi-view is a 2D concept sheet with reviewed crops, not a reconstructed 3D model. Local Sketch and Enhance operations are separate from AI generation.

## Repeatable tests

```bash
.venv/bin/python -m pip install -r requirements-test.txt
.venv/bin/python -m pytest -q -p no:cacheprovider tests
# From repository root, with this venv:
witness-backend/.venv/bin/python docs/integration/evidence/i2/verify_isolated_server.py
```

The 54 original pytest tests are retained, plus two relocation/launcher checks. Fixture databases, CLI outputs and work directories use temporary roots. The two `tests/fixtures/phase0*_app.py` files are code-only historical references for AST preservation tests; they are not executable application entrypoints or private evidence. All test-generated images are synthetic fixtures, not AI results.

The HTTP verifier reserves 8022, uses a disposable synthetic store and an **explicit fake CLI executable** (no paid/live generation), starts the actual launcher, exercises APIs/exports and performs an actual restart of only its owned child. It deletes its runtime afterward and saves aggregate results/contracts, not raw case records or credentials. Existing historical browser drivers were not imported: they target port 8001 and depend on private saved evidence. Their original copies remain intact on b/source; rework for isolated fixtures is later QA work.

## Security and preservation limits

This original backend has no user authentication or tenant boundary. Case-scoped routes check that versions/reports belong to a case; global image/job routes address records by ID. Do not expose it publicly. Reusing Revelio authentication and connecting React belongs to I3. The historical source `PHASE_STATUS.md`/README/demo contain runtime identifiers/old locations and were not copied wholesale; safe phase/demo summaries here replace those records as documentation only.

Private runtime paths and databases are ignored. This prevents new accidental additions; it does not remediate private artifacts already in remote b history. **OWNER-SEC-01 remains open** before final shared merge. See `../docs/integration/I2_BACKEND_PRESERVATION.md` and `I2_BACKEND_API_INVENTORY.md` for exact provenance, changed paths, contracts and verified limitations.
