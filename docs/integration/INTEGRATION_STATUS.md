# Revelio + WitnessTrace integration status

Updated 2026-10-29. The continuous-execution instruction supersedes the historical NEXT gates in I0–I3 documents. No further phase confirmation is required.

**Local integration: PASS. Remote publication: BLOCKED by OWNER-SEC-01 pending owner remediation and explicit push approval.**

| Phase | Final result |
|---|---|
| I0 audit | Preserved source/data/history inventory; baseline main f89093e, b 49f63ee |
| I1 UI foundation | Existing React/landing/auth/design retained; reference evidence preserved |
| I2 backend foundation | Safe source-only WitnessTrace import; original worker/stores/static algorithms retained |
| I3 connection | Existing 4d3b17f verified and reused; no repeated real generation |
| I4 feature parity | 45-field Lab, refinement, immutable revision selection/preference, comparison, Sketchpad, Enhance, multi-view, library, reports and settings connected |
| I5 visual QA | Actual studio and Settings matrices at 1920/1440/1280/768/390 in dark/light; sidebar, contrast, proportions and overflow corrections |
| I6 security/data | Session-protected allowlisted gateway, case-resource validation, staged-data audit, six-revision/report checksum and SQLite verification |
| I7 regression | 100 Revelio/gateway tests; 56 WitnessTrace tests; 100 Revelio tests also on the unified runtime; seven adapter tests; lint/build; 61 integrated + 131 legacy Chromium checks; five startup checks |
| I8 Git delivery | Separate safe checkpoint commits; clean local main fast-forward at final delivery; no b-history merge, reset or remote push |

## Recovery and architecture

`git worktree list --porcelain` verified the dirty old integration directory remained on b at 49f63ee. I3 commit 4d3b17f was a valid integration tip based on main, through I0/I1/I2. A fresh worktree was created at `/home/god/Documents/github/ssdnexus-t1-20-final-merge`, branch `integration/final-ui-backend-merge`. The dirty b checkout, runtime directories and private data were untouched.

React is primary and integrated mode is now the default. Original Revelio account sessions protect `/wt-api`; WitnessTrace owns all integrated case/image/revision/report data and still invokes the original Codex worker. Sketchpad/Enhance reuse the original engine document in a bounded, authenticated, themed surface; its mounted document survives hash navigation. There is no second WitnessTrace case database or provider substitution.

## Evidence and operating boundaries

See FINAL_INTEGRATION_REPORT.md, FEATURE_PARITY.md, API_MAPPING.md, VISUAL_QA.md, SECURITY_REVIEW.md and STARTUP_GUIDE.md. Fresh evidence is under `evidence/final/`; earlier I1/I2/I3 evidence remains historical reference. I3's one real Codex result and checksum evidence were retained; all new generation regression jobs use a labelled geometric CLI fixture, never a fake face passed off as AI.

Completed case/selection/testimony/image/report records survived actual owned-process restarts. Every one of the six source image hashes and all report-file manifest hashes verified. Enhancement preview pixels exactly matched saved pixels. Original data stores were not migrated or overwritten. Ports 8000/8001 were not contacted or managed; listener snapshots compared unchanged.

Local shared collection only: underlying WitnessTrace is still unauthenticated on loopback, and local OS processes can reach it directly. No public deployment or per-user tenancy is claimed. OWNER-SEC-01 concerns private artifacts already in remote b history; no history rewrite or remote push occurred. Compatible dependency updates resolved the 13 npm advisories; final audit reports zero. Historical legacy Python pins are not the unified startup environment.

Final local main/ref delivery is recorded in FINAL_INTEGRATION_REPORT.md and the final handoff. Rollback and safe startup are documented in STARTUP_GUIDE.md.
