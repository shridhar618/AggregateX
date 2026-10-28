# Final integration report

Project: **Revelio + WitnessTrace AI**. Date: 2026-10-29.

**Locally integrated and tested: PASS. Safe remote main publication: BLOCKED pending OWNER-SEC-01 owner remediation; remote pushing also requires explicit approval.**

## Delivered application

The primary frontend is the existing Revelio React/Vite application: landing/auth, Syne/Inter/IBM Plex Mono, sidebar/topbar/mobile navigation, owl/reticle dashboard, coral/charcoal and sage/cream themes, cards, studio and image/comparison components. Integrated mode is the default; the former renderer remains explicitly available as legacy source, not a generation fallback.

The gateway is part of Revelio FastAPI and uses its real account/session dependency. An exact route/asset allowlist forwards authenticated requests to loopback WitnessTrace. WitnessTrace's SQLite and file stores own cases, original statements, clarifications, 45-field drafts, jobs, immutable image lineage, preferred/selected revisions, edit projects, enhancement parameters, layouts and reports. The Codex CLI invocation and processing/store algorithms were retained.

Native React controls integrate cases, Lab, prompt review, refinement, history/preferences, comparison, library, reports and settings. Sketchpad/Enhance and reviewed multi-view reuse original engines inside bounded same-origin themed documents. The image editor stays mounted across hash navigation; tool switching preserves its document. Exact committed enhancement pixels are saved. Backend records synchronize to React after successful engine mutations.

See FEATURE_PARITY.md for every major feature and API_MAPPING.md for concrete requests. Multi-view explicitly remains AI-generated 2D interpretation, not geometrically accurate reconstructed 3D.

## Git recovery and delivery

- Original main: `/home/god/Documents/github/ssdnexus-t1-20`, baseline `f89093eaa45ace99b134093b563d1f30d3bbe5c0`.
- Old dirty integration checkout: `/home/god/Documents/github/ssdnexus-t1-20-integration`, b at `49f63ee4e242efe0c5aa4aef0a524652e75cfd5a`; left untouched.
- Verified I3 source tip: `4d3b17f1dba34efafd6b3319d6831e76e4f8912f`, whose parents contain safe source-only I2 `333f824`, I1 `1d0339f`, I0 `db59b9b`, and main baseline.
- Final isolated worktree: `/home/god/Documents/github/ssdnexus-t1-20-final-merge`.
- Final branch: `integration/final-ui-backend-merge`.
- Feature checkpoint: `2595906` (`feat: integrate WitnessTrace tools with Revelio case and revision UI`). Runtime/visual checkpoint: `c3a45a7` (`feat: finalize integrated startup, persistent editors and responsive case workspaces`). The final QA/documentation commit completes delivery; resolve exact hashes with `git log --oneline integration/final-ui-backend-merge`.
- The final local delivery fast-forwards clean main to the final integration tip; both refs identify the same completed code after delivery. `git rev-parse main integration/final-ui-backend-merge` gives the exact final SHA. Remote main remains at f89093e; no remote push was performed.

The final branch descends from main plus safe integration commits. b is not an ancestor and was not merged wholesale. No branches/worktrees were deleted; no dirty checkout was switched/reset/cleaned/stashed. Existing main/b/backend/integration refs were preserved. No non-fast-forward rewrite or force push was used.

## Verification

| Check | Fresh result / evidence |
|---|---|
| Revelio + gateway | **100 passed**: 76 original plus 24 gateway checks; `evidence/final/revelio-pytest.txt` |
| Unified installed runtime | Same **100 passed** under WitnessTrace's runtime; `unified-runtime-pytest.txt` |
| WitnessTrace | **56 passed**, existing dependency warning; `witness-pytest.txt` |
| Adapter | **7 passed**; payloads, validation, errors, cancellation and polling; `adapter-tests.txt` |
| ESLint / Vite build | PASS; `lint.txt`, `build.txt` |
| npm security audit | **0 vulnerabilities** after compatible lock updates; `npm-audit.json` |
| Legacy Revelio Chromium | **131 passed** freshly in explicit legacy mode; zero page exceptions/failed requests; `legacy-browser-summary.json` |
| Unified launcher | **5 passed**; occupied-port refusal, actual browser/session/case persistence/private runtime permissions/cleanup; zero generation; `startup-smoke.json` |
| I3 browser regression | **30 passed** in recovered checkout, using deterministic CLI fixtures; original I3 evidence preserved |
| Final integrated Chromium | **61 passed**, zero page exceptions; `browser-result.json`, `browser-checks.txt` |
| Visual evidence | **28** actual screenshots, ten studio and ten Settings states plus tools/navigation; screenshot manifest |
| Data integrity | Six saved revisions, all source/report hashes, exact preview/save RGBA equality, SQLite integrity/FKs, refresh and actual server restart PASS |

The full workflow registers a real local session, creates/freezes invented testimony, submits an explicit fixture generation, edits/saves Lab, generates a Lab revision and reviewed refinement, compares by keyboard, marks preferred, draws/saves an annotation, retains the canvas across navigation, enhances/saves, downloads persisted PDF/JSON/PNG, generates a fixture sheet, confirms four test crop rectangles, navigates/downloads angles, restarts the actual backend, checks every revision/report hash, then verifies case switching and unavailable-backend recovery. Four CLI fixture generation jobs produce six total revisions with local sketch/enhancement children. These fixture patterns are expressly **not AI results**.

## Real-generation evidence

No additional real Codex generation was submitted. I3 already recorded exactly one successful authenticated UI → gateway → original CLI worker → persisted image → browser/download invocation. Sanitized evidence is in I3_VERTICAL_SLICE.md and `evidence/i3/live-result.json`.

- Original saved image SHA-256: `5aaf6eece63882e3d1e83bd45161ff580fa7722222b9aa32ee8a9adcc935ff2b`.
- Normalized exported PNG SHA-256: `7e9cc1675435d7ee8bdddb0bf08d4229a97f0c6001e92ebbe96df33d800fa90c`.

Those scopes differ deliberately. No real face image, raw worker output, account secret or SQLite runtime was committed as evidence. The final verifier refuses real-generation mode.

## Security, data and remaining boundaries

All newly introduced files were reviewed for runtime/private material. New screenshots contain invented cases/geometric patterns only. Existing source stores and private data were not overwritten. Integrated launch/storage directories are external to Git. Protected 8000/8001 listeners were left untouched.

The gateway provides real web-session enforcement, same-origin JSON mutations, bounded bodies, no credential forwarding, no arbitrary target/path proxy, and case-resource ownership checks in the original stores. The preserved upstream is still an unauthenticated localhost service; signed-in local users share the collection. This is not a public multi-tenant deployment. Codex installation does not guarantee quota, tool availability, face accuracy or identity consistency. Interrupted jobs do not gain a new resume/cancel feature.

**OWNER-SEC-01 remains open:** remote b history already contains private runtime material. Owners must assess/remediate it and record publication clearance. No shared history rewrite was authorized or attempted. This gates remote publication, not the completed safe local integration. See SECURITY_REVIEW.md.

## Start and rollback

Install the pinned WitnessTrace environment and npm dependencies as documented in STARTUP_GUIDE.md, then `npm run dev`. Open `http://127.0.0.1:5182/register` or `/login`. The launcher uses 5182/8021/8022, refuses occupied ports and stops only its children. Existing collections are selected through explicit matching storage-directory configuration; none is silently copied.

Rollback uses a separate worktree/recovery branch or reviewed reverts of the integration checkpoints. Preserve runtime files; restore matching database/file backups only with the owning service stopped. The original b checkout is not a rollback scratch directory.
