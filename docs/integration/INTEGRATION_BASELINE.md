# I0 integration baseline

Audit date: 2026-10-28. Scope: I0 only. No application implementation, merge, push, real image generation, service restart or port-8000 access performed.

## Git facts and isolation

| Ref | Verified SHA |
|---|---|
| main / origin/main | `f89093eaa45ace99b134093b563d1f30d3bbe5c0` |
| b / origin/b | `49f63ee4e242efe0c5aa4aef0a524652e75cfd5a` |
| backend / origin/backend | `d3bc788308092082ead684ed3e0aa211ec6413be` |
| newBackend independent main | `4b2be3cd824f1661f3b33fb3c5199111faf17aac` |

Remote: `git@github.com:Hackfest-X-Saividya/ssdnexus-t1-20.git`. `git ls-remote` and subsequent `git fetch origin` confirmed matching local/remote branch tips. Main and b are different commits, sharing ancestor `d3bc788308092082ead684ed3e0aa211ec6413be`. Main has the handoff and subsequent landing light-palette commit; b has the committed migration `adding all file`.

Original checkout `/home/god/Documents/github/ssdnexus-t1-20` was clean and remains on main. It has ignored `__pycache__/`, `evidence/`, `migration-private/`, and `tests/` leftovers; these were preserved. The prior terminal's deletions cannot be reconstructed as uncommitted changes from today's clean checkout. Current b **commits** deletion of Revelio source and replacement with WitnessTrace; a full merge is unsafe for the UI and privacy. `git show b` reports 786 changed files, 90,628 insertions and 21,512 deletions relative to its parent.

Integration branch `integration/revelio-witnesstrace` was created from main in a separate worktree:
`/home/god/Documents/github/ssdnexus-t1-20-integration`.
No existing checkout was switched, reset, cleaned or overwritten. No existing branch was deleted. Only I0 documentation will be committed here.

Commands examined: `git status --short`, `git branch -vv`, `git log --all --oneline --decorate --graph -25`, `git diff --stat main...b`, `git diff --name-status main..b`, `git ls-tree -r --name-only b`, `git remote -v`, `git worktree list`, remote ref comparison. Full diff inventories are private audit artifacts.

## Source provenance

Original Phase 08 project:
`/home/god/Documents/github/Composite-Studio/WitnessTrace_Visual_Upgrade_Kit/witnesstrace_ui_kit/working_product`.

A separate migration already exists at `/home/god/Documents/github/newBackend`. Its independent Git tree is clean at the SHA above. `MIGRATION_REPORT.md` records the original source, data copy, tests and previous migration; those historical claims were treated as reports, not fresh results.

Fresh SHA-256 comparison of **94 files** (nine core Python/requirements/launcher files plus all static and test files, excluding caches) finds **zero differences** between original, migrated copy and committed b. No backend source recovery is needed. Functional source provenance for I2 is **committed b**, checked against both complete Phase 08 copies. Import selected source files rather than pretending to merge the entire branch. The migrated copy has additional dependency locks, migration documentation and newer local QA data, not newer production logic. Full file hashes and mtimes reside privately in `audit.json` and per-copy manifests.

Selected runtime data source for future integration: migrated `newBackend/data/witness.sqlite3` and its associated data files, with `outputs/` and `work/` retained. Use one existing WitnessTrace case store; do not create another case database or overwrite the original project. Data-path and service handover are future phased work, not completed here.

## Handoff cross-check

The requested `/home/god/Documents/github/UI_INTEGRATION_HANDOFF.md` does not exist. Read the entire 1,314-line committed copy at repository-root `UI_INTEGRATION_HANDOFF.md` instead.

Verified from source: React 19.2.4, Vite 8.0.0, JavaScript/JSX, plain CSS; pathname entry switch, custom hash router and AppContext; landing/auth/workspace surfaces; five original pages; 248px sidebar, 60px topbar; final dark `#090909` / `#ef5539` and light cream/sage layers; Syne/Inter/IBM Plex Mono font links. Original API, procedural renderer and cookie-auth assumptions are real. Backend is Revelio FastAPI (`backend/app/main.py`), not WitnessTrace.

Corrections to stale handoff context: its inspected HEAD was d3bc788; current main is f89093e. The formerly uncommitted landing palette is now committed. WitnessTrace is available for inspection and has actual asynchronous job routes, 45 fields/seven groups, immutable case records and all seven store/schema modules. The handoff recommended vanilla based partly on missing WitnessTrace code; see ARCHITECTURE_DECISION.md for the updated assessment. Its macOS temporary screenshots are not local evidence. Twelve committed reference images exist; fresh rendered captures are deferred to I1.

Logo origin remains unverified: preserve existing assets in source; do not import additional logos or add endorsement claims. Fonts currently use Google Fonts and need offline/licence verification before self-hosting; no new font assets were downloaded in I0.

## Existing frontend inventory

- `src/main.jsx`: lazy landing/login/register/app entries, theme initialization and legacy redirects.
- `src/App.jsx`: verified cookie auth gate, boot, shell and five-page navigation.
- `src/state/AppContext.jsx`: health/catalog, notifications, UI preferences and active sketch state.
- `src/api/client.js`: fetch wrapper, auth redirect, synchronous sketch contracts and download links.
- `src/pages/Workspace.jsx`: stats/sketches/activity dashboard.
- `src/pages/NewSketch.jsx`: local history reducer, 140ms procedural live render, description, mode, revisions and autosave. These domain assumptions must change without discarding its layout.
- `src/pages/Library.jsx`, `Compare.jsx`, `Settings.jsx`: card browsing, revision reveal/split and providers/settings. Rename/delete/provider controls require capability mapping, not cosmetic hookup.
- `src/components/shell/`, `ui/`, `sketch/`: sidebar, topbar, modal/focus trap, toasts, viewer, compare slider, trait/adjust/refine/description panels.
- `src/index.css`, `src/styles/app.css`, `src/landing/`, `src/auth/`: existing visual system and entry surfaces retained untouched.
- `vite.config.js`: `/api` proxy defaults to port 8000. Do not start default dev-all; future overrides must target an isolated allowed port. WitnessTrace also needs `/images` and controlled static/worker paths.

## Existing backend and feature inventory

| Capability | Verified source | Integration requirement |
|---|---|---|
| Terminal image generation | `app.py`: prompt_for, run_job, durable_run_job | Keep authenticated Codex exec, image validation and durable finish; explicit action, never slider auto-generation |
| Cases/testimony | `case_store.py` | Exact original freeze, append-only sourced clarifications, stale-revision protection |
| Character Lab | `lab_schema.py`, case Draft validation, static/character-lab.js | 45 fields, seven groups, Unknown/uncertainty/quotes; explicit preview |
| Refinement/lineage | case_store.py, static/refinement.js | Prompt review, child versions, selection/preferred, request-key deduplication |
| Sketchpad | sketch_store.py, static/sketchpad.js | Keep drawing/layers/transform engine and editable project persistence |
| Enhance | enhance_store.py, static/enhance.js, enhance-worker.js | Actual RGBA worker pixels; save committed preview; imports/adjustment provenance |
| Multi-view | multiview_store.py, static/multiview-reports.js | 2D concept sheets, reviewed crops, never claim 3D or identity consistency |
| Reports | report_store.py | Immutable PDF/JSON/PNG bundles, testimony, history and checksums |
| Local UI/history | static/index.html, workbench.js/css, workbench-polish.css | Reference for complete functionality, not a second disconnected final app |
| Original Revelio API | backend/app/api, services, providers, database.py | Preserve source; do not route final generation to procedural/Gemini providers |
| Accounts | backend/app/api/auth.py, services/auth_service.py | Verified scrypt, hashed opaque cookie sessions; WitnessTrace currently has no auth |

## Actual WitnessTrace API inventory (source/OpenAPI)

No endpoint has been integrated into React in I0. Request contracts below name real Pydantic models; detailed adapter mapping and payload examples belong to I3.

| Method | Path | Request model |
|---|---|---|
| GET | `/` | `—` |
| POST | `/api/generate` | `GenerateRequest` |
| GET | `/api/jobs/{job_id}` | `—` |
| GET | `/images/{job_id}` | `—` |
| GET | `/api/health` | `—` |
| GET | `/api/cases` | `—` |
| POST | `/api/cases` | `NewCase` |
| GET | `/api/cases/{case_id}` | `—` |
| PUT | `/api/cases/{case_id}` | `SaveCase` |
| POST | `/api/cases/{case_id}/freeze` | `Freeze` |
| POST | `/api/cases/{case_id}/clarifications` | `Clarification` |
| GET | `/api/lab-schema` | `—` |
| POST | `/api/cases/{case_id}/prompt-preview` | `Draft` |
| POST | `/api/cases/{case_id}/selection` | `Selection` |
| POST | `/api/cases/{case_id}/refinement-preview` | `Refinement` |
| POST | `/api/cases/{case_id}/refine` | `Refinement` |
| GET | `/api/cases/{case_id}/versions/{version_id}/sketch` | `—` |
| POST | `/api/cases/{case_id}/local-edits` | `SaveEdit` |
| POST | `/api/cases/{case_id}/imports` | `ImportImage` |
| GET | `/api/cases/{case_id}/versions/{version_id}/enhance` | `—` |
| GET | `/api/cases/{case_id}/versions/{version_id}/pixels` | `—` |
| POST | `/api/cases/{case_id}/enhancements` | `SaveEnhancement` |
| GET | `/api/enhance-schema` | `—` |
| POST | `/api/cases/{case_id}/multiview-preview` | `multiview_store__Request` |
| GET | `/api/cases/{case_id}/multiview` | `—` |
| POST | `/api/cases/{case_id}/multiview` | `multiview_store__Request` |
| POST | `/api/cases/{case_id}/views/{version_id}/layouts` | `Layout` |
| GET | `/api/cases/{case_id}/views/{version_id}/layouts/{layout_id}/{angle}.png` | `—` |
| POST | `/api/cases/{case_id}/reports` | `report_store__Request` |
| GET | `/api/cases/{case_id}/reports` | `—` |
| GET | `/api/cases/{case_id}/versions/{version_id}/export.png` | `—` |
| GET | `/api/cases/{case_id}/reports/{report_id}/preview` | `—` |
| GET | `/api/cases/{case_id}/reports/{report_id}/{extension}` | `—` |
| GET | `/api/cases/{case_id}/versions/{version_id}/export.json` | `—` |

All current WitnessTrace routes lack authentication dependencies. Saved-data and image/export routes enforce case/version ownership where specified, not user tenancy. Health reports CLI installation and a tool-availability caveat; it does not prove authenticated generation. Submission routes return persisted job handles with `job_id`, `status`, `message`, `image_url` (202 for asynchronous generation). Poll GET jobs until validated completion, then refresh case versions; do not show acceptance as success. Images use `/images/{job_id}`, not RV IDs. Global process guard returns 409 during another generation. Pydantic validation returns 422 detail arrays; business conflicts use 409, missing/cross-case resources use 404, failed local saves/report creation use 503. Normalize both array and string detail errors in the future adapter. Original generation schema accepts 10–2500 description characters; case generation builds its prompt from persisted validated testimony/draft. Do not truncate frozen testimony to fit a new UI limit.

## Fresh verification

| Check | Command / isolation | Result |
|---|---|---|
| Dependencies | npm ci in integration worktree | 154 installed; lockfile unchanged |
| Frontend lint | npm run lint | PASS |
| Production build | npm run build | PASS, Vite 8.0.0, 70 modules, 1.85s |
| Revelio API | backend/.venv/bin/python -m pytest -q backend/tests | 76 passed, 20.42s |
| WitnessTrace | newBackend/.venv/bin/python -m pytest -q private/backend-test-copy/tests | 54 passed, 1 Starlette/httpx deprecation warning, 28.26s |
| Python dependencies | pip check in both venvs | No broken requirements |
| npm advisories | npm audit --json | 13: 1 low, 2 moderate, 10 high; exit 1; no fixes applied in I0 |
| Source snapshots | archive member SHA-256 vs manifests | No mismatches |
| Git recovery | git bundle verify pre-I0.bundle | Complete history; PASS |
| SQLite backups/restores | SQLite backup API, restored copies, integrity_check, foreign_key_check, table counts | PASS for both copies |

WitnessTrace tests ran on an external source copy to avoid writing to original data/outputs; fake CLI fixtures consume no quota. First run: 52 passed / 2 failed because the isolated copy omitted `evidence/phase02/before/app.py` and `phase03/before/app.py`, required by AST-preservation tests. Copying those unchanged source fixtures resolved both; full rerun passed. Include these code-only fixtures when preserving the suite in I2. Production code/tests were not edited.

Node v22.23.1/npm 10.9.8, Python 3.14. Existing Revelio pins install yanked Pydantic 2.12.1/core 2.41.3; this is a baseline dependency issue to address in a later scoped phase. npm audit details remain private; vite is a direct affected dependency. No browser tests, real CLI generation or historical 18-script regression rerun was claimed in I0. No React component-test command is configured.

## Private data and recovery evidence

Private backup root (outside every Git repository): `/home/god/Documents/github/integration-audit-private`, mode 0700. It contains the complete Git bundle, source/runtime archives without venv/cache/Git directories, per-file SHA-256/mtime manifests, SQLite online backups, restored verification copies, source comparisons, test logs and OpenAPI inventory. Do not commit or publish it: the Git bundle and archives contain already tracked or local private records.

| Copy | Cases | Statements | Versions / valid image hashes | Report bundles / export files |
|---|---:|---:|---:|---:|
| Original working_product | 11 | 12 | 23 / 23 | 9 / 27 |
| Migrated newBackend | 13 | 14 | 25 / 25 | 10 / 30 |

Both databases have 13 tables, integrity_check `ok`, zero foreign_key_check rows. SQLite backups were restored into separate files and table counts/integrity checked. Both file archives were read back and every member hash matched the snapshot manifest. All snapshotted non-database files still match their source hashes after verification. All original testimony, versions, events, edit operations, multi-view layouts and report rows are retained byte-for-value in newBackend. One original case's revision counter and one selection/preferred row differ; these are existing migration/QA state differences, not data loss or I0 mutations. Prefer the newer complete migrated runtime; do not roll it back over the original.

Committed b's database matches all migrated database tables logically. b tracks 56 data files, 14 outputs, 34 work files, 434 evidence files and 12 migration-private files, including databases, images, reports and worker artifacts. This is already in origin/b: future ignore rules cannot erase existing remote history. No history rewrite or branch cleanup was attempted. Filename scan found no credential-named tracked files beyond `.env.example`; that is not a comprehensive secret audit. Preserve originals and avoid propagating these files into main. Main has no checked-in WitnessTrace runtime database; its ignored backend/data directory is absent in this checkout.

## Conflicts, risks and rollback

Potential conflicts: b deletes `src/`, package/Vite config and Revelio backend; replaces README; adds root app.py/static/tests and private runtime trees; shared `/api/health`, `/`, `/static` and catalog/auth assumptions differ. Use explicit source selection under an isolated backend namespace, retaining React source and existing Revelio backend until replacement routes/auth are verified. Avoid Python `app` package/module import collisions with an explicit app-dir/service wrapper. No schema migration is needed for WitnessTrace data.

High-risk future areas: global DOM coupling of Sketchpad/Enhance, lifecycle cleanup/StrictMode, shared state on case switch, asynchronous image completion, all image download paths, immutable testimony, idempotent edits, auth on image/worker/report routes, single-process generation and shared Codex output attribution. Existing backend is a localhost prototype, not publicly deployable multi-tenant infrastructure. No accuracy claims can be inferred from tests.

Rollback for I0: leave the original main checkout and all source copies untouched; use the integration documentation commit's revert if desired. Keep the worktree and branch for review. Restore code from the verified bundle into a separate recovery checkout if needed. Restore a database only after stopping its verified owning service, preserving current DB/sidecars/files, and restoring the matching file archive; never overwrite a running store. No server stop/start was necessary here; port 8000 was never contacted or managed.

## Next gate

I1 is not started. On explicit NEXT, preserve/capture actual React baseline and address its phase-specific issues. I2–I8 remain pending. Do not merge or push main before their verification and the required final approval.
