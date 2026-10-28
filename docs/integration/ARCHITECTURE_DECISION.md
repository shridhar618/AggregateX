# Architecture decision: retain Revelio React and WitnessTrace services

Date: 2026-10-28. Status: selected for phased implementation; I0 contains no implementation.

Keep **Option A**: main's React/Vite application as the single frontend, with a domain adapter to the existing WitnessTrace FastAPI application. Preserve the Codex CLI worker, stores and existing image-processing engines. Preserve the landing page and shell. This is not a merge of Revelio's procedural renderer into WitnessTrace generation.

## Evidence and comparison

The full root UI_INTEGRATION_HANDOFF.md was read. Its vanilla recommendation was reasonable given its then-missing WitnessTrace source, but the current task explicitly prioritizes the real React UI. Both sources are now available. The 94 matching backend/static/test files establish a stable functional source, while main's UI passes lint/build and its original backend passes 76 tests. WitnessTrace independently passes 54 tests.

| Criterion | A: React primary | B: vanilla design port |
|---|---|---|
| Visual fidelity | Keeps actual shell, page compositions, landing, theme, modal, compare, viewer, icons and animations | Recreates React markup/interactions; large CSS and responsive rules must be transferred and reconciled |
| Functionality | Stores/worker remain intact; domain UI must use case/job contracts | Existing global DOM flows remain mostly intact |
| Complexity | Medium-high: schema-driven Lab, case context, async jobs, legacy engine lifecycle | Medium-high: new shell/dashboard and visual work across every screen, preserving landing separately |
| Regression risk | Higher for DOM engine integration; explicit mount/state/cleanup tests needed | Lower for existing tools, higher for visual fidelity and shell interactions |
| Testing burden | Existing backend suite plus adapter tests and full browser tool lifecycle | Same backend suite plus recreated UI interaction/fidelity tests |
| Maintainability | One existing React app; localized imperative engines; no duplicate domain storage | Existing vanilla globals remain; visual components duplicated from React references |
| Time | More API/state work; substantial actual frontend reused | Less functional plumbing; more UI recreation; no reliable numeric estimate established |

A is preferred because no backend rewrite is necessary, most UI primitives already consume props, and the only imperative processing engines can be preserved in a bounded DOM host. B would discard substantial working React interactions and redo the visual foundation. This is a source-based feasibility decision, not a claim that the integration has passed browser tests.

## Planned boundaries

- Retain `src/main.jsx`, shell, routing, global preferences, landing and themes. Extend navigation for all WitnessTrace workspaces. Move selected-case ownership into case context; do not clear it just because NewSketch unmounts.
- Add one API service (e.g. `src/api/witnesstrace.js`) using real case/version IDs, persisted Draft schema, optimistic case revision, request keys and structured errors. Do not emulate RV sketch storage or silently coerce 45 fields into 20 traits.
- Generate only on explicit action. Submit `/api/generate`, `/refine` or `/multiview`; poll `/api/jobs/{job_id}` and refresh persisted case after completion. Keep failed/prior images visible; never equate HTTP 202 with image success.
- Keep core modules together under an explicit backend directory/app-dir to avoid collision between WitnessTrace `app.py` and Revelio `backend/app` package. Serve one same-origin application; proxy API, images and necessary worker/static resources during development. Production app must serve React SPA fallbacks without shadowing downloads.
- Keep `case_store.py`, lab schema and all editing/report stores as the source of domain validation. Use existing `WITNESSTRACE_DATA_DIR` for the migrated case store. Outputs/work currently derive from app.py's own root, so any relocation must explicitly retain/copy and verify those paths in I2/I6. Do not change the Codex argv/prompt/subprocess/environment filtering or image attribution logic.
- WitnessTrace Enhance really processes pixels in `static/enhance-worker.js`; the backend validates/saves results. Preserve worker algorithm, committed preview and request signatures. CSS-only filters would violate parity.
- Sketchpad/Enhance are IIFEs reading global `$`, `activeCase`, `busy`, `permitted`, etc.; attach handlers at evaluation and capture fixed IDs. They cannot simply be imported in a React effect. Introduce narrow mount/unmount adapters accepting owned DOM/state/API hooks, retaining drawing, operation replay, transforms and worker algorithms. Keep the engine host mounted across relevant tabs; explicitly cancel in-flight work, dispose observers/listeners/workers and confirm dirty case switches. Do not iframe a second application or place both frameworks in charge of the same DOM subtree. I4 must prove tool-by-tool parity and StrictMode/re-entry behavior before proceeding.
- Render all 45 schema fields/seven groups with the existing trait/control visual vocabulary. Preserve Unknown, uncertainty, exact quote/source validation, drafts and explicit prompt review.
- Adapt Library to real cases, Compare to actual versions/lineage/preferred, and Settings to actual CLI/backend/storage facts. Remove unsupported delete/rename/provider choices from active flows instead of presenting no-op controls.
- Preserve landing layout and motion. Its live procedural demos must be adapted into truthful saved synthetic examples or explicit Codex-backed workflow entry; no generation on slider movement and no simulated AI success. Exact presentation is I1/I4 work.

## Authentication decision

Preserve the verified Revelio cookie login boundary. Its original API implements scrypt password hashes, hashed opaque sessions, HttpOnly SameSite=Strict cookies, logout and throttling; its authentication tests pass. WitnessTrace itself has no login or user ownership model. Do not make `me()` return a fake user or bypass login on network failure.

I3 should reuse existing authentication services/router and apply their dependency to WitnessTrace saved-data, job, image and export routes within the single service. Retain the existing account store for identities only; WitnessTrace remains the only case/revision store. This does not authorize conversion of unrelated sketch records into cases. Public landing assets/limited health checks may remain public. All signed-in users of this **local single-workstation installation** share the existing case collection; do not imply per-user tenancy. No public deployment or multi-user access claim is justified. If actual reuse fails, stop and document the concrete issue rather than silently disabling authentication.

## Data, assets and delivery

Use committed b only for explicitly selected code/test/docs files, verified against newBackend and the original. Do not merge/cherry-pick its wholesale replacement commit. Do not import data, evidence images, raw worker logs, reports, migration-private or credentials. Two source-only historical app.py fixtures are required by preservation tests and should be retained as tests/fixtures with test-path adjustments when appropriate; runtime evidence is not needed in Git.

Keep all runtime data locally with backups. Original 11-case source remains untouched; migrated 13-case state is the proposed active collection. I0 verified original versions/statements retained and documented existing mutable selection/revision differences. Do not blindly combine databases. The selected case DB has no user tenancy; route-level case ownership checks must remain effective.

Existing brand assets remain preserved in main's source history; ownership remains unverified. No new third-party marks or endorsement language are authorized. Do not port unverified logos from external sources. Font licensing/offline provisioning and fresh visual reference screenshots remain I1 work.

## Gates and reversibility

Each NEXT authorizes one phase only. I1 preserves frontend and captures references; I2 imports source only with tests; I3 implements real adapter/auth/proxy integration; I4 exposes full functionality; I5 validates visual fidelity; I6 rechecks data/security; I7 runs complete automated/browser/live-generation checks; I8 reviews, commits and prepares main safely. No main merge occurs before I8 and no remote main push without explicit final approval.

If engine lifecycle adaptation requires changing pixel algorithms or replacing whole working engines, reassess this decision with concrete failing tests before choosing B. No fallback is implemented in I0. Keep changes incremental and reversible by commit; originals, bundle and restored backups remain recovery anchors. No port-8000 process is touched.
