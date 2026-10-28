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

## Remaining phases

| Phase | Status | Next required work |
|---|---|---|
| I1 frontend preservation | NOT STARTED | Await NEXT; capture rendered React references and preserve/fix phase-scoped frontend concerns |
| I2 backend preservation | NOT STARTED | Selectively preserve verified b source/tests without runtime artifacts |
| I3 API integration | NOT STARTED | Actual contracts/adapter/auth/proxy and integration tests; create API_MAPPING.md |
| I4 complete features | NOT STARTED | Coherent full UI and engine lifecycle parity; create FEATURE_PARITY.md |
| I5 visual fidelity | NOT STARTED | All viewport/theme screenshots and fixes; create VISUAL_QA.md |
| I6 data/security | NOT STARTED | Transactional path/data/auth/security verification |
| I7 automated QA | NOT STARTED | Full browser workflow, restart/export checks and permitted real CLI generation |
| I8 final Git | NOT STARTED | Final reviewed integration commit/merge preparation; create FINAL_INTEGRATION_REPORT.md |

STOPPED: awaiting explicit NEXT. I1 has not begun. Do not merge main before I8; do not push remote main without explicit approval of final commit/push.
