# I3 working vertical slice

Date: 2026-10-29. Result: **PASS**, including one real integrated Codex generation. Scope stops at case/testimony/generation/status/image/download/persistence. I4 has not started.

## Working path

The original landing, account pages, navigation, themes, notifications and shell remain. With explicit `VITE_WITNESSTRACE_LOCAL=1`, Workspace and New Sketch use real WitnessTrace cases through the existing AppProvider. The integration uses the original studio grid, panels, button typography and SketchViewer, with scoped CSS for responsive variable-size images. Original NewSketch/Workspace implementations remain unchanged for legacy mode; they are not used as a procedural fallback for WitnessTrace generation.

1. Register/sign in through the existing server session mechanism.
2. Workspace reads real case summaries and count. Select a case or create a clearly synthetic case.
3. New Sketch freezes the exact original account using its optimistic revision. Frozen original is read-only; later information is separately sourced clarification.
4. Explicit Generate refreshes durable case jobs and reviews the backend-built prompt budget before POSTing `/api/generate`.
5. The original FastAPI worker calls the original authenticated Codex subprocess. Browser cancellation/navigation does not cancel the server job.
6. Adapter polls the persisted job. Only its saved validated Case version supplies the canonical image URL to SketchViewer.
7. Viewer supports image error, zoom, Fit and case-owned PNG download. Refresh restores selection from the ID and reads canonical saved records. Restart persistence was exercised with isolated synthetic storage.

## Fresh verification and evidence

| Check | Result | Evidence |
|---|---|---|
| Existing WitnessTrace + relocation tests | 56 passed; one existing dependency warning | `evidence/i3/witness-pytest.txt` |
| Original Revelio + new gateway tests | 84 passed (76 original, eight gateway checks) | `evidence/i3/revelio-pytest.txt` |
| Node adapter unit tests | seven tests passed | `evidence/i3/adapter-tests.txt` |
| ESLint | passed, no warnings | `evidence/i3/lint.txt` |
| Vite production build | passed | `evidence/i3/build.txt` |
| Chromium deterministic workflow | 30 checks passed | `evidence/i3/browser-result.json`, `browser-checks.txt` |
| Real integrated generation | exactly one submission; validated image displayed/downloaded | `evidence/i3/live-result.json`, `live-checks.txt` |
| Frontend preservation | 64 of 69 manifest files unchanged relative to I2; five reviewed connection/shell/viewer/proxy edits | `evidence/i3/frontend-preservation.json` |
| WitnessTrace backend preservation | no I3 changes | Git diff from I2 |

Adapter tests exercise real route/payload serialization, bare list shape, ID validation, HTTP validation detail arrays, 401, malformed JSON/shapes, network failure, request timeout, cancellation, working/complete/failed lifecycle, polling deadline and canonical image URL rejection. Neither unit tests nor polling automatically resubmit generation.

Gateway tests verify session enforcement for cases, jobs submission and images, disabled/unsafe targets (including 8000/8001), path allowlist, cross-origin mutation rejection, JSON requirement, no forwarded cookies/authorization, no-store and connection failure normalization. These tests mock only the upstream transport; the Chromium test uses actual separately running FastAPI services and real sessions.

The deterministic browser uses an explicit fake CLI producing a **720×480 labelled geometric pattern, not an AI image**. It exercises the real production worker/output validation/store, rather than mocking browser success. Two fixture submissions occur: one completes and one deliberately fails. Double-clicking the initial Generate action produces exactly one initial job; refresh/navigation does not resubmit. Additional checks cover live connection/case creation/freeze, download and source checksums, actual backend process restart, eight viewport/theme states, viewer zoom/Fit, missing image, failed-job no-extra-version/prior-image retention, invalid case, invalid testimony, append-only clarification, second-case selection/cleared input and backend unavailability recovery. No JavaScript page exception occurred.

Repeat deterministic verification only:

```bash
node --test scripts/tests/witnesstrace.test.mjs
backend/.venv/bin/python -m pytest -q backend/tests
(cd witness-backend && .venv/bin/python -m pytest -q)
npm run lint
npm run build
witness-backend/.venv/bin/python docs/integration/evidence/i3/verify_browser.py
```

The browser verifier refuses occupied 5182/8021/8022, uses temporary mode-0700 external runtime directories and stops only its own services. Ports 8000/8001 were never requested or managed; the existing 8001 listener remained PID 143217. All isolated services were stopped.

## One real Codex test — not a mocked result

Authentication was checked privately without retaining tokens or raw output. No other `codex exec` worker was active before the attempt. The browser created a separate synthetic case and froze invented testimony. **Exactly one real `/wt-api/api/generate` POST** traversed the session gateway to WitnessTrace, whose unmodified worker used the installed real Codex binary with its normal authenticated home (no fake CLI/home overrides). No alternative provider was invoked.

The job completed; its saved version was returned by the case store and rendered as a decoded image in the React viewer. The original image served through the gateway matched the stored version checksum:

`5aaf6eece63882e3d1e83bd45161ff580fa7722222b9aa32ee8a9adcc935ff2b`

The browser PNG download matched the backend's canonical normalized export bytes:

`7e9cc1675435d7ee8bdddb0bf08d4229a97f0c6001e92ebbe96df33d800fa90c`

These are different checksum scopes: source image bytes versus normalized PNG export. They are not claimed byte-identical. No generated facial image, real account secret, worker log or SQLite database was added to repository evidence. Only sanitized pass results/checksums are retained. Temporary integration records were removed with their disposable runtime; the Codex tool's own generated-image directory was not deleted or altered by cleanup. This one result proves the working integration path, not scientific face accuracy, identity consistency or future quota availability. **Do not rerun the verifier's `--live-once` mode automatically; I3's one-real-attempt allowance has been used.**

## Visual review

Eight actual Chromium full-page screenshots are indexed in `evidence/i3/screenshot-index.md`. Browser viewport is width 1440/1280/768/390 × height 1000; full-page PNG height reflects content. Both dark and light themes were rendered. All eight captures were inspected visually, with comparison to I1's actual New Sketch reference (including `dark-1440-new.png`).

The dark charcoal/coral and cream/sage palettes, branded sidebar, topbar, fonts, panels and viewer toolbar remain recognizable. Three desktop columns collapse to two and then one; no horizontal document overflow occurs. Variable-size landscape content is contained, not distorted into a 4:5 image. The case chip is hidden at ≤900px in integration mode to prevent the longer real IDs squeezing the title. The 390px title truncation, long desktop sidebar label clipping and dark viewer in light theme are existing documented design characteristics; broader corrections remain I5. The case/immutable-description controls replace legacy procedural generation controls only in the opt-in slice; deferred tools are clearly labelled.

## Boundaries and limitations

- Local development only. Gateway requires real sessions; direct WitnessTrace localhost port still lacks authentication. No LAN/public deployment or user-level tenancy is approved or claimed.
- Original actual case databases/images are untouched; synthetic test data only. Original project source copies are unchanged.
- Library, Compare, Settings retain original legacy implementations and show a disconnected-feature notice. Their WitnessTrace adaptation and full Character Lab/Sketchpad/Enhance/Multi-view/Reports remain I4.
- WitnessTrace has no initial-generation idempotency key or cancellation endpoint. The client locks duplicate UI operations, checks persisted jobs and never automatically retries a POST. After ambiguous submission, reconnect and inspect the existing job first.
- Polling/reconnect recovery does not resume an interrupted worker after a process restart; the preserved backend records such a job failed. Completed-record restart persistence passed.
- OWNER-SEC-01 and DEP-01 remain open; ignore rules do not remediate existing remote history. No merge or push performed.

Rollback: stop only owned local services and revert the I3 checkpoint commit, or inspect I2 `333f824` in a separate worktree. No source project, private runtime collection or shared branch was overwritten.
