# I2 backend preservation and safe import

Status: PASS — source-only backend preservation, independent startup and tests. React integration is not started. No merge/cherry-pick from b, no main update, no remote push and no history rewrite occurred.

## Provenance, checkpoint and recovery

- Integration worktree: `/home/god/Documents/github/ssdnexus-t1-20-integration`, branch `integration/revelio-witnesstrace`, clean at I2 intake commit `1d0339fadaa418e38db688f754f0327174216bcd`.
- Committed backend source: **b `49f63ee4e242efe0c5aa4aef0a524652e75cfd5a`** (`adding all file`), matching the existing fetched origin/b ref. Existing main remains `f89093eaa45ace99b134093b563d1f30d3bbe5c0`; backend remains `d3bc788308092082ead684ed3e0aa211ec6413be`. No new remote operation was necessary.
- Additional integrity references: original `Composite-Studio/WitnessTrace_Visual_Upgrade_Kit/witnesstrace_ui_kit/working_product` and independently migrated `newBackend`, under `/home/god/Documents/github/`. Production/static/test source bytes were checked against both before import. The two migration-added dependency lockfiles exist only in b/newBackend; all other selected source/fixture files match original too.
- Recovery verified: complete-history private `integration-audit-private/pre-I0.bundle` remains valid; both I0 SQLite backup files remain readable with integrity_check=ok. A fresh private `integration-audit-private/i2/pre-I2.bundle` preserves the I0/I1 integration commits, with main f89093e as prerequisite. Both bundles were verified. Existing source/runtime archives and restored backup files were preserved outside Git.
- I2 rollback: revert the local I2 commit on the integration branch after preserving any new local runtime data. This does not restore/overwrite private databases or alter main/b/backend. Recover I0/I1 commits from the incremental bundle with its existing main prerequisite if needed. Do not restore data beneath a running service.

## Import allowlist and exact files

Selected **57 files** with `git show <verified-b-SHA>:<path>`; no checkout of b or wholesale branch import. **52 are byte-identical**, and five have explicitly reviewed relocation-only changes. All functions, async functions and classes in app.py have identical ASTs to committed b; both existing historical worker-preservation tests also pass. No case/database schema or service logic changed.

Exact source/destination paths and full SHA-256 hashes: [source-import-manifest.json](evidence/i2/source-import-manifest.json). Modified imported files include unified diffs in that manifest. Code-only historical fixtures were inspected as Python source; no fixture image/database/record was copied. The preserved PNG asset was visually inspected and is the existing Revelio wordmark/owl, not a face image; brand ownership remains unverified, with no new endorsement claim.

| Source path on b | Imported path | Integrity / exception |
|---|---|---|
| `app.py` | `witness-backend/app.py` | Relocation-only diff recorded |
| `case_store.py` | `witness-backend/case_store.py` | Byte-identical |
| `lab_schema.py` | `witness-backend/lab_schema.py` | Byte-identical |
| `sketch_store.py` | `witness-backend/sketch_store.py` | Byte-identical |
| `enhance_store.py` | `witness-backend/enhance_store.py` | Byte-identical |
| `multiview_store.py` | `witness-backend/multiview_store.py` | Byte-identical |
| `report_store.py` | `witness-backend/report_store.py` | Byte-identical |
| `requirements.txt` | `witness-backend/requirements.txt` | Byte-identical |
| `requirements-runtime-lock.txt` | `witness-backend/requirements-runtime-lock.txt` | Byte-identical |
| `requirements-test.txt` | `witness-backend/requirements-test.txt` | Byte-identical |
| `start.sh` | `witness-backend/start.sh` | Relocation-only diff recorded |
| `static/character-lab.js` | `witness-backend/static/character-lab.js` | Byte-identical |
| `static/enhance-worker.js` | `witness-backend/static/enhance-worker.js` | Byte-identical |
| `static/enhance.js` | `witness-backend/static/enhance.js` | Byte-identical |
| `static/icons/LICENSE` | `witness-backend/static/icons/LICENSE` | Byte-identical |
| `static/icons/arrow-up-right.svg` | `witness-backend/static/icons/arrow-up-right.svg` | Byte-identical |
| `static/icons/arrows-move.svg` | `witness-backend/static/icons/arrows-move.svg` | Byte-identical |
| `static/icons/brush.svg` | `witness-backend/static/icons/brush.svg` | Byte-identical |
| `static/icons/circle.svg` | `witness-backend/static/icons/circle.svg` | Byte-identical |
| `static/icons/crop.svg` | `witness-backend/static/icons/crop.svg` | Byte-identical |
| `static/icons/download.svg` | `witness-backend/static/icons/download.svg` | Byte-identical |
| `static/icons/emoji-neutral.svg` | `witness-backend/static/icons/emoji-neutral.svg` | Byte-identical |
| `static/icons/eraser.svg` | `witness-backend/static/icons/eraser.svg` | Byte-identical |
| `static/icons/eye.svg` | `witness-backend/static/icons/eye.svg` | Byte-identical |
| `static/icons/file-earmark-text.svg` | `witness-backend/static/icons/file-earmark-text.svg` | Byte-identical |
| `static/icons/folder2-open.svg` | `witness-backend/static/icons/folder2-open.svg` | Byte-identical |
| `static/icons/fonts.svg` | `witness-backend/static/icons/fonts.svg` | Byte-identical |
| `static/icons/image.svg` | `witness-backend/static/icons/image.svg` | Byte-identical |
| `static/icons/palette.svg` | `witness-backend/static/icons/palette.svg` | Byte-identical |
| `static/icons/patch-exclamation.svg` | `witness-backend/static/icons/patch-exclamation.svg` | Byte-identical |
| `static/icons/pencil-square.svg` | `witness-backend/static/icons/pencil-square.svg` | Byte-identical |
| `static/icons/pencil.svg` | `witness-backend/static/icons/pencil.svg` | Byte-identical |
| `static/icons/person-arms-up.svg` | `witness-backend/static/icons/person-arms-up.svg` | Byte-identical |
| `static/icons/person.svg` | `witness-backend/static/icons/person.svg` | Byte-identical |
| `static/icons/scissors.svg` | `witness-backend/static/icons/scissors.svg` | Byte-identical |
| `static/icons/slash-lg.svg` | `witness-backend/static/icons/slash-lg.svg` | Byte-identical |
| `static/icons/sliders.svg` | `witness-backend/static/icons/sliders.svg` | Byte-identical |
| `static/icons/square.svg` | `witness-backend/static/icons/square.svg` | Byte-identical |
| `static/index.html` | `witness-backend/static/index.html` | Byte-identical |
| `static/multiview-reports.js` | `witness-backend/static/multiview-reports.js` | Byte-identical |
| `static/refinement.js` | `witness-backend/static/refinement.js` | Byte-identical |
| `static/revelio-logo.png` | `witness-backend/static/revelio-logo.png` | Byte-identical |
| `static/sketchpad.js` | `witness-backend/static/sketchpad.js` | Byte-identical |
| `static/workbench-polish.css` | `witness-backend/static/workbench-polish.css` | Byte-identical |
| `static/workbench.css` | `witness-backend/static/workbench.css` | Byte-identical |
| `static/workbench.js` | `witness-backend/static/workbench.js` | Byte-identical |
| `tests/conftest.py` | `witness-backend/tests/conftest.py` | Relocation-only diff recorded |
| `tests/test_app.py` | `witness-backend/tests/test_app.py` | Byte-identical |
| `tests/test_cases.py` | `witness-backend/tests/test_cases.py` | Relocation-only diff recorded |
| `tests/test_character_lab.py` | `witness-backend/tests/test_character_lab.py` | Relocation-only diff recorded |
| `tests/test_enhance.py` | `witness-backend/tests/test_enhance.py` | Byte-identical |
| `tests/test_multiview_reports.py` | `witness-backend/tests/test_multiview_reports.py` | Byte-identical |
| `tests/test_phase08_workflow.py` | `witness-backend/tests/test_phase08_workflow.py` | Byte-identical |
| `tests/test_refinement.py` | `witness-backend/tests/test_refinement.py` | Byte-identical |
| `tests/test_sketchpad.py` | `witness-backend/tests/test_sketchpad.py` | Byte-identical |
| `evidence/phase02/before/app.py` | `witness-backend/tests/fixtures/phase02_app.py` | Byte-identical |
| `evidence/phase03/before/app.py` | `witness-backend/tests/fixtures/phase03_app.py` | Byte-identical |

New backend-local files: `tests/test_relocation.py`, `README.md`, safe `DEMO_GUIDE.md`, safe `PHASE_STATUS.md`. The guide/ledger are adapted documentation, not claimed byte-identical copies of historical runtime reports. They preserve workflow/phase knowledge while removing old private case/job IDs and wrong-directory/port instructions. Original historical documents remain untouched on b and in source projects.

## Exclusions and privacy

The b tree contains 666 tracked paths; 609 were not selected. The following families are excluded from import. Full per-file exclusion inventory is private in `integration-audit-private/i2/excluded-paths.json`; public evidence contains only safe path-family counts/reasons in [excluded-summary.json](evidence/i2/excluded-summary.json).

| Excluded family | Count | Reason |
|---|---:|---|
| `.env.example` | 1 | Unneeded original environment template; no env values imported |
| `.gitignore` | 1 | Do not overwrite root Revelio ignore rules; explicit new rules added |
| `DEMO_GUIDE.md` | 1 | Historical case/job IDs and assumptions; safe guide adapted instead |
| `MIGRATION_CODE_SHA256.json` | 1 | Mixed original migration inventory not an accurate manifest for selected import |
| `MIGRATION_REPORT.md` | 1 | Historical private runtime locations and evidence references; provenance documented here |
| `PHASE_STATUS.md` | 1 | Large historical ledger includes case/job IDs/evidence; safe summary written instead |
| `README.md` | 1 | Old project paths/ports/data-dependent instructions; relocation-specific README written |
| `data/` | 56 | SQLite, case/source images, testimony and exports: private runtime, not fixtures |
| `design-qa.md` | 1 | Historical standalone UI QA, not necessary to run preserved backend |
| `design-source/` | 12 | Design blueprints/references not required for backend preservation |
| `evidence/` | 432 | Historical screenshots, records, databases/reports and logs; only two code-only app.py fixtures were separately relocated |
| `migration-private/` | 12 | Private migration records/backups/process artifacts |
| `outputs/` | 14 | Generated face outputs: private runtime |
| `tests/` | 41 | 41 historical non-pytest browser/operator drivers target protected port 8001 and/or private evidence; some embed historical IDs; leave original copies intact and adapt safely in later QA |
| `work/` | 34 | Worker replies/prompts/generated outputs: private runtime |

All 54 original pytest tests remain present; the excluded drivers are not collected pytest tests and are not runtime functionality. Their prior 18-script browser pass is historical only and is **not** a fresh I2 claim. Full browser/React engine parity remains later work; do not run the old 8001/private-evidence scripts unchanged against the existing app.

No real witness records, private generated faces, SQLite files, raw worker responses, Codex credentials, venvs or caches were staged. Root `.gitignore` now excludes new WitnessTrace runtime/venv paths, root runtime directories, SQLite files/sidecars and Codex auth paths. Required code-only fixtures under `tests/fixtures` remain tracked. No `.png` blanket ignore hides assets; only the inspected original logo is imported as PNG.

**OWNER-SEC-01 remains OPEN:** remote b already contains private runtime material; no wholesale merge/cherry-pick is permissible. New ignore rules prevent future additions only. Owners must classify/remediate historical exposure and record clearance before final shared merge. I2 does not authorize history rewriting, deletion or force-push. I1's DEP-01 dev-toolchain advisory follow-up also remains open.

## Final structure and responsibilities

```text
src/, public/, package*.json, vite.config.js   existing Revelio React, untouched
backend/                                    existing Revelio API, untouched
witness-backend/
  app.py                                    existing FastAPI routes + unchanged CLI worker
  case_store.py                             SQLite cases, immutable testimony, draft/job/revision/selection integrity
  lab_schema.py                             actual 45 attributes and seven groups
  sketch_store.py                            case-owned project/operation and PNG saves
  enhance_store.py                           source imports, canonical pixels and enhancement persistence/validation
  multiview_store.py                         2D sheet requests and reviewed crop integrity
  report_store.py                            persisted PDF/JSON/PNG snapshots and downloads
  static/                                   all 35 original workbench/editor/worker/icon/logo/license files
  tests/                                    eight original pytest modules + conftest + two historical code fixtures
    test_relocation.py                      two additional relocation/launcher checks
  requirements*.txt                         original declaration + verified runtime/test pins from b
  start.sh                                  isolated standalone launcher
  README.md, DEMO_GUIDE.md, PHASE_STATUS.md  safe relocated operating/feature guides
```

The existing static workbench is kept because its Sketchpad/Enhance/multi-view engines are functional source for later integration. It is a preservation/reference surface, **not a second interface presented as the final integrated application**. React still uses its existing API client/proxy unchanged.

## Path/launch changes (limited and tested)

1. `app.py` output/work initialization accepts `WITNESSTRACE_OUTPUTS_DIR` / `WITNESSTRACE_WORK_DIR`, expanded and resolved. Default module-relative directories remain compatible. `ROOT`, `STATIC`, worker functions, CLI argv/stdin/env filtering, prompt and validation are unchanged. Existing `WITNESSTRACE_DATA_DIR` controls the case store unchanged; case image/report paths remain relative to it.
2. `start.sh` resolves its own directory; uses explicit local `.venv/bin/python`; defaults all three runtime roots outside Git under `${XDG_DATA_HOME:-$HOME/.local/share}/witnesstrace-integration/{data,outputs,work}` with umask077; defaults **8022/127.0.0.1**, rejects 8000/8001 including zero-padded forms, and never kills listeners. Dependency installation is explicit setup rather than an automatic unpinned startup install. No existing migrated store is selected or copied by default.
3. `tests/conftest.py` sets output/work roots into its temporary bootstrap directory before app imports, alongside the existing temporary data setup. Individual fixture monkeypatches remain intact. One pre-existing trailing space was removed to satisfy the staged whitespace check.
4. Two AST tests reference `tests/fixtures/phase02_app.py` and `phase03_app.py` instead of a private evidence directory. Those fixture source bytes match committed history. Test assertions are unchanged.
5. Root `eslint.config.js` adds `witness-backend` beside the existing `dist` and `backend` exclusions, so unrelated imperative legacy JS is not misclassified as React source. This is the only changed I1 frontend/config manifest entry: **68/69 byte-identical**, with all React source/assets, package/lock, Vite config and API client unchanged. The root .gitignore prevention changes are separate from that manifest.

No absolute Composite-Studio/newBackend source paths or protected-port references were found in imported production code. The standalone launcher was actually invoked from an unrelated temporary cwd; imports/static assets worked without original source directories. No symlinks to original source/runtime were created. Python imports use the dedicated app-dir to avoid collision with Revelio's `backend/app` package; run their suites in separate processes rather than combining incompatible `app` module namespaces.

## Dependencies and setup

A fresh ignored `witness-backend/.venv` was created with Python 3.14. Installed directly from committed `requirements-test.txt` and its runtime include: FastAPI0.162.0, Starlette1.10.0, Uvicorn0.54.0, Pillow12.3.0, Pydantic2.14.1, ReportLab4.5.1, pytest9.2.0, httpx0.28.1 and Playwright1.63.0. SQLite is from Python; ReportLab packaged Vera fonts worked; system `pdftotext` is available and exercised by existing report tests. `pip check` reports no broken requirements. Pin files are not a complete transitive supply-chain audit.

```bash
cd witness-backend
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-runtime-lock.txt
./start.sh  # localhost:8022, separate private runtime
# In another terminal, only after confirming this is the isolated listener:
curl --fail http://127.0.0.1:8022/api/health
```

For tests install `requirements-test.txt`, then `.venv/bin/python -m pytest -q -p no:cacheprovider tests`. Root-level HTTP smoke command: `witness-backend/.venv/bin/python docs/integration/evidence/i2/verify_isolated_server.py`. The script refuses an occupied 8022 port, sets all private roots explicitly and stops only its owned child. It creates/deletes two entirely synthetic cases/six pattern-image versions in a protected temporary root. No original case database is opened for tests.

## Fresh verification results

| Check | Actual result / evidence |
|---|---|
| All original backend tests from new cwd | **54 passed**, one existing Starlette/httpx deprecation warning, 28.79s |
| Full backend suite including two new checks | **56 passed**, same warning, 27.62s; [pytest.txt](evidence/i2/pytest.txt) |
| Python dependency compatibility | PASS, no broken requirements; [pip-check.txt](evidence/i2/pip-check.txt) |
| Standalone service and exports | **33 checks PASS**, actual startup + restart on 8022; [server-checks.txt](evidence/i2/server-checks.txt), [server-checks.json](evidence/i2/server-checks.json) |
| Static relocation | All 35 static assets/icons/worker scripts match source SHA-256 over HTTP |
| Persistence | Two synthetic cases/six versions; exact statements, selected/preferred state, all revision and report bytes survive actual owned-process restart; SQLite integrity ok/FKs empty |
| Security negatives | Frozen original overwrite rejected; wrong-case pixels/projects/exports rejected; invalid IDs/path traversal return404; launcher refuses protected ports |
| Actual OpenAPI and route inventory | All 34 explicit routes documented in I2_BACKEND_API_INVENTORY.md; framework/static routes separately recorded |
| Frontend lint | PASS, `npm run lint`; [frontend-lint.txt](evidence/i2/frontend-lint.txt) |
| Frontend build | PASS, Vite8.0.0/70 modules; [frontend-build.txt](evidence/i2/frontend-build.txt) |
| Frontend preservation | 68/69 I1 manifest entries identical; only reviewed ESLint exclusion differs; [frontend-preservation.json](evidence/i2/frontend-preservation.json) |
| Original copies | 94 original and 94 migrated core/static/test source hashes still match I0; both Git worktrees clean where applicable; [original-preservation.json](evidence/i2/original-preservation.json) |
| Protected services | No requests/signals to8000/8001. Existing8001 PID143217 unchanged;8022 stopped after checks. |

The first HTTP harness attempt incorrectly parsed the JSON report download before accessing raw bytes; it was corrected and all33 checks rerun successfully. This was a verifier-only error, with no production service changes. Existing regression tests and the HTTP fixture both use fake CLI executables explicitly; they verify real saved image files and immutable storage without claiming real AI generation. HTTP Enhance uses the true identity/default parameter case, not a claimed test of all browser-worker filters. Those engines were preserved byte-for-byte and need browser integration parity later.

## Codex CLI verification and preservation

`codex-cli 0.165.0` is installed. `codex login status` exited0 and reported an authenticated login. Raw authentication stdout/stderr was discarded; no credentials were copied or committed. Evidence is boolean/version status only in [codex-check.json](evidence/i2/codex-check.json).

All worker/prompt/validation/durable-finish functions and all app models/routes have identical ASTs to b, and the Phase02/03 historical preservation tests pass. Original generation route remains FastAPI→worker→existing authenticated Codex CLI→validated file→persistent case revision. **No live image-generation call was submitted in I2**, so current image-tool access, quota, latency and live end-to-end image success remain unproven. No new provider or API fallback was added.

## Limitations and next phase

- This is safe backend preservation, not React integration. No API client/proxy/auth implementation changed; I3 has not started.
- Original backend has no user/tenant authentication; global job/image routes are not case-user access control. Keep it on loopback and apply the chosen real auth boundary during I3.
- One process-local generation lock and shared Codex output attribution remain prototype limitations. Text-only refinement may drift; 2D sheets are not real3D; no forensic accuracy or identity continuity claim is made.
- Historical private data and browser evidence are deliberately absent. No database schema merge or private runtime path handover occurred. Existing original projects/data remain the recovery anchors.
- Historical browser/operator scripts were excluded for protected-port/private-evidence coupling. This does not claim a fresh18-script pass; isolated equivalents/full UI QA remain later work.
- OWNER-SEC-01 and DEP-01 remain open; new ignore rules do not remove already-pushed private history.

Local checkpoint: commit titled `feat: preserve WitnessTrace backend with isolated runtime and tests` on the integration branch (resolve SHA with git log). It contains source/docs/tests only. Main/b/backend are unchanged, with no push. Stop after I2; await explicit NEXT for I3.
