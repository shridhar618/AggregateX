# Integration status

Updated: 2026-10-28. Active worktree: `/home/god/Documents/github/ssdnexus-t1-20-integration`.
Branch: `integration/revelio-witnesstrace`; base `f89093eaa45ace99b134093b563d1f30d3bbe5c0`.

## I0 — PASS: audit and architecture recommendation

Completed:
- Audited required branch/status/diff/tree/log/remote commands and fetched remote refs. main/b/backend refs match remote; original main checkout clean and preserved.
- Created isolated integration worktree/branch from main. Verified complete-history Git bundle outside repository.
- Located/read full committed handoff after supplied parent-path file proved absent; cross-checked frontend/API/auth/CSS and complete backend source.
- Established b really contains committed Phase 08 code. All 94 core/static/test files match original and migrated copies. Separate migration already exists at newBackend.
- Backed up both source/runtime copies privately, hashed files, restored SQLite backups and checked integrity/FKs/counts. Verified 23/23 original and 25/25 migrated revision images.
- Selected Option A, actual React frontend plus preserved WitnessTrace services/engines. Recorded authentication integration and imperative-engine risks.

Files created: `INTEGRATION_BASELINE.md`, `ARCHITECTURE_DECISION.md`, this status file. No production source edits. Private manifests/backups/logs are under `/home/god/Documents/github/integration-audit-private` (0700) and are not staged.

Fresh tests: npm ci; npm run lint PASS; npm run build PASS; Revelio pytest 76 passed (20.42s); WitnessTrace pytest 54 passed (28.26s), one existing Starlette/httpx deprecation warning; pip check PASS in both environments; Git bundle and archive hash verification PASS; database restore/integrity/FK checks PASS. WitnessTrace initially had 2 missing-fixture failures in the isolated test copy; copying original code-only historical fixtures fixed them; full suite rerun passed.

Known baseline limitations: npm audit reports 13 advisories (10 high/2 moderate/1 low); original Revelio Pydantic/core pins are yanked; committed b already contains private runtime artifacts on remote; no comprehensive secret scan or history rewrite performed. Existing original-to-migrated differences are a case revision counter and selected/preferred state, with all original statements/versions retained. No fresh screenshots/browser regression, live generation, service restart or integrated endpoint tests in I0. These are not claimed as completed. No port 8000 contact or management.

Checkpoint: the documentation-only commit titled `docs: audit integration sources and record I0 architecture` is the I0 checkpoint (resolve SHA with `git log -1` after commit). Existing main, b and backend unchanged. No push/merge performed.

## I1 — PASS: frontend preservation and visual baseline

Completed only I1 on explicit NEXT. The React source, CSS layers, original backend, package manifests and assets remain unchanged: 69 frontend/config/asset files match main base f89093e byte-for-byte. Option A remains selected; no WitnessTrace source/API integration started.

Evidence: 116 real Chromium screenshots, eight surfaces × five widths × two actual DOM themes (80 matrix states) plus 36 section/modal/editor/loading/error captures. Screenshots were visually reviewed in contact sheets and selected native-resolution images. Computed tokens, typography, grid/shell dimensions, routes and per-image overflow/asset checks are recorded. Password fields are masked; all accounts/descriptions/images are isolated synthetic Revelio procedural fixtures. Neither paid generation nor Codex was invoked.

Tests: npm run lint PASS; npm run build PASS (70 modules); 131 browser/API checks PASS, including all 80 active-theme checks; evidence verifier PASS for all screenshot hashes and 69 unchanged source files. Zero JavaScript page exceptions, zero failed requests/broken images. Console resource messages: 45 expected 401 auth responses and two controlled health 503s. Owned services ran only on 5182/8021 and were stopped; original 8001 PID 143217 remains unchanged; ports 8000/8001 were never contacted or managed.

Created `I1_VISUAL_BASELINE.md`, `I1_FRONTEND_API_DEPENDENCIES.md`, `I1_DEPENDENCY_SECURITY.md` and `evidence/i1/` (capture/verification Python scripts, screenshot index/hashes, browser results, source manifest, audit risk summary and lint/build/audit logs). Full changed paths are recorded in `evidence/i1/files-changed.txt`.

Baseline defects retained/documented: Settings overflow (812/768 and 518/390 in both themes), landing headline clipping, long sidebar label clipping, layered/legacy theme colors, unreadable light-theme dark-block captions, stale privacy copy and auth offline classification. No CSS/functionality changes were made to hide defects. Real mobile touch, full accessibility certification, hosted generation, destructive execution and live WitnessTrace workflows were not verified in this phase.

Security gates: **OWNER-SEC-01 OPEN** — owners must classify/remediate already-pushed runtime material in b and record clearance before final shared merge; limited key/token-pattern scan is not privacy clearance. No history rewrite/force-push/deletion performed. **DEP-01 OPEN** — 13 dev-toolchain npm advisories (10 high/2 moderate/1 low); runtime-only audit reports zero. Compatible fix candidates documented; no upgrades applied.

Checkpoint: local commit titled `docs: preserve Revelio visual baseline and record I1 risks` (resolve SHA from git log). No merge, cherry-pick or push. I2 requires a new explicit NEXT.

## Remaining phases

| Phase | Status | Next required work |
|---|---|---|
| I1 frontend preservation | PASS | See I1 reports/evidence; source preserved unchanged |
| I2 backend preservation | NOT STARTED | Selectively preserve verified b source/tests without runtime artifacts |
| I3 API integration | NOT STARTED | Actual contracts/adapter/auth/proxy and integration tests; create API_MAPPING.md |
| I4 complete features | NOT STARTED | Coherent full UI and engine lifecycle parity; create FEATURE_PARITY.md |
| I5 visual fidelity | NOT STARTED | All viewport/theme screenshots and fixes; create VISUAL_QA.md |
| I6 data/security | NOT STARTED | Transactional path/data/auth/security verification |
| I7 automated QA | NOT STARTED | Full browser workflow, restart/export checks and permitted real CLI generation |
| I8 final Git | NOT STARTED | Final reviewed integration commit/merge preparation; create FINAL_INTEGRATION_REPORT.md |

STOPPED: awaiting explicit NEXT. I1 is complete; I2 has not begun. Do not merge main before I8; do not push remote main without explicit approval of final commit/push.
