# I1 Revelio visual baseline

Status: PASS — preservation and evidence capture. This is a baseline of the existing application, not certification that every existing defect is fixed or that WitnessTrace integration is complete.

## Scope and preservation

The application rendered directly from the integration worktree's actual React/Vite source. Source/config/assets remain byte-identical to main base `f89093eaa45ace99b134093b563d1f30d3bbe5c0`: all **69 files** in [source-manifest.json](evidence/i1/source-manifest.json) match SHA-256 and Git source bytes. No frontend, CSS, backend, package or lockfile was modified. Option A remains the established architecture; no backend adapter or WitnessTrace import was started.

Read the I0 baseline, decision and status. The supplied parent-path handoff remains absent; the unchanged 1,314-line repository-root `UI_INTEGRATION_HANDOFF.md` is the actual reference. Component/source inspection and rendered measurements cross-check its claims; deviations are recorded below. Existing logo assets are preserved as reference, with ownership unverified.

## Reproducible environment and evidence

- Chromium **153.0.8010.12**, Playwright through an existing local Python environment; desktop browser at all widths, deviceScaleFactor 1. Viewport resize testing does not emulate a mobile device's touch, browser chrome or software keyboard.
- Vite on **127.0.0.1:5182**, original Revelio FastAPI on **127.0.0.1:8021**. Both ports were checked for availability and started with explicit arguments. Original backend ran with a temporary `REVELIO_DATA_DIR`, no inherited Revelio/Verisketch/Gemini settings and hosted provider disabled. Neither port 8000 nor 8001 was contacted, stopped or restarted. The existing port-8001 PID 143217 remained unchanged.
- Test account and sketches were created exclusively in that temporary database via real API/form flows. Two seeded fictional procedural sketches and a second revision expose history/comparison. A third sketch was saved through the UI. These are **Revelio procedural illustrations, not AI, Codex outputs or WitnessTrace cases**.
- Password inputs are masked gray in screenshots; no passwords, cookies, tokens, account DB or browser storage state is retained in evidence. Temporary server data/logs were deleted by the harness after both owned processes stopped.
- The 80-state matrix covers eight surfaces × five widths × two themes. An additional 36 captures cover sections, dialogs, input/refinement/history, full-page layouts, loading and controlled errors: **116 actual screenshots** total. Matrix uses reduced motion for stable frames. A separate normal-motion capture confirms hero Canvas and 30 CSS animated elements are present; timing aesthetics are not fully evaluated.
- [browser-results.json](evidence/i1/browser-results.json) records route, viewport, active DOM theme, source rendering, computed styles/tokens, overflow, broken-image checks, console/resource events and requests. [screenshot-index.md](evidence/i1/screenshot-index.md) lists every exact path and layout result. [screenshot-sha256.json](evidence/i1/screenshot-sha256.json) fixes the captured files by hash.
- Every accepted image was inspected in contact sheets, with native-resolution spot checks of editor, landing, settings, dialogs and mobile defects. No new UI was judged from CSS alone. Early harness attempts were rejected/corrected for lazy-image waits, selectors, styled-checkbox targets, hash-only theme initialization and boot remount timing. Only the final successful run is accepted; it explicitly checks all 80 active themes.

### Re-run

From the integration worktree, after `npm ci` and installation of `backend/requirements.txt` in `backend/.venv`, run:

```bash
# Use a Python interpreter with Playwright and its Chromium installed.
/home/god/Documents/github/newBackend/.venv/bin/python docs/integration/evidence/i1/capture_baseline.py
python docs/integration/evidence/i1/verify_evidence.py
npm run lint
npm run build
```

The harness refuses occupied 5182/8021 listeners, creates isolated reference data, disables hosted generation and stops only its own subprocesses. It does not read the newBackend database or start WitnessTrace; the interpreter path merely supplies Playwright. Never substitute `npm run dev`/dev-all defaults. Ignore `--states-only` for authoritative capture; it is a harness-debug convenience that preserves a previous matrix. Re-running intentionally overwrites the synthetic baseline captures/results.

## Screen and component inventory

| Step | Surface / route | Actual owning sources and styles | Data dependence | Current health / evidence |
|---|---|---|---|---|
| 1 | Landing `/` | LandingPage, LandingNav, Hero, Sections (Statement/Band/Features/Workflow), LiveDemo, EditorShowcase, Trust (Privacy/Capabilities), Pricing, Closing (FAQ/CTA/Footer), motion.jsx; landing.css/index.css | EngineProvider health/catalog; demo extract/render/render.png; showcase local revisions | Hero/nav/features/demo/editor/footer captured; live procedural demo works; desktop and mobile headline clipping; see dark/light-1440-landing-full.png |
| 2 | Login `/login` | AuthPage, brand/Logo, ThemeToggle; auth.css + landing.css | auth/me/login and genuine cookie | Validation, invalid login and actual successful login exercised; dark/light all widths |
| 3 | Registration `/register` | AuthPage Field validation; same styles | auth/me/register | Empty-form validation captured; real account creation API verified; full registration submit through the browser form not exercised |
| 4 | Workspace `/app#/workspace` | App shell; Sidebar, Topbar/AccountMenu/notifications, CaseClock, BootScreen, Toasts; Workspace; app.css/index.css | context health/catalog/auth, stats/listSketches/activity | Actual synthetic totals 2 sketches/3 revisions in matrix; cards/activity/status; clipped long sidebar label |
| 5 | New Sketch `/app#/new` and `?sketch=…` | NewSketch state owner; DescriptionPanel/GuidedForm/WitnessMerge; TraitPanel/AdjustPanel/RefinePanel; ModeSelector/ReferenceUpload; SketchViewer/CompareSlider/Pipeline/RenderNotes | catalog and profile contracts; extract/render; generate/revisions/get/update | Populated matrix, empty/guided/witnesses/extracted/zoom/adjust/refine/saved/full states; real procedural save works |
| 6 | Library `/app#/library` | Library + HistoryModal; EmptyState/ConfirmModal; app.css | list/search/get/update/delete + download URLs | Cards, search-empty, actual history modal, cancellation and exports checked; destructive execution not performed |
| 7 | Compare `/app#/compare?sketch=…` | Compare/Picker + CompareSlider; CompareSlider.css/app.css | list/get cached by sketch ID; catalog differences | Actual revisions, keyboard/drag, picker and split view verified; no identity score implied |
| 8 | Settings `/app#/settings` | Settings, ConfirmModal, context preferences; app.css/index.css | storage/health/deleteAll | Actual provider status, privacy/prefs, recheck/theme, gated wipe dialog; provider overflow at 768 and 390 |

All `/app` routes require the original real cookie session. `/app` uses the custom hash router, not a router library. Landing and authentication remain separate lazy entry surfaces in one build. Shell overlays, generated error notices and loading states remain real source components.

## Effective design tokens

These values were read from `getComputedStyle(document.documentElement)` in the **populated 1440px studio**, after the final CSS overrides and theme initialization. No token layers were flattened or changed.

| Token / role | Dark | Light |
|---|---|---|
| `--bg` | `#090909` | `#faf6e9` |
| `--bg-2` | `#111111` | `#f5f1e2` |
| `--panel` | `#171717` | `#fffdf6` |
| `--panel-2` | `#202020` | `#fffdf6` |
| `--panel-3` | `#2b2b2b` | `#edf2d9` |
| `--border` | `#393632` | `#d5e1b9` |
| `--border-strong` | `#5b554e` | `#a0c878` |
| `--text` | `#eee8dc` | `#273323` |
| `--text-2` | `#c2b9aa` | `#56634c` |
| `--text-3` | `#8a8379` | `#747e69` |
| `--cyan` | `#ef5539` | `#527642` |
| `--blue` | `#b7a992` | `#64854e` |
| `--amber` | `#ef5539` | `#ffb547` |
| `--red` | `#ff5d6c` | `#ff5d6c` |
| `--green` | `#8fa38b` | `#38d996` |
| `--sidebar-w` | `248px` | `248px` |
| `--topbar-h` | `60px` | `60px` |
| `--r-lg` | `14px` | `14px` |
| `--t` | `240ms` | `240ms` |

Inter is the interface font, Syne the display/headings, IBM Plex Mono metadata/labels. The browser loaded used Google Fonts faces successfully. Unused unicode subsets/weights remain `unloaded` in FontFaceSet, which is not an asset failure. Fonts remain externally loaded, so offline rendering is not certified. `--cyan` is coral/sage; `--blue` is a neutral/secondary accent despite historical names. Shadow and focus-ring strings plus all measured font stacks are recorded per screenshot in JSON.

The measured light amber/red/green retain legacy bright values, matching the handoff's warning; no contrast pass was performed. Hard-coded dark viewer and cyan reveal accents remain visible in the cream theme. These are future integration design fixes, not new I1 changes.

### Computed component measurements

| Element / property (1440 studio unless noted) | Dark | Light |
|---|---|---|
| `.sidebar` width | `248` | `248` |
| `.sidebar` padding | `16px 12px` | `16px 12px` |
| `.topbar` height | `60` | `60` |
| `.topbar` padding | `0px 24px` | `0px 24px` |
| `.content` padding | `28px 24px 40px` | `28px 24px 40px` |
| `.studio__grid` gridTemplateColumns | `340px 412px 360px` | `340px 412px 360px` |
| `.studio__grid` gap | `16px` | `16px` |
| `.viewer__stage` height | `594` | `594` |
| `.viewer__stage` backgroundColor | `rgb(6, 9, 14)` | `rgb(6, 9, 14)` |
| `.viewer__stage` padding | `22px` | `22px` |
| `.viewer__frame` aspectRatio | `4 / 5` | `4 / 5` |
| `.viewer__img` objectFit | `contain` | `contain` |
| `.panel` borderRadius | `14px` | `14px` |
| `.btn--primary` height | `44` | `44` |
| `.btn--primary` background | `rgb(239, 85, 57) none repeat scroll 0% 0% / auto padding-box border-box` | `rgba(0, 0, 0, 0) linear-gradient(rgb(160, 200, 120), rgb(147, 188, 107)) repeat scroll 0% 0% / auto padding-box border-box` |
| `.input` height | `30` | `30` |
| `.input` padding | `4px 11px` | `4px 11px` |
| `body` fontSize | `14px` | `14px` |
| `body` lineHeight | `21px` | `21px` |
| `.topbar__title h1` fontSize | `16px` | `16px` |
| `.topbar__title h1` fontFamily | `Syne, Inter, "Helvetica Neue", Arial, sans-serif` | `Syne, Inter, "Helvetica Neue", Arial, sans-serif` |
| `.label` fontSize | `10.5px` | `10.5px` |
| `.label` letterSpacing | `1.47px` | `1.47px` |
| `.lib-card` width × height / radius ([capture](evidence/i1/dark-1440-library.png)) | `274.00 × 613.19px / 14px` | Additional themed matrix/state details in JSON |
| `.range` width × height / radius ([capture](evidence/i1/dark-1440-new-adjustments.png)) | `330.00 × 20.00px / 6px` | Additional themed matrix/state details in JSON |
| `.modal` width × height / radius ([capture](evidence/i1/dark-1440-library-history.png)) | `820.00 × 235.00px / 14px` | Additional themed matrix/state details in JSON |
| `.toast` width × height / radius ([capture](evidence/i1/dark-1440-new-extracted-toast.png)) | `380.00 × 68.25px / 10px` | Additional themed matrix/state details in JSON |

Primary button above is the actual 44px large extraction action. Base/small buttons are 36/30px in source and visible toolbars; do not infer all buttons are 44px. Inputs use 30px controls; textarea uses its own 14px text/1.6 line-height. Viewer frames, cards and compare assume 4:5; flexible dimensions are still required for WitnessTrace. Hierarchy is visible in topbar h1 (Syne 16px), dashboard hero h2 (responsive uppercase), panel titles (Syne 13.5px) and mono 10.5px labels. The first `.panel` on NewSketch is its header, so its padding is not a universal panel-body padding; standard heads/bodies use separate classes.

### Responsive layout measurements

| Width × height | Studio columns (dark) | Sidebar physical width / behavior | Topbar height | Page horizontal overflow |
|---|---|---|---|---|
| 1920 × 1080 | `340px 892px 360px` | `248px`, fixed visible | `60px` | none in eight-surface matrix |
| 1440 × 900 | `340px 412px 360px` | `248px`, fixed visible | `60px` | none in eight-surface matrix |
| 1280 × 800 | `330px 638px` | `248px`, fixed visible | `60px` | none in eight-surface matrix |
| 768 × 1024 | `720px` | `264px`, off-canvas drawer; root layout width 0 | `60px` | settings |
| 390 × 844 | `362px` | `264px`, off-canvas drawer; root layout width 0 | `60px` | settings |

The light matrix has the same responsive structure. At ≤1360 the side panel moves below the center; ≤1280 stats/providers/settings use two columns; ≤1080 sidebar becomes a 264px drawer and studio/workspace/compare become one column; ≤760 stats/settings/sliders/split narrow further; ≤420 case chip hides. Landing uses min-width 640/860/1024/1200 and max-width 639/720 overrides; auth collapses at ≤860. These source breakpoints are preserved. At 390 library cards stack and controls are reached by normal vertical scrolling; long topbar titles ellipsize. Width resizing is not a real-device touch test.

## Browser interaction results

The final run passes **131 checks**: 80 explicit active-theme checks and 51 API/interaction checks. Full exact names/results are in browser-results.json. The evidence verifier also confirms 116 screenshot hashes, all eight × five × two captures, 69 unchanged frontend/config/asset files, no missing image assets and stopped owned services.

| Classification | Behaviors verified |
|---|---|
| Fully working with original reference backend | Real registration API; browser login + rejection; local trait extraction via Ctrl+Enter; genuine procedural preview; guided answer application; multi-witness comparison/application; refinement Interpret/Apply; save new sketch; real synthetic second revision; library search/history; PNG/JSON/HTML export responses and SHA-256 |
| Frontend-only working | Tabs; sidebar navigation/aria-current; mobile drawer open/navigation-close; landing mobile menu/Escape; actual theme toggle/reload persistence; slider keyboard/undo/redo; viewer zoom/Fit; compare keyboard/drag/version pickers/split; modal focus containment/Shift+Tab/Escape/cancel; reduced-motion preference; notifications open and Escape action |
| Backend-dependent working in isolated reference | Health recheck; provider/status display; live landing procedural demo; loading/boot; controlled 503 workspace offline message |
| Deliberate placeholder | Pricing Join Waitlist/Team plan: notice dialog explicitly says planned/demo and no backend collection; it is not a subscription or working waitlist |
| Pre-existing visual defects | Settings overflow, landing headline clipping, long sidebar-label clipping and legacy theme color inconsistencies described below |
| Not verified | Paid hosted/local-model generation, actual speech recognition, real mobile touch/keyboard, accessibility compliance, full destructive delete/delete-all execution, library rename/status interactions, exhaustive conflict/mark editing, registration form successful submission, live Codex/WitnessTrace generation |

No request acceptance was called AI completion. The reference API synchronously saved actual procedural images, and every UI caption remains procedural/not AI. Export checks exercised real bytes and recorded hashes; not every download anchor was clicked through the browser download UI.

### Error/asset observations

- **Zero JavaScript page exceptions/unhandled page errors.** No failed requests, no broken images or 404 assets in the final run.
- There are **47 browser console resource errors**: 45 expected 401 responses from anonymous auth/me probes and the deliberate invalid login, plus two 503s from the controlled health outage. They are documented, not hidden as “zero console errors.” There were no other console error messages. StrictMode duplicates some probes.
- The loading screenshot delays the real health response without changing its result. The offline screenshot deliberately returns an identified 503 for health in the test harness; it is not an observed real backend outage. Both controls are recorded explicitly in metadata and do not edit production behavior. The notifications capture was taken after removing interception but before explicitly retrying/reloading the App; it still shows the deliberately induced offline state. Notification opening was observed there; actual outage recovery was not tested.

## Known defects and handoff deviations

| ID | Finding / evidence | Impact / future action |
|---|---|---|
| UI-01 | Settings scrollWidth **812px at viewport 768** and **518px at 390**, in both themes; light mobile sidebar capture inherits Settings overflow. `*-768-settings.png`, `*-390-settings.png` | Horizontal scrolling/clipped provider content. Handoff reported 829 at 768 and no issue at 390; this environment disproves the latter. Dynamic paths/fonts/provider content differ. Fix intrinsic-minimum/grid/preformatted content wrapping later. |
| UI-02 | Landing title clips at its right edge: especially “description” / “composites” at 390 and parts of longest lines at larger sizes. `dark-390-landing.png`, `light-390-landing.png`, 1920 landing | Hidden overflow can conceal text while document scrollWidth still equals viewport. Source unchanged; do not equate no horizontal scrolling with no clipping. Later responsive typography/line layout fix required. |
| UI-03 | Long INVESTIGATION WORKSPACE sidebar label clips at 248px. `dark/light-1440-workspace.png` | Confirmed handoff defect; retain shell design while adjusting label sizing/space later. |
| UI-04 | Four theme-token layers, hard-coded viewer well/cyan compare accent; light status colors remain dark-palette brights | Confirmed by computed colors and screenshot contrast. Consolidation/accessibility fixes belong to later phases; no flattening in I1. |
| UI-05 | Settings privacy text says “No account is required” while App actually enforces cookie login | Existing stale copy, source and screenshot confirmed. Update truthfully during integration. |
| UI-06 | `ApiError.isOffline` only recognizes status 0; HTTP proxy 502/503/504 do not trigger AuthPage offline wording | Source-confirmed handoff issue. Workspace controlled-503 offline handling works; auth proxy scenario not separately re-exercised in I1. |
| UI-07 | Sidebar source does not provide a modal focus trap/inert closed links or Escape handler, unlike the landing menu/modal | Keyboard accessibility risk from source; full drawer focus-order/accessibility audit not performed. Open/navigation-close tested; do not claim accessible modal semantics. |
| UI-08 | Light-theme Compare captions, capability band, final CTA and footer retain dark backgrounds with low-contrast dark text. `light-1440-compare.png`, `light-1440-landing-footer.png` and light full-page capture | Visually confirmed inherited theme inconsistency; readable theme-specific foregrounds/surfaces need later correction. No measured WCAG contrast claim. |

Handoff confirmed: actual stack, shell dimensions, three-column 1440 studio, display fonts, final dark/light palette, variable breakpoint behavior, procedural data flow and cookie authentication. Context corrected: current main already committed the handoff and landing light-palette block; stale handoff “uncommitted” status is not current. The temporary macOS handoff captures were not reused as new evidence. `IntroLoader`/Wordmark/original src/images files remain dead/unreferenced source assets; no removals were made.

## Validation and next gate

`npm run lint` PASS; `npm run build` PASS (70 modules; Vite 8.0.0). Logs: [lint.txt](evidence/i1/lint.txt), [build.txt](evidence/i1/build.txt), [verification.txt](evidence/i1/verification.txt). No React unit/component test script exists in package.json; the isolated Chromium harness is the new frontend interaction check. Existing backend suites were not modified or replaced, and no new backend test claim is made in I1.

Dependency audit and owner Git-history gates remain open in [I1_DEPENDENCY_SECURITY.md](I1_DEPENDENCY_SECURITY.md). They do not block preservation documentation, but they must be resolved before final deployment/shared merge as specified. No private data was staged; no merge or push occurred. I2 — Backend Preservation — **NOT STARTED**. Await explicit NEXT.
