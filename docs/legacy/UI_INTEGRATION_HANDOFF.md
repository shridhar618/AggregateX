# UI Integration Handoff: Revelio → WitnessTrace AI

> **Purpose.** This is a read-only reverse-engineering record of the **Revelio** frontend. Another engineering agent should be able to reproduce its look and interaction quality inside **WitnessTrace AI** while keeping WitnessTrace's backend, persistence, Codex CLI generation pipeline and all of its existing features.
>
> **This document is not enough on its own.** A faithful transfer also needs the source CSS files and brand assets listed in §14 and §20. Read the document alongside those files.

### Evidence labels used throughout

| Label | Meaning |
|---|---|
| **[SRC]** | Verified by reading the source file cited. |
| **[BROWSER]** | Verified in a running instance with headless Chromium (Brave) over the DevTools protocol, on isolated test data. |
| **[INFERRED]** | Reasoned from the source but not exercised end-to-end. |
| **[NOT VERIFIED]** | Not tested. |
| **[MISSING]** | Information not available to this inspection, such as WitnessTrace's code. |

**Inspection date:** 2026-10-28. **Inspector:** Claude Code (Opus 5.5), working read-only. The only file created in the project is this document. Temporary artifacts (screenshots, API samples, test data) were written outside the repository; see §13.

---

## 1. Executive summary

- **What Revelio is [SRC].**
  - A **React 19.2.4 + Vite 8.0.0** single-page frontend written in **plain JavaScript (JSX, no TypeScript)**.
  - It is styled with **hand-written plain CSS**. There is no Tailwind, no CSS-in-JS and no component library.
  - It talks to a local **FastAPI** backend (`backend/app`) on `127.0.0.1:8000`, reached through a Vite proxy at `/api`.
  - It has three entry surfaces in one build:
    - a marketing **landing page** (`/`);
    - **login and registration** pages (`/login`, `/register`);
    - a hash-routed **workspace** (`/app#/…`) with five screens: Workspace overview, New Sketch studio, Library, Compare and Settings.
- **Its visual identity [SRC][BROWSER].**
  - A dark "forensic workstation" look: charcoal `#090909` with coral `#ef5539`.
  - A light theme in cream `#faf6e9` with sage `#527642` / `#a0c878`.
  - Type is **Syne** (display), **Inter** (UI text) and **IBM Plex Mono** (data and labels).
  - A fixed 248 px sidebar, a sticky 60 px top bar, panels with 14 px radius, and a three-column "studio" for the main editor.
- **What it does functionally [SRC][BROWSER].**
  - Text → deterministic trait extraction → an editable 20-trait profile with 16 proportion sliders → a **procedural SVG/PNG composite rendered by the backend**.
  - Refinement by natural-language command, which proposes changes; nothing applies until the operator confirms.
  - Multi-witness merge, saved immutable revisions, before/after compare, a library, and exports (PNG, JSON, printable HTML report).
  - Optional hosted Gemini generation; it was off and untested in this inspection.
- **Fit with WitnessTrace [INFERRED].**
  - WitnessTrace is described as **vanilla HTML/CSS/JS** served by FastAPI, with many features Revelio's UI does not have: Sketchpad, Enhance, Multi-view, cases, a 45-attribute Character Lab, PDF/SHA-256 reports, and async Codex CLI generation.
  - Revelio's React components are tightly bound to **its own** data model: the `Profile` schema, `RV-` sketch IDs and synchronous generate calls.
  - **Recommendation: port the design system and the visual shell into WitnessTrace's existing vanilla frontend (a CSS-first port).** Re-implement a small set of self-contained widgets in vanilla JS, such as the compare slider, modal, toasts, viewer toolbar, pipeline and theme toggle.
  - **Do not** transplant React or Revelio's backend. See §16 and §22.
- **Readiness [INFERRED].**
  - The design system, layout and interaction patterns are fully documented and verified (52 of 53 browser checks passed; the one failure is a real source bug, described in §8).
  - The feature mapping is **partial**, because WitnessTrace's code was not supplied **[MISSING]**. Its endpoints, payloads and current markup must be inventoried in phase M0 before integration.

---

## 2. Source project identity and environment

| Item | Value | Evidence |
|---|---|---|
| Product name | Revelio. It was previously "VeriSketch AI" and originally "ShareLock"; the folder name still reflects the original. | [SRC] `package.json`, `README.md` |
| Project root | `/Users/shridharbhat/Downloads/ShareLock-main 2` (macOS) | [SRC] |
| Git branch / HEAD | `main` @ `d3bc788308092082ead684ed3e0aa211ec6413be` ("Fix theme toggle overlapping the stacked landing nav") | [SRC] `git rev-parse` |
| Remotes | `origin`, `hackfest`. URLs intentionally omitted. | [SRC] |
| Working tree | **One uncommitted change:** `src/landing/landing.css`, which adds the light-theme colours for the landing live demo and editor showcase (block appended at the end of the file). This document describes the tree **including** that change. | [SRC] `git status` |
| Node / npm | v22.19.0 / 10.9.3 | [SRC] |
| Python | 3.13.7 (venv at `backend/.venv`) | [SRC] |
| Package manager | npm (`package-lock.json`, lockfileVersion 3) | [SRC] |
| Build tool | Vite 8.0.0 + `@vitejs/plugin-react` 6.0.1 | [SRC] |
| Module type | ESM (`"type": "module"`) | [SRC] |
| Dev ports | Vite on `127.0.0.1:5173`, preview on `127.0.0.1:4173`, API on `127.0.0.1:8000` (override with `REVELIO_API_PORT`) | [SRC] `vite.config.js`, `scripts/run-api.mjs` |

> **Port note for WitnessTrace.** WitnessTrace runs on **8001**, and another app uses **8000**. Revelio's defaults (5173, 8000) collide with that environment. **Do not run Revelio's dev servers on the WitnessTrace machine with default ports.** Use `REVELIO_API_PORT` and `vite --port` if Revelio must run there for reference.

### Commands [SRC] `package.json`

| Script | Command | Purpose |
|---|---|---|
| `npm run dev` | `node scripts/dev-all.mjs` | Starts the API (via `run-api.mjs`) and Vite together |
| `npm run dev:web` | `vite` | Frontend only |
| `npm run dev:api` | `node scripts/run-api.mjs` | `uvicorn app.main:app --host 127.0.0.1 --port 8000` using `backend/.venv` |
| `npm run build` | `vite build` | Production bundle into `dist/` |
| `npm run preview` | `vite preview` | Serves `dist/` with the same `/api` proxy |
| `npm run lint` | `eslint .` | ESLint 9 flat config |
| `npm run test:api` | `node scripts/run-api.mjs --test` | `pytest -q` in `backend/` |

### Verification run during this inspection

- **Lint:** `eslint .` is clean. **[BROWSER-adjacent: CLI]**
- **Backend tests:** `pytest`, **76 passed**. **[SRC]**
- **Build:** `vite build` succeeded. It was built into a temporary directory, so `dist/` was not touched.
  - Largest chunk: `index-*.js` at 193.4 kB (61.3 kB gzip), which is mostly React and ReactDOM.
  - `NewSketch` is 53.7 kB.
  - `LandingPage` is 57.6 kB.
  - CSS: `landing-*.css` about 66 kB, `App-*.css` about 49 kB, `index-*.css` about 18 kB.

### Environment variables

Names only. **No values are recorded.** [SRC] `.env.example`, `backend/.env.example`, `backend/app/config.py`, `vite.config.js`

| Variable | Read by | Purpose |
|---|---|---|
| `VITE_API_BASE` | frontend (`src/api/client.js`) | API base path. Default `/api`. **The only frontend env var.** |
| `REVELIO_API_URL` | `vite.config.js` (Node) | Proxy target for `/api`. Default `http://127.0.0.1:8000`. |
| `REVELIO_API_PORT` | `scripts/run-api.mjs` | Port uvicorn binds |
| `REVELIO_DATA_DIR`, `REVELIO_CORS_ORIGINS`, `REVELIO_HOSTED_PROVIDER`, `REVELIO_HOSTED_TIMEOUT`, `REVELIO_LOCAL_MODEL_PATH`, `REVELIO_MAX_UPLOAD_MB` | backend | Backend config. Each falls back to `VERISKETCH_*`. |
| `GEMINI_API_KEY`, `GEMINI_IMAGE_MODEL` | backend only | Optional hosted provider. **Never in the frontend.** |

No real `.env` file exists in the repository; only the `.env.example` files are present.

---

## 3. Repository and project structure

Only UI-relevant files are shown. Line counts are approximate (`wc -l`). [SRC]

```
index.html                         HTML shell: Google Fonts link, favicon, #root, /src/main.jsx
vite.config.js                     React plugin; /api proxy → REVELIO_API_URL (default 127.0.0.1:8000)
eslint.config.js                   ESLint flat config (react-hooks, react-refresh)
public/
  favicon.png, apple-touch-icon.png   Owl mark on a dark tile (64², 180²)
  landing/demo-r1.webp, demo-r2.webp  Pre-rendered procedural composites for the landing hero (900×1125)
src/
  main.jsx            (47)   Path switch: / → LandingPage, /login|/register → AuthPage, /app → App.
                             Theme init; legacy localStorage migration; old /#/x → /app#/x redirect
  index.css           (986)  GLOBAL design system: tokens (:root), reset, buttons, inputs, range,
                             segmented, chips, tags, alerts, skeleton, keyframes, scrollbars, reduced
                             motion, and 4 stacked palette layers (see §6)
  App.jsx             (160)  Workspace shell: auth gate (GET /auth/me), boot sequence, hash routing,
                             Sidebar/Topbar/footer, lazy pages, engine-offline screen
  api/client.js       (97)   fetch wrapper + `api` object (every endpoint the UI calls) + ApiError
  state/AppContext.jsx(101)  Global context: catalog, health/providers, toasts, notifications,
                             activeCase, prefs (localStorage), user, logout
  lib/
    router.js         (24)   Hash router: useRoute(), navigate(path, params)
    nav.js            (8)    NAV items (id, label, short, icon)
    format.js         (81)   humanize, optionLabel, formatDateTime, relativeTime, markLabel,
                             profileSummary, emptyProfile, downloadBlob, safeStorage
    theme.js          (26)   'revelio.theme' storage, applyTheme, initializeTheme
    auth.js           (9)    safeNext (open-redirect guard), loginUrl
  styles/app.css      (3641) Workspace styles: shell, sidebar, topbar, boot, toasts, modals, hero,
                             stats, cards, studio grid, viewer, traits, adjust, refine, merge,
                             revisions, library, compare, settings, responsive @media
  components/
    brand/Logo.jsx           LogoMark (owl <img>), BrandLogo (wordmark <img>), Wordmark (unused)
    shell/BootScreen.jsx     Startup checklist overlay
    shell/Sidebar.jsx        Fixed nav + system status card (off-canvas ≤1080px)
    shell/Topbar.jsx         Title, case chip, engine dot, clock, theme toggle, notifications, account menu
    shell/Toasts.jsx         Toast stack (aria-live)
    ui/Icon.jsx              ~60 inline SVG icons (stroke, 24×24 viewBox)
    ui/Modal.jsx             Modal (focus trap, Esc, scroll lock) + ConfirmModal (type-to-confirm)
    ui/EmptyState.jsx        Icon + title + text + action
    ui/ThemeToggle.jsx       Sun/moon button → applyTheme
    ui/CaseClock.jsx         Live local date/time
    ui/DictateButton.jsx     Web Speech API dictation into a text field
    sketch/DescriptionPanel.jsx  Tabs: free text (extract) · Guided questions · Witnesses (merge)
    sketch/TraitPanel.jsx        Profile editor with provenance tags, conflicts, evidence, marks
    sketch/AdjustPanel.jsx       Feature selects + 16 proportion sliders
    sketch/RefinePanel.jsx       NL refinement → proposed changes → apply
    sketch/WitnessMerge.jsx      2–4 accounts → shared/conflict/single-source → resolve → apply
    sketch/ModeSelector.jsx      Provider radio cards (offline/local/hosted)
    sketch/ReferenceUpload.jsx   Optional reference image (data URL) for hosted mode
    sketch/SketchViewer.jsx      Preview surface: zoom, fit, before/after, PNG, meta strip
    sketch/CompareSlider.jsx/.css  Drag/keyboard reveal slider (shared with landing)
    sketch/Pipeline.jsx          5-step status strip
    sketch/RenderNotes.jsx       Renderer honesty notes
  pages/
    Workspace.jsx     (200)  Overview dashboard
    NewSketch.jsx     (493)  Studio: the main editor (state owner for profile/history/preview/save)
    Library.jsx       (188)  Sketch cards, search, rename, status, history modal, delete, exports
    Compare.jsx       (173)  Version A/B pickers, slider/split, trait diff table
    Settings.jsx      (150)  Providers, privacy, interface prefs, delete-all
  auth/AuthPage.jsx, auth.css  Login/register (reuses landing.css tokens)
  landing/                     Marketing page (lp- prefixed CSS); see §5
    landing.css       (3911)   Landing styles + palette layers (also some workspace overrides; see §18)
  assets/brand/logo-mark.png, logo-wordmark.png   Brand images bundled by Vite
  images/*.png                 Original supplied logo files (NOT referenced by code)
backend/app/…                  FastAPI service. Do NOT transfer (see §14, Category D).
docs/screenshots/*.png         12 committed README screenshots
scripts/render-landing-assets.py  Regenerates public/landing/*.webp using the backend renderer
```

---

## 4. Technology stack and exact dependencies

### Runtime dependencies (installed versions from `package-lock.json`) [SRC]

| Package | Declared | Installed | Role |
|---|---|---|---|
| react | ^19.2.4 | 19.2.4 | UI |
| react-dom | ^19.2.4 | 19.2.4 | DOM renderer (`createRoot`) |

### Dev dependencies [SRC]

| Package | Installed |
|---|---|
| vite | 8.0.0 |
| @vitejs/plugin-react | 6.0.1 |
| eslint / @eslint/js | 9.39.4 / 9.39.4 |
| eslint-plugin-react-hooks | 7.0.1 |
| eslint-plugin-react-refresh | 0.5.2 |
| globals | 17.4.0 |
| @types/react / @types/react-dom | 19.2.14 / 19.2.3 (editor typings only; no TS compilation) |

### What is **not** used [SRC]

There is no router library, state library (Redux, Zustand), form library, CSS framework (Tailwind, Bootstrap), component kit, icon package, animation library (Framer Motion, GSAP), canvas or editor library (Fabric, Konva) or image-processing library in the frontend. Each of these is hand-written:

- **Routing:** a hash router (`src/lib/router.js`) and a pathname switch (`src/main.jsx`).
- **State:** React context plus `useState` / `useReducer`.
- **Icons:** inline SVG paths in `src/components/ui/Icon.jsx`.
- **Animation:** CSS keyframes and transitions, `IntersectionObserver` (`src/landing/motion.jsx`), and one `<canvas>` 2D effect (`src/landing/Hero.jsx`).
- **Auth:** an HttpOnly session cookie set by the backend. The frontend only calls `/api/auth/*`.

### Fonts [SRC] `index.html`

- **Loaded from Google Fonts:** `Inter` (400, 500, 600, 700), `IBM Plex Mono` (400, 500, 600) and `Syne` (400–800), with `display=swap`.
- **Referenced but not loaded:** `Manrope` and `Iowan Old Style` / `Palatino` appear in **overridden** token layers and are never effective (see §6.2).

### Backend (context only; not for transfer) [SRC] `backend/requirements.txt`

fastapi 0.135.1, starlette 1.10.0, uvicorn 0.38.0, pydantic 2.12.1, pillow 12.0.0, pytest 8.4.2 and httpx 0.28.1 (tests).

---

## 5. All screens and routes

### 5.0 Routing model [SRC] `src/main.jsx`, `src/lib/router.js`, `src/App.jsx`

- **Pathname switch** at boot, chosen once per page load:
  - `/` loads `LandingPage`.
  - `/login` and `/register` load `AuthPage mode`.
  - `/app` and `/app/*` load `App`.
  - Each is a separate lazy chunk.
- **Inside `/app`:** a **hash router** of the form `#/<path>?k=v`, with paths `workspace` (default), `new`, `library`, `compare` and `settings`. Any unknown path renders `workspace`.
  - `navigate(path, params)` sets `location.hash`.
  - `useRoute()` listens to `hashchange`.
- **Legacy redirect:** `/#/library` is rewritten to `/app#/library` with `location.replace`.
- **Auth gate (`App`):**
  - `GET /api/auth/me` returns **401** → `location.replace('/login?next=<path+hash>')`.
  - Any other failure (network error, 5xx) → the shell renders and shows its "engine offline" state.
  - `safeNext` only allows `next` values that start with `/app`.
- **Mid-session 401:** any API call under `/app` that returns 401 (other than `/auth/*` calls) redirects to login via `client.js`.
- **Page titles:** `document.title` is set per surface. Inside `/app`, the visible page title comes from `TITLES` in `App.jsx`.

Screenshot filenames below refer to §13. Unless stated, every screen was **[BROWSER]** verified at 1440×900 in the dark theme.

---

### 5.1 Landing page

| Field | Detail |
|---|---|
| Route | `/` |
| Purpose | Marketing page with **live** demos running on the real backend |
| Screenshots | `landing-hero-dark`, `landing-hero-light`, `landing-platform`, `landing-demo-generated`, `landing-features`, `landing-how`, `landing-editor-compare`, `landing-privacy`, `landing-pricing`, `landing-pricing-modal`, `landing-faq`, `vp-390-landing-menu`, `landing-demo-offline`; committed `docs/screenshots/landing*.png` |
| Layout | Fixed nav (`.lp-nav`, z 100). On ≥1024px the section links form a **vertical stack at the top right**, with the theme toggle to their left. Below that, full-width sections inside `.lp-shell` (max-width 88rem, about 1408px). |
| Sections, in order (`LandingPage.jsx`) | `Hero` (`#platform`) → `Statement` → `Band` → `LiveDemo` (`#demo`) → `Features` (`#features`) → `Workflow` (`#how`) → `EditorShowcase` (`#editor`) → `Privacy` (`#privacy`) → `Capabilities` → `Pricing` (`#pricing`) → `Faq` (`#faq`) → `FinalCta` → `Footer` |
| Source | `src/landing/LandingPage.jsx`, `Hero.jsx`, `Sections.jsx`, `LiveDemo.jsx`, `EditorShowcase.jsx`, `Trust.jsx`, `Pricing.jsx`, `Closing.jsx`, `LandingNav.jsx`, `engine.jsx`, `motion.jsx`, `constants.js` |
| Styles | `src/landing/landing.css`, plus `src/index.css` (global) and `src/components/sketch/CompareSlider.css` |
| Reusable pieces | `Reveal`, `SplitLines`, `SplitWords`, `CountUp`, `useInView`, `useScrollProgress`, `scrollToId` (`motion.jsx`); `EngineProvider` / `useEngine` (`engine.jsx`); `CompareSlider`; `ThemeToggle`; `Icon`; `LogoMark` / `BrandLogo` |
| State | `EngineProvider`: `{status: checking/online/offline, health, catalog, error}`. LiveDemo: description, profile, extraction, phase, renders count, preview state (blob URL). EditorShowcase: profile, current blob, in-page revisions, compare flag. Nav: menu open, scrolled, active section (IntersectionObserver). Pricing: notice modal. |
| Interactions | Nav link → smooth scroll. Hero canvas "liquid reveal" on pointer-capable devices only (`canHover() && !prefersReducedMotion()`). Live demo: Generate → `POST /traits/extract` then `POST /render` → blob SVG; selects and sliders re-render through the debounced, abortable `/render`; **Download PNG** → `POST /render.png`. Editor showcase: sliders, hairline and facial-hair segments, Save revision (in memory), Before/after (`CompareSlider`), Reset. Pricing "proposal" buttons → `PlanNotice` modal (collects nothing). FAQ uses native `<details>`. Mobile menu is a full-screen dialog with focus trap and Esc. |
| API calls | `GET /health`, `GET /catalog`, `POST /traits/extract`, `POST /render`, `POST /render.png`. **No login needed.** |
| Validation | Description length checked client-side (`limits` from catalog) and server-side (10–2000 chars) |
| Loading | Skeleton blocks (`.lp-skel`), spinner, "rendering" pill, scan-line overlay during render |
| Empty | "Ready when you are" panel with a grid background |
| Error / offline | "The local engine isn't running … `npm run dev` … Retry" **[BROWSER]** (`landing-demo-offline`); inline `.lp-error` |
| Mobile | `<1024px`: link stack hidden, ☰ opens the full-screen `.lp-menu`. `<640px`: the "Open Workspace" button and "Log in" link are hidden from the bar (both stay available in the menu). **[BROWSER]** no horizontal overflow at 390/768/1280/1440. |
| Accessibility | Skip link (`.lp-skip`), `aria-current` on the active section link, `aria-labelledby` on sections, menu `role=dialog aria-modal`, `inert` when closed, reduced-motion support (`prefers-reduced-motion` + `@media`) |
| Notes | `IntroLoader.jsx` exists but **is not mounted anywhere** **[SRC][BROWSER]**, so the README's "skippable intro" is stale. The `Wordmark` export in `Logo.jsx` is unused. `REPO_URL` in `constants.js` is linked from the footer. |
| Migration | Optional for WitnessTrace. It is a marketing surface. Its **demo panels are good visual references** for a text-input + preview + controls layout. |

### 5.2 Login / Register

| Field | Detail |
|---|---|
| Routes | `/login`, `/register`; query `?next=/app…` |
| Purpose | Local accounts (an HttpOnly cookie session) |
| Screenshots | `auth-login-dark/light`, `auth-register-dark/light`, `auth-register-errors`, `auth-login-error`, `auth-offline` |
| Layout | Top bar (owl + theme toggle). A two-column grid: a decorative composite frame with tagline on the left, and a 440px form card on the right. A single column at ≤860px. |
| Source / styles | `src/auth/AuthPage.jsx`; `src/auth/auth.css` + `src/landing/landing.css` (tokens, `lp-btn`, `lp-label`, `lp-eyebrow`) |
| State | `form {name,email,password,confirm}`, `errors`, `serverError`, `busy`, `show` (password visibility), `engine` (checking/online/offline) |
| Interactions | Submit → client validation (email regex, password 8–128, confirm match) → `api.register` / `api.login` → `location.assign(next)`. Show/hide password. Switch link keeps `next`. If already logged in → redirect to `next`. |
| API | `GET /auth/me`, `POST /auth/register`, `POST /auth/login` |
| Errors | Inline per-field `.lp-error` with focus on the first invalid field; a server error box (`role=alert`) **[BROWSER]** |
| **Known defect** | When the API is down **behind the Vite proxy**, the proxy answers **502**. The client only treats a thrown `fetch` (status 0) as offline, so **the "engine isn't running" notice is not shown** and a submit shows "Request failed (502)". **[BROWSER]** `auth-offline` |
| Migration | Only relevant if WitnessTrace adds accounts. Otherwise skip. |

### 5.3 Boot screen (workspace startup)

- **Where:** `/app`, as an overlay (`.boot`, z 500) **[BROWSER]** `app-boot`.
- **Source:** `components/shell/BootScreen.jsx`. It shows four real checks (interface, engine, catalog, providers) with ok / error / skipped icons and a minimum display time of 900 ms (`MIN_BOOT_MS`). It fades out with a `leaving` class after 420 ms.
- **API:** `GET /health`, `GET /catalog`.
- **Migration:** it maps well to WitnessTrace startup checks (FastAPI health, Codex CLI availability, DB). This is **Category B**.

### 5.4 Engine-offline screen

- **What:** `EngineOffline` in `App.jsx`. A centred panel with a CPU icon, the copy "Local engine not reachable", a `pre.code` block of commands and a "Retry connection" button **[BROWSER]** `app-engine-offline`.
- **When it shows:** after boot, if `health` or `catalog` is missing.
- **Migration:** Category B. Replace the command text with WitnessTrace's own start instructions.

### 5.5 Workspace overview

| Field | Detail |
|---|---|
| Route | `/app#/workspace` (default) |
| Purpose | Dashboard: hero, stats, recent sketches, unfinished work, activity, providers |
| Screenshots | `app-workspace-dark`, `app-workspace-light`, `vp-*-workspace`; committed `docs/screenshots/workspace*.png` |
| Layout | `.hero.panel.panel--corners` (two columns: text plus a visual of the owl reticle with rings and the 01–04 flow list) → `.stats` (four stat cards) → `.workspace__grid` (1.6fr / min 300px). The left column holds "Recent sketches" (`.recent`, a card grid with `auto-fill minmax(170px,1fr)`). The right `.workspace__side` holds Unfinished work, Recent activity (`.timeline`) and Generation providers (`.provider-mini`). |
| Source | `src/pages/Workspace.jsx` |
| API | `GET /stats`, `GET /sketches`, `GET /activity?limit=12` (run in parallel with `Promise.all`) |
| State | `data {stats, sketches, activity}`, `error`, `draft` (from `localStorage['revelio.draft']`) |
| Loading / empty / error | Skeleton per block; `EmptyState` "No sketches saved yet" with a CTA; `.alert--error` |
| Interactions | "Create new sketch" → `navigate('new', {fresh})`; "Resume unsaved draft"; cards → `#/new?sketch=ID`; "Open library"; "Details" → settings |
| Mobile | ≤1080px: single column and the hero visual hidden. ≤760px: stats in one column. ≤1280px: stats in two columns. |
| Migration | **High value** as the WitnessTrace dashboard: cases instead of sketches, Codex job status instead of providers (Category B). |

### 5.6 New Sketch studio (main editor)

| Field | Detail |
|---|---|
| Route | `/app#/new`, `#/new?sketch=RV-…&rev=N`, `#/new?fresh=<token>` (forces a blank editor) |
| Purpose | Describe → extract → edit → live preview → save immutable revisions → compare and export |
| Screenshots | `app-new-empty`, `app-new-extracted`, `app-new-editor-tab`, `app-new-refine`, `app-new-guided`, `app-new-witnesses`, `app-viewer-zoomed`, `app-viewer-compare`, `app-new-light`, `vp-*-new`; committed `docs/screenshots/new-sketch*.png` |
| Layout | Optional restore banner → `.studio__head.panel` (editable title input, ID chip, `Pipeline`, undo/redo/reset/new) → `.studio__grid` with three areas, `input | center | side`, at `minmax(280px,340px) minmax(0,1fr) minmax(300px,360px)`, gap 16. **Input column:** `DescriptionPanel` (tabs Description/Guided/Witnesses), extraction alerts, `ModeSelector`, `ReferenceUpload`. **Center:** `SketchViewer`, the `.generate` panel (revision note + save buttons + progress + errors), the `.revisions` list (thumbnail buttons) and `RenderNotes`. **Side** (sticky, `top: topbar+16px`, `max-height: 100vh-92px`): tabs Profile (`TraitPanel`) / Editor (`AdjustPanel`) / Refine (`RefinePanel`). |
| Measured [BROWSER] | At 1440: columns `340px 412px 360px`; viewer stage 410×594; side panel 360×808. At 1280: `330px 638px` (side panel drops below the centre). At 768: a single 720px column. At 390: a single 362px column. |
| Source | `src/pages/NewSketch.jsx` plus the `components/sketch/*` listed in §3 |
| State owner | `NewSketch`; see §9 |
| API | `GET /sketches/{id}`, `POST /render` (debounced 140 ms, aborts previous), `POST /traits/extract`, `POST /refine/parse`, `POST /refine/apply`, `POST /witnesses/merge`, `POST /sketches/generate`, `POST /sketches/{id}/revisions`, `PATCH /sketches/{id}` (rename on blur), `POST /render.png` (unsaved download), `GET …/image.png?download=true` (saved download), and the revision thumbnails `GET …/image.png` |
| Validation | Description min/max from the catalog; extract button disabled when empty or too long; refine needs ≥3 chars; merge needs ≥2 non-empty accounts; reference image PNG/JPEG/WebP ≤5 MB (client) |
| Loading | Pipeline "active" state; viewer "Rendering…" pill and optional scan-line (pref `scanEffect`); save button spinner plus indeterminate progress bar with a live elapsed timer (`Elapsed`, 250 ms tick) |
| Empty | `EmptyState` "No profile yet" in the viewer |
| Errors | Viewer `.alert--error` (render); `.generate__error` with "Use the offline composite instead" for provider failures; field errors; toasts |
| Keyboard | ⌘/Ctrl+Enter = extract (in the textarea); ⌘/Ctrl+Z = undo; ⇧⌘/Ctrl+Z = redo (ignored while focus is in an input, textarea or select); arrow keys on the compare handle; Enter blurs the title input |
| Mobile | ≤1360px: side panel moves under the centre column. ≤1080px: a single column. ≤760px: pipeline text hidden and viewer height auto. |
| Migration | **Core reference** for WitnessTrace's text workspace + preview + Character Lab + refinement. Most components are **Category B** (they are bound to the `Profile` schema). |

### 5.7 Sketch Library

| Field | Detail |
|---|---|
| Route | `/app#/library` |
| Screenshots | `app-library`, `app-library-light`, `app-library-empty-search`, `app-library-history`, `app-library-delete-confirm`, `vp-*-library` |
| Layout | `.toolbar.panel` (search input with icon, record count, "New sketch") → `.library__grid` (`auto-fill minmax(240px,1fr)`, gap 16) of `.lib-card.panel` (4:5 thumbnail with tag, title + rename, ID + draft/final chip, rev count + relative time, method label, Open/History/Compare, Export row PNG/JSON/Report + delete) |
| Source | `src/pages/Library.jsx` (includes `HistoryModal`) |
| API | `GET /sketches?q=` (debounced 220 ms), `PATCH /sketches/{id}` (title, status), `DELETE /sketches/{id}`, `GET /sketches/{id}` (history), export links `…/image.png?download=true`, `…/export.json?download=true`, `…/report` (new tab) |
| Interactions [BROWSER] | Search filters; status chip toggles Draft↔Final; History modal opens and closes on Esc; delete opens `ConfirmModal`; export hrefs point to backend routes |
| Migration | Maps to **case / revision browsing**; Category B |

### 5.8 Compare

| Field | Detail |
|---|---|
| Route | `/app#/compare`, `?sketch=ID` |
| Screenshots | `app-compare-slider`, `app-compare-split`, `app-compare-light`, `vp-*-compare` |
| Layout | `.toolbar.panel` with two `Picker`s (sketch select + revision select), an arrow and a segmented "Drag reveal / Side by side" → `.compare-page__grid` (1.2fr / min 320px): stage panel (`CompareSlider` or `.split` figures, a `.compare-meta` with two columns, a disclaimer) + "Trait profiles" panel (`table.diff`, changed rows highlighted, "Changed or known only" toggle, a count chip) |
| Default | Version A = the previous revision and B = the current revision of the same sketch |
| API | `GET /sketches`, `GET /sketches/{id}` (cached per id) |
| Migration | Maps directly to WitnessTrace **before/after and version comparison**; Category B (the data source differs) |

### 5.9 Settings

| Field | Detail |
|---|---|
| Route | `/app#/settings` |
| Screenshots | `app-settings`, `app-settings-light`, `app-settings-delete-all`, `vp-*-settings` |
| Layout | Providers panel (three `.provider` cards in a three-column grid: tags, status chip, reason, data-leaves-device line, an env snippet for hosted, detection list for local) + `.settings__grid` (three columns): Data & privacy (bullets + `dl.kv` data dir/engine), Interface (two `.switch` toggles: scan-line effect, reduce motion), Delete local data (danger zone → `ConfirmModal` with `requireText="DELETE"`) |
| API | `GET /storage`, `GET /health` (re-check), `POST /data/delete-all {confirm:"DELETE"}` |
| **Known defect** | At **768px** the provider cards overflow by **61px horizontally** (page scrollWidth 829 vs viewport 768). There is no overflow at ≥900px or at 390px. **[BROWSER]** |
| Migration | Category B; WitnessTrace would show Codex CLI auth status and storage info here |

### 5.10 Shell overlays (all `/app` screens)

| Element | Source | Behaviour [BROWSER] |
|---|---|---|
| Sidebar | `shell/Sidebar.jsx` | Fixed 248px, z 60. Brand wordmark (44px), NAV with numeric keys 01–05, active item = coral 12% fill + 2px inset left bar. System status card (engine dot pulse, provider rows). Privacy note. **≤1080px:** off-canvas (264px wide, `translateX(-100%)`), scrim z 55, opened by the topbar ☰ (`vp-390-sidebar-open`). **Cosmetic defect:** at 248px the active label "INVESTIGATION WORKSPACE" is clipped to "…WORKSPAC" (visible in all 1440 screenshots). |
| Topbar | `shell/Topbar.jsx` | Sticky, height 60, z 40. Eyebrow + uppercase Syne title, case chip (`NONE ACTIVE` / `UNSAVED DRAFT` / `RV-… R2`), LOCAL/OFFLINE dot, `CaseClock`, theme toggle, notifications (badge count ≤9; dropdown; Esc / outside click closes), account avatar (initials) → name, email and **Log out** |
| Toasts | `shell/Toasts.jsx` | Bottom stack (z 400). At most 4 visible (`slice(-3)` + new). Auto-dismiss after 4200 ms by default. `role=alert` for errors, otherwise `status`. Also logged to notifications (30 max). |
| Modals | `ui/Modal.jsx` | Scrim z 350; focus trap; Esc; outside-mousedown closes; body scroll lock (`body.is-locked`); focus restored on close |
| Footer | `App.jsx` | `REVELIO · v1.0` + disclaimer |

---

## 6. Complete visual design system

### 6.0 How the theme is assembled

This must be understood before copying any values. [SRC]

- **Theme switch:** `html[data-theme="dark"|"light"]`. It is set by `initializeTheme()` from `localStorage['revelio.theme']`, defaults to `dark`, and is toggled by `ThemeToggle` → `applyTheme()`. There is **no** `prefers-color-scheme` auto-detection.
- **Workspace tokens** are CSS custom properties on `:root` in `src/index.css`. They are defined in **four stacked layers**, and later layers override earlier ones:
  1. Base "cyber" palette (`:root`, lines ~5–58) plus its light variant (lines ~60–83).
  2. "Editorial gold" layer (lines ~822–830, plus the light variant ~832–854).
  3. Final **light** layer: `:root[data-theme='light']` (lines ~879–902), cream and sage.
  4. Final **dark** layer: `:root:not([data-theme='light'])` (lines ~935–961), charcoal and coral.
- **Landing and auth tokens** are scoped to `.lp` in `src/landing/landing.css`. That file has the same layering (base `.lp` at lines ~6–49, gold ~3005, light ~3114, dark override blocks further down).
- **Variable names are historical.** `--cyan` is the **primary accent** (coral or sage), not cyan, and `--blue` is a secondary neutral. Rename them during the port (for example to `--accent`); see §18.
- **Effective values** below were read with `getComputedStyle` in the running app **[BROWSER]**. When porting, copy the **effective** values into **one** flat token file instead of reproducing the four layers.

### 6.1 Colour tokens: workspace (`:root`, effective) [BROWSER]

| Token (source name) | Role | Dark | Light |
|---|---|---|---|
| `--bg` | Page background | `#090909` | `#faf6e9` |
| `--bg-2` | Secondary background / inputs | `#111111` | `#f5f1e2` |
| `--panel` | Card / panel surface | `#171717` | `#fffdf6` |
| `--panel-2` | Raised surface | `#202020` | `#fffdf6` |
| `--panel-3` | Track / tertiary surface | `#2b2b2b` | `#edf2d9` |
| `--border` | Hairline border | `#393632` | `#d5e1b9` |
| `--border-strong` | Emphasised border | `#5b554e` | `#a0c878` |
| `--text` | Primary text | `#eee8dc` | `#273323` |
| `--text-2` | Secondary text | `#c2b9aa` | `#56634c` |
| `--text-3` | Muted / labels | `#8a8379` | `#747e69` |
| `--cyan` | **Primary accent** | `#ef5539` (coral) | `#527642` (sage) |
| `--blue` | Secondary accent | `#b7a992` | `#64854e` |
| `--amber` | Warning / AI tag | `#ef5539` | `#ffb547` ⚠ legacy |
| `--red` | Error | `#ff5d6c` | `#ff5d6c` ⚠ legacy |
| `--green` | Success | `#8fa38b` | `#38d996` ⚠ legacy |
| `--cyan-soft` | Accent fill | `rgba(239,85,57,.13)` | `rgba(160,200,120,.2)` |
| `--cyan-line` | Accent border | `rgba(239,85,57,.5)` | `rgba(160,200,120,.82)` |
| `--blue-soft` | Secondary fill | `rgba(183,169,146,.12)` | `rgba(160,200,120,.16)` |
| `--amber-soft` | Warning fill | `rgba(239,85,57,.13)` | `rgba(160,200,120,.18)` |
| `--red-soft` | Error fill | `rgba(239,85,57,.13)` | `rgba(174,63,68,.09)` |
| `--green-soft` | Success fill | `rgba(143,163,139,.12)` | `rgba(160,200,120,.2)` |
| `--shadow` | Panel shadow | `0 1px 0 rgba(255,255,255,.025) inset, 0 12px 32px rgba(0,0,0,.28)` | `0 1px 0 rgba(255,255,255,.9) inset, 0 10px 28px rgba(70,91,48,.08)` |
| `--shadow-lg` | Popovers / modals | `0 1px 0 rgba(255,255,255,.035) inset, 0 24px 64px rgba(0,0,0,.42)` | `0 1px 0 rgba(255,255,255,.94) inset, 0 22px 52px rgba(70,91,48,.13)` |
| `--focus` | Focus ring (box-shadow) | `0 0 0 2px #090909, 0 0 0 4px #ef5539` | `0 0 0 2px #faf6e9, 0 0 0 4px #527642` |

⚠ **Light theme never overrides `--amber`, `--red` and `--green`**, so they keep the original dark-palette brights. Status colours on cream may lack contrast. Treat this as a defect to fix during the port. [BROWSER]

**Body background [SRC] `index.css`.**

- **Dark:** `#090909` plus a radial coral glow (`rgba(239,85,57,.045)`) plus a 32px grid of `rgba(238,232,220,.018)` lines.
- **Light:** `#faf6e9` plus sage and lime radial glows plus a 32px grid of `rgba(160,200,120,.12)` lines.
- `background-attachment: fixed` in both themes.

**Other measured surfaces [BROWSER].**

- **Sidebar and topbar:** dark `rgb(13,13,13)`. Light: the sidebar uses a `linear-gradient(rgba(221,235,157,.32), rgba(250,246,233,.98))` and the topbar `rgba(250,246,233,.9)`.
- **Light-theme panels** use `linear-gradient(#fffdf6, #f5f1e2)` with a `1px #a0c878` border.
- **Viewer stage:** a dark well, `rgb(6,9,14)` plus a cyan radial, kept in both themes (legacy value).

**Button colours [BROWSER].**

| Variant | Dark | Light |
|---|---|---|
| `.btn--primary` | bg `#ef5539`, text `#140b08`, hover `#ff674b`, no shadow | `linear-gradient(180deg,#a0c878,#93bc6b)`, text `#24311e`, hover `linear-gradient(#add184,#a0c878)` |
| `.btn` / `.btn--ghost` | transparent, text `--text-2`, 1px transparent border | same tokens |

### 6.2 Colour tokens: landing and auth (`.lp`, effective) [BROWSER]

| Token | Dark | Light |
|---|---|---|
| `--bg` / `--bg-2` | `#090909` / `#111111` | `#faf6e9` / `#f5f1e2` |
| `--surface` / `--surface-2` | `#171717` / `#202020` | `#fffdf6` / `#f3f5e7` |
| `--border` / `--border-2` | `#393632` / `#5b554e` | `#d5e1b9` / `#a0c878` |
| `--text` / `--text-2` / `--text-3` | `#eee8dc` / `#c2b9aa` / `#8a8379` | `#273323` / `#56634c` / `#747e69` |
| `--cyan` (accent) | `#ef5539` | `#527642` |
| `--blue` / `--violet` | `#b7a992` / `#8d8272` | `#64854e` / `#7d9863` |
| `--ok` / `--warn` | `#42dea0` / `#ef5539` | `#42dea0` / `#ffbd59` |
| `--cyan-soft` / `--cyan-line` | `rgba(239,85,57,.13)` / `.5` | `rgba(160,200,120,.2)` / `.82` |
| `--grad` | `linear-gradient(120deg,#eee8dc 0%,#ef5539 100%)` | `linear-gradient(120deg,#a0c878 0%,#7fa95b 56%,#527642 100%)` |

**Light live demo and editor showcase** (the uncommitted block at the end of `landing.css`) [SRC]:

- **Panel:** `linear-gradient(160deg,#fffdf6,#f5f3e6)` plus sage and gold radial glows, border `#d5e1b9`, shadow `0 40px 90px -52px rgba(82,118,66,.55)`.
- **Cards:** `rgba(255,254,250,.88)` with a 3px top rule `linear-gradient(90deg,#a0c878,#7fa95b 55%,#ddb55f)`.
- **Chips:** `rgba(160,200,120,.22)`.
- **Editor viewer:** a sage 28px grid over `linear-gradient(160deg,#f3f5e7,#e9eed9)`.

### 6.3 Typography

**Font families [SRC][BROWSER].**

| Token | Family stack | Effective |
|---|---|---|
| `--font` | `'Inter', ui-sans-serif, system-ui, -apple-system, 'Segoe UI', Roboto, sans-serif` | Inter |
| `--display` | `'Syne', 'Inter', 'Helvetica Neue', Arial, sans-serif` (final layer; the earlier `Manrope` and `Iowan Old Style` layers are overridden) | Syne |
| `--mono` | `'IBM Plex Mono', ui-monospace, 'SF Mono', Menlo, Consolas, monospace` | IBM Plex Mono |

**Licensing:** Inter, IBM Plex Mono and Syne are all **SIL Open Font License 1.1**, so they are free to self-host or embed. [INFERRED from public licensing; confirm in M0.] Loading is from `fonts.googleapis.com` with `display=swap`; offline, the stack falls back to system fonts.

**Measured type scale, workspace [BROWSER].**

| Element (selector) | Family | Size / line-height | Weight | Tracking | Case |
|---|---|---|---|---|---|
| Body (`body`) | Inter | 14px / 21px (1.5) | 400 | normal | none (feature settings `'cv11','ss01'`) |
| Page title (`.topbar__title h1`) | Syne | 16px / 18.4px | 600 | 0.24px | UPPERCASE |
| Eyebrow (`.topbar__title .label`) | Plex Mono | 9.5px / 14.25px | 500 | 1.33px | UPPERCASE |
| Label (`.label`) | Plex Mono | 10.5px / 15.75px | 500 | 1.47px | UPPERCASE |
| Section title (`.section-title`) | Syne | 13.5px | 600 | −0.07px | none (preceded by a ◇ accent glyph via `::before`) |
| Hero title (`.hero__title`) | Syne | 44px / 43.1px (`clamp(28px,3.1vw,44px)` in light) | 800 | −2.86px | UPPERCASE, gradient text (`background-clip:text`) |
| Stat value (`.stat__value`) | Plex Mono | 30px / 45px | 500 | −0.6px | none, zero-padded (`'02'`) |
| Nav item (`.nav-item`) | Syne | 11px / 16.5px | 700 | 0.88px | UPPERCASE |
| Buttons (`.btn`, `.btn--sm`, `.btn--lg`) | Inter | 13 / 12.5 / 14px | 500 / 500 / 600 | normal | none |
| Inputs (`.input`, `.select`) / textarea | Inter | 12.5px / 14px (lh 1.6) | 400 | — | — |
| Tags (`.tag`) | Plex Mono | 10px | 500 | 0.8px | UPPERCASE |
| Chips (`.chip`) | Inter | 12px | 500 | — | — |
| Footer (`.app__foot`) | Inter | 12px | 400 | — | — |

**Measured type scale, landing at 1440px [BROWSER].**

| Element | Value |
|---|---|
| `.lp` base | Inter 16px / 1.55 |
| `.lp-hero__title` | Syne 103.7px / 87.1px, 800, −5.7px, UPPERCASE |
| `.lp-h2` | Syne 57.6px / 58.8px, 800, −3.17px |
| `.lp-eyebrow` | Inter 12.8px, 700, 4.86px tracking, UPPERCASE |
| `.lp-section__lead` | Inter 16.8px / 26px |
| `.lp-nav__links a` | Syne 14.4px, 700, UPPERCASE |
| `.lp-label` | Plex Mono 10.9px, 500, 1.52px, UPPERCASE |
| `.lp-btn--ghost` (lg) | 15.7px, 52px tall |

Landing sizes use `clamp()` and are responsive.

### 6.4 Layout and spacing [SRC][BROWSER]

| Item | Value |
|---|---|
| Sidebar | `--sidebar-w: 248px`, `position:fixed`, padding 16px 12px, gap 18px. ≤1080px: `--sidebar-w:0`, drawer width 264px. |
| Topbar | `--topbar-h: 60px`, `position:sticky; top:0`, padding 0 24px (≤760px: 0 12px), gap 16px |
| Main column | `.app__main { margin-left: var(--sidebar-w) }` |
| Content container | `.content { max-width: 1680px; margin: 0 auto; padding: 22px 24px 40px }` (≤760px: 14px 14px 32px; measured 28px top in workspace) |
| Panel | radius 14px (`--r-lg`), 1px border, `--shadow`; `.panel__head` padding 14px 16px; `.panel--corners` adds 12px accent corner brackets (`::before`/`::after`, `--cyan-line`) |
| Workspace grid | `.stats` 4 columns (≤1280px: 2, ≤760px: 1), gap 14. `.workspace__grid` `minmax(0,1.6fr) minmax(300px,1fr)`, gap 18. `.recent` `repeat(auto-fill,minmax(170px,1fr))`, gap 14. |
| Studio grid | `minmax(280px,340px) minmax(0,1fr) minmax(300px,360px)`, gap 16; areas `input center side` (≤1360px: `'input center' 'input side'`; ≤1080px: one column) |
| Side panel | sticky `top: calc(var(--topbar-h) + 16px)`; `max-height: calc(100vh - var(--topbar-h) - 32px)`; body scrolls (`.studio__sidebody`, max 640px ≤1360, 70vh ≤1080) |
| Viewer stage | `height: clamp(420px, 66vh, 760px)`; frame `aspect-ratio: 4/5`; ≤760px: `height:auto; min-height:360px` |
| Image proportions | Composites are **4:5** (renderer output 900×1125 PNG, SVG viewBox 600×750). Cards, viewer, compare and thumbnails all assume 4:5. |
| Library grid | `repeat(auto-fill, minmax(240px,1fr))`, gap 16 |
| Compare grid | `minmax(0,1.2fr) minmax(320px,1fr)`, gap 16 |
| Settings grid | three columns (≤1280px: two; ≤760px: one) |
| Landing shell | `.lp-shell` max-width 88rem, padding-inline 1.25rem (2rem measured at 1440) |
| Auth layout | `minmax(0,1fr) minmax(0,440px)`, gap `clamp(2rem,6vw,5rem)`, max-width 1200px |

**Z-index hierarchy [SRC].**

| Context | Element | z-index |
|---|---|---|
| Workspace | `.topbar` | 40 |
| Workspace | `.account__panel` | 40 |
| Workspace | `.sidebar-scrim` | 55 |
| Workspace | `.sidebar` | 60 |
| Workspace | `.skip-link` | 300 |
| Workspace | `.modal-scrim` | 350 |
| Workspace | `.toasts` | 400 |
| Workspace | `.boot` | 500 |
| Landing | `.lp-nav` | 100 |
| Landing | mobile `.lp-menu` | 150 |
| Landing | `.lp-skip` | 200 |
| Landing | `.lp-modal` | 250 |
| Landing | `.lp-intro` (unused) | 300 |

**Scrolling:** `html { scroll-behavior: smooth }`. Custom thin scrollbars (`::-webkit-scrollbar`). The body is locked while a modal is open (`body.is-locked`) or the landing menu is open (`html.lp-locked`).

### 6.5 Other tokens [SRC][BROWSER]

| Category | Values |
|---|---|
| Radii | `--r-xs` 4px (tags) · `--r-sm` 6px (sm buttons, inputs, selects, case chip) · `--r-md` 10px (buttons, textarea, cards, mode cards) · `--r-lg` 14px (panels) · `--r-xl` 18px · pills 999px (chips, avatar). Landing: `--r-pill` 9999px · `--r-card` 1.75rem · `--r-card-sm` 1.125rem · `--r-ctl` 0.75rem |
| Borders | 1px everywhere; dashed for unknown tags and the demo separator; active nav = `box-shadow: inset 2px 0 0 var(--cyan)`; active tab = `inset 0 -2px 0 var(--cyan)` |
| Buttons | `.btn` min-height **36px**, padding 0 14px, gap 8px · `.btn--sm` **30px** / 0 10px · `.btn--lg` **44px** / 0 20px · `.btn--icon` square · landing `.lp-btn--lg` 52px |
| Inputs | `.input`/`.select` **30px** (sm), padding 4px 11px (select 30px right for the chevron data-URI) · textarea padding 8px 11px, lh 1.6 · landing `.lp-input` 46px (2.9rem) |
| Slider (`.range`) | 20px hit area; 4px track; fill = `linear-gradient(90deg, var(--cyan) 0 var(--fill), var(--panel-3) var(--fill) 100%)` driven by an inline `--fill` % style; thumb styled per engine |
| Switch | track 36×20, radius 20, knob 14 |
| Chip / tag heights | 24px / 20px |
| Icons | SVG 24×24 viewBox, stroke 1.6, `currentColor`; default `.icon { width:16px; height:16px }` (`index.css`); landing empty-state icons 2rem |
| Backdrop / blur | landing nav `blur(16px) saturate(1.3)` when scrolled; `.lp-traits` blur 14px |
| Transitions | `--t-fast` 140ms · `--t` 240ms · `--t-slow` 480ms; easing `--ease` `cubic-bezier(.2,.8,.2,1)`, `--ease-in-out` `cubic-bezier(.65,0,.35,1)`; landing `--ease-out` `cubic-bezier(.22,1,.36,1)` |
| Keyframes (`index.css`) | `shimmer` (skeleton), `dotPulse`, `fadeUp`, `fadeIn`, `scaleIn` (popovers), `spin`, `scanSweep` (viewer scan line), `chipIn`, `workspaceEnter` (440ms staggered panels), `softGlow`; `.reveal` and `.stagger > *` helpers |
| Reduced motion | `@media (prefers-reduced-motion: reduce)` plus the user pref `html.reduce-motion` (Settings) disable animations |
| Breakpoints (workspace, max-width) | **1360**, **1280**, **1080** (sidebar becomes a drawer, one column), **760** (mobile), **420**; one `min-width:1081px` |
| Breakpoints (landing) | min-width **640**, **860**, **1024** (stacked nav), **1200**; max-width **639**, **720**; `(hover:hover) and (pointer:fine)` gates hover effects |
| Breakpoints (auth) | max-width **860** |

### 6.6 Design-token transfer table (use this as the port's single source)

| New token (suggested) | Dark | Light | Source of truth |
|---|---|---|---|
| `--wt-bg` | #090909 | #faf6e9 | `index.css` final layers |
| `--wt-bg-2` | #111111 | #f5f1e2 | ″ |
| `--wt-surface` | #171717 | #fffdf6 | ″ |
| `--wt-surface-2` | #202020 | #fffdf6 | ″ |
| `--wt-surface-3` | #2b2b2b | #edf2d9 | ″ |
| `--wt-border` | #393632 | #d5e1b9 | ″ |
| `--wt-border-strong` | #5b554e | #a0c878 | ″ |
| `--wt-text` | #eee8dc | #273323 | ″ |
| `--wt-text-2` | #c2b9aa | #56634c | ″ |
| `--wt-text-3` | #8a8379 | #747e69 | ″ |
| `--wt-accent` | #ef5539 | #527642 | `--cyan` |
| `--wt-accent-fill` | #ef5539 | #a0c878 | primary button bg |
| `--wt-accent-soft` | rgba(239,85,57,.13) | rgba(160,200,120,.2) | `--cyan-soft` |
| `--wt-accent-line` | rgba(239,85,57,.5) | rgba(160,200,120,.82) | `--cyan-line` |
| `--wt-on-accent` | #140b08 | #24311e | primary button text |
| `--wt-danger` | #ff5d6c | *define (≈#b3261e)* | `--red` (light undefined) |
| `--wt-warn` | #ef5539 | *define (≈#9a6b12)* | `--amber` (light legacy) |
| `--wt-ok` | #8fa38b | *define (≈#3f6b34)* | `--green` (light legacy) |
| `--wt-font` / `--wt-display` / `--wt-mono` | Inter / Syne / IBM Plex Mono | same | `index.css` |
| radii, motion, layout | see §6.4–6.5 | same | `index.css` |

Values marked *define* are **[INFERRED] suggestions**, because the source leaves those light-theme roles unset.

---

## 7. Reusable component inventory

**Reusability legend:**
- **Direct:** the CSS and markup pattern can be copied as-is.
- **Adapt:** keep the visuals, rewire the data and events.
- **Reimpl:** rebuild in vanilla JS from this spec.

All components are React function components in plain JSX **[SRC]**.

### 7.1 Shell and UI primitives

| Component | Source path | Props (public contract) | State | Styles (classes) | Events / data | Complexity | Reuse |
|---|---|---|---|---|---|---|---|
| `Icon` | `src/components/ui/Icon.jsx` | `{name, className='icon', title, size, strokeWidth=1.6}` | — | `.icon` | ~60 names in `P` map (workspace, newSketch, library, compare, settings, menu, close, plus, minus, check, arrowRight/Left, chevronDown/Right, undo, redo, reset, save, download, upload, trash, edit, search, zoomIn/Out, fit, scan, layers, sparkle, cpu, cloud, shield, alert, info, error, ok, bell, clock, file, json, printer, image, users, text, list, sliders, wand, eye, eyeOff, lock, database, history, copy, external, dot, more, sun, moon, mic, micOff, user, logout) | Low | **Direct.** Copy the path data into a vanilla `icon(name)` helper. |
| `LogoMark` / `BrandLogo` | `src/components/brand/Logo.jsx` | `LogoMark{size=32, animated}`; `BrandLogo{height=32, animated, className}`; ratio 554/170 | — | `.logo-mark`, `.brand-logo` | `<img>` of brand PNGs | Low | **Do not transfer the brand.** Keep the slot. |
| `Sidebar` | `src/components/shell/Sidebar.jsx` | `{current, open, onNavigate, onClose}` | reads `health, providers, engineError` | `.sidebar`, `.sidebar__brand`, `.nav-item(.is-active)`, `.nav-item__key`, `.status-card`, `.sidebar-scrim(.is-open)`, `.sidebar__note` | anchors `#/<id>` from `NAV` | Low | **Reimpl** (simple markup) |
| `Topbar` (+`AccountMenu`, `useDismiss`) | `src/components/shell/Topbar.jsx` | `{title, eyebrow, onMenu}` | open flags | `.topbar`, `.topbar__title`, `.case-chip(.is-active)`, `.topbar__engine`, `.clock`, `.notif*`, `.account*` | Esc and outside-click dismiss | Low | **Reimpl** |
| `BootScreen` | `src/components/shell/BootScreen.jsx` | `{steps:{ui,engine,catalog,providers: 'pending'|'ok'|'error'|'skipped'}, leaving}` | — | `.boot*` | — | Low | **Adapt** (different checks) |
| `Toasts` + `notify()` | `src/components/shell/Toasts.jsx`, `src/state/AppContext.jsx` | `notify({kind:'ok'|'info'|'warn'|'error', title, message, timeout=4200})` | toasts (max 4), notifications (max 30) | `.toasts`, `.toast.is-<kind>`, `.toast__body` | dismiss button | Low | **Reimpl** (~40 lines vanilla) |
| `Modal`, `ConfirmModal` | `src/components/ui/Modal.jsx` | `Modal{title, children, onClose, footer, wide, labelledBy}`; `ConfirmModal{title, message, confirmLabel, danger, requireText, onConfirm, onClose, busy}` | typed text | `.modal-scrim`, `.modal(--wide)`, `.modal__body/__foot/__message` | focus trap, Esc, scroll lock, restore focus | Low | **Reimpl** |
| `EmptyState` | `src/components/ui/EmptyState.jsx` | `{icon='scan', title, children, action, compact}` | — | `.empty(--compact)` | — | Low | **Direct** markup |
| `ThemeToggle` | `src/components/ui/ThemeToggle.jsx`, `src/lib/theme.js` | `{className}` | theme | `.theme-toggle`, `.lp-theme-toggle` | sets `html[data-theme]`, stores the theme in `localStorage` | Low | **Reimpl** (change the storage key) |
| `CaseClock` | `src/components/ui/CaseClock.jsx` | — | `now` (1 s interval) | `.clock`, `.clock__date` | — | Low | **Direct** |
| `DictateButton` | `src/components/ui/DictateButton.jsx` | `{value, onChange, maxLength, label='Dictate', lang}` | listening, interim | `.dictate*` | Web Speech API (`continuous`, `interimResults`); hidden if unsupported; Brave/Electron → warning toast | Medium | **Optional, Adapt** |
| `Pipeline` | `src/components/sketch/Pipeline.jsx` | `{steps:[{id,label,state:'done'|'active'|'pending'|'warn',detail}]}` | — | `.pipeline`, `.pipeline__step.is-<state>`, `__node/__text/__label/__detail` | — | Low | **Direct.** Good fit for Codex job steps. |
| `CompareSlider` | `src/components/sketch/CompareSlider.jsx` + `.css` | `{before, after, beforeLabel, afterLabel}` (image URLs) | `pos` 0–100 | `.compare`, `.compare__img`, `.compare__before` (clip-path inset), `.compare__tag--l/r`, `.compare__handle` | pointer capture drag; ←/→ step 5; `role=slider` + aria-value* | Low | **Reimpl** (~50 lines vanilla), copy the CSS directly |
| `SketchViewer` | `src/components/sketch/SketchViewer.jsx` | `{src, kind:'ai'|'procedural', label, sublabel, loading, error, before:{src,label}, onDownload, downloadBusy, meta:[[k,v]], empty}` | `zoom` ∈ [0.5,0.75,1,1.25,1.5,2,3], `comparing` | `.viewer.panel.panel--corners`, `__bar/__label/__tools/__zoom/__sep/__stage(.is-zoomed)/__frame/__img/__scan/__busy/__error/__corner/__meta/__empty/__compare` | toolbar buttons; uses the `prefs.scanEffect` context | Medium | **Adapt / Reimpl.** The primary preview for WitnessTrace. |
| `RenderNotes` | `src/components/sketch/RenderNotes.jsx` | `{notes:[{trait,kind,message}]}` | — | `.notes*` | — | Low | **Adapt** (provenance or caveat list) |

### 7.2 Domain components (bound to Revelio's `Profile` model)

| Component | Source path | Props | State | Backend calls | Complexity | Reuse |
|---|---|---|---|---|---|---|
| `DescriptionPanel` (+`GuidedForm`) | `src/components/sketch/DescriptionPanel.jsx` | `{description, onDescriptionChange, onExtracted, onGuided, onMerged}` | tab, busy, error; Guided: answers, marks, observations | `POST /traits/extract` | High | **Adapt.** The visual is a good text-input workspace; the extraction semantics are Revelio-specific. |
| `WitnessMerge` | `src/components/sketch/WitnessMerge.jsx` | `{onApply({profile, description})}` | texts (2–4), result, decisions, filter | `POST /witnesses/merge` | High | **Optional enhancement** (WitnessTrace has no merge) |
| `TraitPanel` (+`TraitRow`, `SourceTag`) | `src/components/sketch/TraitPanel.jsx` | `{profile, onChange(next, key)}` | showUnknown | — | High | **Adapt** to 45 attributes and 7 groups; provenance tags map to "sourced clarifications" and "uncertainty annotations" |
| `AdjustPanel` | `src/components/sketch/AdjustPanel.jsx` | `{profile, onChange, aiNotice}` | — | — | Medium | **Adapt** to the Character Lab sliders and selectors |
| `RefinePanel` | `src/components/sketch/RefinePanel.jsx` | `{profile, onApply(next, changes)}` | text, proposal, selected, busy, error | `POST /refine/parse`, `POST /refine/apply` | High | **Adapt.** Keep the input, example chips and confirm-before-apply pattern; WitnessTrace refinement generates a new image revision. |
| `ModeSelector` | `src/components/sketch/ModeSelector.jsx` | `{mode, onChange}` | — | uses providers from `/health` | Low | **Adapt** (Codex CLI status / options) |
| `ReferenceUpload` | `src/components/sketch/ReferenceUpload.jsx` | `{value:{dataUrl,name,size}, onChange, supported, providerLabel}` | error | none (sent inside generate) | Low | **Adapt** to WitnessTrace Enhance uploads (multipart is likely preferable) |

### 7.3 Pages and landing (composition only)

| Component | Source path | Notes |
|---|---|---|
| `Workspace` | `src/pages/Workspace.jsx` | Dashboard composition (§5.5); **Adapt** |
| `NewSketch` | `src/pages/NewSketch.jsx` | State owner (§9); **Adapt.** Do not copy the logic verbatim. |
| `Library` (+`HistoryModal`) | `src/pages/Library.jsx` | Card grid, inline rename, status chip, exports; **Adapt** |
| `Compare` (+`Picker`) | `src/pages/Compare.jsx` | A/B pickers, segmented view, diff table; **Adapt** |
| `Settings` | `src/pages/Settings.jsx` | Provider cards, switches, danger zone; **Adapt** |
| `AuthPage` (+`Field`) | `src/auth/AuthPage.jsx` | Only if accounts are wanted |
| Landing set | `src/landing/*.jsx` | Marketing; optional. `motion.jsx` helpers (`Reveal`, `SplitLines`, `useInView`) are a reusable pattern. |

### 7.4 Verified code excerpts (copied from source) [SRC]

**API wrapper and its error contract** (`src/api/client.js`):

```js
async function request(path, { method = 'GET', body, signal, raw = false } = {}) {
  let res
  try {
    res = await fetch(`${BASE}${path}`, {
      method,
      signal,
      headers: body !== undefined ? { 'Content-Type': 'application/json' } : undefined,
      body: body !== undefined ? JSON.stringify(body) : undefined,
    })
  } catch (err) {
    if (err?.name === 'AbortError') throw err
    throw new ApiError(0, 'The local Revelio engine is not reachable. Start it with “npm run dev:api”.')
  }
  if (!res.ok) {
    // Session expired or logged out elsewhere: send the workspace back to the login page.
    if (res.status === 401 && !path.startsWith('/auth/') && window.location.pathname.startsWith('/app')) {
      window.location.assign(loginUrl())
    }
    let data = {}
    try {
      data = await res.json()
    } catch {
      /* non-JSON error body */
    }
    const detail = typeof data.detail === 'string' ? data.detail : `Request failed (${res.status})`
    throw new ApiError(res.status, detail, data)
  }
  if (raw) return res
  if (res.status === 204) return null
  return res.json()
}
```

**Hash router** (`src/lib/router.js`):

```js
const parse = () => {
  const raw = window.location.hash.replace(/^#\/?/, '')
  const [path, query = ''] = raw.split('?')
  return { path: path || 'workspace', params: Object.fromEntries(new URLSearchParams(query)) }
}

export const navigate = (path, params = {}) => {
  const qs = new URLSearchParams(Object.entries(params).filter(([, v]) => v != null && v !== '')).toString()
  const next = `#/${path}${qs ? `?${qs}` : ''}`
  if (window.location.hash !== next) window.location.hash = next
}
```

**Compare slider core** (`src/components/sketch/CompareSlider.jsx`; the full file is about 50 lines):

```jsx
<div ref={ref} className="compare"
  onPointerDown={(e) => { dragging.current = true; e.currentTarget.setPointerCapture(e.pointerId); move(e.clientX) }}
  onPointerMove={(e) => dragging.current && move(e.clientX)}
  onPointerUp={() => { dragging.current = false }}
  onPointerCancel={() => { dragging.current = false }}>
  <img className="compare__img" src={after} alt={afterLabel} draggable={false} />
  <div className="compare__before" style={{ clipPath: `inset(0 ${100 - pos}% 0 0)` }}>
    <img className="compare__img" src={before} alt={beforeLabel} draggable={false} />
  </div>
```

**Theme** (`src/lib/theme.js`):

```js
export const THEME_KEY = 'revelio.theme'
export function applyTheme(theme) {
  const nextTheme = THEMES.includes(theme) ? theme : 'dark'
  document.documentElement.dataset.theme = nextTheme
  try { window.localStorage.setItem(THEME_KEY, nextTheme) } catch { /* … */ }
  return nextTheme
}
```

The `try` body in the last excerpt is condensed from a multi-line block; the logic is unchanged.

---

## 8. User interactions and behaviour

**Classification:**
- **FUNC:** fully functional, backend-backed.
- **FE:** frontend-only.
- **BE:** depends on a specific backend capability.
- **MOCK:** placeholder or no-op by design.
- **UNVER:** not verified.

The "Verified" column records browser results from this inspection (headless Chromium, isolated data). The full run: **53 checks, 52 passed, 0 console errors.**

| Element | Trigger | State change | Backend request | UI response | Error behaviour | Class | Verified |
|---|---|---|---|---|---|---|---|
| Sidebar nav item | click | `location.hash` | — | page swaps, topbar title updates, `aria-current=page` | — | FE | ✅ |
| Theme toggle | click | `html[data-theme]`, `localStorage['revelio.theme']` | — | full re-theme; persists across reload | storage failure → session only | FE | ✅ |
| Example description | click | description text | — | textarea filled | — | FE | ✅ |
| Extract facial traits / ⌘↵ | click, keydown | `profile`, `meta`, tab → Profile | `POST /traits/extract` | toast "N characteristics extracted"; trait rows tagged *Extracted*; conflicts and explicit-unknown alerts | 422 → inline `field__error`; "No traits recognised" warn toast | FUNC | ✅ |
| Live preview | any profile change | `preview{url,notes,loading,error}` | `POST /render` (140 ms debounce, aborts previous) | `<img src=blob:…svg>`; "Rendering…" pill; optional scan line | viewer error alert | FUNC | ✅ |
| Trait select (Profile tab) | change | `profile.traits[k]={value,source:'manual'}` | (render) | tag becomes *Manual* | — | FE | ✅ (indirect) |
| Conflict chip "Use X" | click | resolves `alternatives` | (render) | conflict cleared | — | FE | NOT VERIFIED |
| Add / remove mark | click | `profile.marks` | (render) | mark list | — | FE | NOT VERIFIED |
| Proportion slider | input; dblclick resets | `profile.adjustments[k]` (±1, step .05) | (render) | value label; `.is-changed`; reset icon enabled | — | FE | ✅ |
| Undo / Redo | buttons, ⌘Z / ⇧⌘Z | `historyReducer` (past/future, 80 deep, 900 ms coalescing per key) | (render) | profile restored | disabled at the ends | FE | ✅ |
| Reset | click | profile ← `baseline` | (render) | — | disabled when equal | FE | NOT VERIFIED |
| Draft autosave | 500 ms after a change | `localStorage['revelio.draft']` | — | restore banner on next visit | storage failure silent | FE | ✅ |
| Save composite / Save revision | click | `gen{mode,since}` → `sketch`, `viewingRev` | `POST /sketches/generate` / `POST /sketches/{id}/revisions` | spinner, indeterminate bar + elapsed timer; toast "RV-… · revision N saved"; URL → `#/new?sketch=ID` (`history.replaceState`); revision list grows | `.generate__error`; for hosted, "Use the offline composite instead" | FUNC | ✅ (offline mode) |
| Save disabled when clean | — | `dirty=false` | — | hint "Revision N matches…" | — | FE | ✅ |
| Hosted AI generate | click (mode=hosted) | — | generate with `mode:'hosted'` | AI-labelled raster | 409 when disabled (verified via API), 502 on provider error | BE | **UNVER** (no key; API returned 409 as designed) |
| Title input | blur / Enter | — | `PATCH /sketches/{id}` | toast "Sketch renamed" | error toast | FUNC | NOT VERIFIED (Library rename path similar) |
| Viewer zoom −/+/fit | click | `zoom` | — | frame width `zoom×100%`; label `125%` | disabled at limits / in compare | FE | ✅ |
| Viewer Before / after | click | `comparing` | — | `CompareSlider` with previous revision | disabled without a previous version | FE | ✅ |
| Compare handle | drag, ←/→ | `pos` | — | clip-path reveal; `aria-valuenow` | — | FE | ✅ (keyboard 50→45) |
| Viewer PNG | click | — | saved: `GET …/image.png?download=true`; unsaved: `POST /render.png` → blob download | file download | error toast | FUNC | ✅ (href verified) |
| Revision thumbnail | click | `viewingRev`, profile ← revision | (render) | `.rev.is-active` | — | FE | NOT VERIFIED |
| Refine: Interpret | submit / example chip | `proposal`, `selected` | `POST /refine/parse` | checklist of proposed changes (editable target select) | warn alert "Nothing to change"; "Not understood" note | FUNC | ✅ |
| Refine: Apply N changes | click | profile | `POST /refine/apply` | profile updated; revision note prefilled | field error | FUNC | ✅ |
| Guided: Apply answers | click | traits set `source:'described'` | — | toast "Guided answers applied" | — | FE | ✅ |
| Witnesses: Compare | click | `result`, `decisions` | `POST /witnesses/merge` | counts and filter chips; per-trait rows; conflicts need a decision; **Apply disabled until resolved** | field error | FUNC | ✅ |
| Mode card | click | `mode` | — | radio selection; disabled when unavailable | — | FE | ✅ (render) |
| Reference image | file pick | `{dataUrl,name,size}` | sent within generate (hosted only) | thumbnail + size | type/size error | BE | NOT VERIFIED |
| Dictate | click | listening / interim | browser speech service | text appended | unsupported → hidden; Brave → warning toast | FE / browser | Present ✅; speech NOT VERIFIED |
| Notifications | click / Esc / outside | open | — | list of session toasts | — | FE | ✅ |
| Account → Log out | click | — | `POST /auth/logout` | clears draft → `/login` | logout failure ignored | FUNC | ✅ |
| Library search | input (220 ms debounce) | items | `GET /sketches?q=` | filtered grid / "No sketches match" | alert | FUNC | ✅ |
| Library status chip | click | — | `PATCH {status}` | Draft ↔ Final | error toast | FUNC | ✅ |
| Library rename | ✎ → input blur/Enter, Esc cancels | editing | `PATCH {title}` | toast | error toast | FUNC | NOT VERIFIED |
| Library History | click | historyFor | `GET /sketches/{id}` | modal with per-revision PNG links | modal error | FUNC | ✅ |
| Library delete | 🗑 → confirm | confirm, busy | `DELETE /sketches/{id}` | toast; grid reloads | error toast | FUNC | modal ✅; delete NOT VERIFIED in browser (API route exists, covered by backend tests) |
| Export PNG / JSON / Report | link | — | `GET` download routes; report opens in a new tab | browser download / print page | — | FUNC | hrefs ✅; files ✅ via API |
| Compare pickers / view toggle | change / click | a, b, view | `GET /sketches/{id}` (cached) | slider ↔ split; diff table | alert | FUNC | ✅ |
| Settings switches | click | `prefs.scanEffect`, `prefs.reduceMotion` → `localStorage['revelio.prefs']` | — | `html.reduce-motion` | — | FE | ✅ |
| Settings Re-check | click | health | `GET /health` | spinner | — | FUNC | NOT VERIFIED |
| Delete all local data | type `DELETE` → confirm | — | `POST /data/delete-all` | toast; clears draft | 422 if not confirmed | FUNC | gating ✅; deletion NOT VERIFIED in browser |
| Landing live demo | Generate / controls / Download | local state | extract / render / render.png | blob preview | offline panel | FUNC | ✅ |
| Landing editor showcase | sliders / segments / Save revision / Before/after / Reset | in-memory revisions | `POST /render` | compare slider | offline panel | FUNC (no persistence) | ✅ |
| Landing pricing "proposal" | click | notice | — | modal states that nothing is collected | — | **MOCK** (by design) | ✅ |
| Landing FAQ | click | native `<details>` | — | expands | — | FE | ✅ |
| Landing / workspace mobile menu | ☰ | open | — | drawer / full-screen menu | Esc closes | FE | ✅ |
| Auth forms | submit | form state | register / login | redirect to `next` | inline + server errors | FUNC | ✅ |

**Defects found during the interaction audit [BROWSER]:**

1. **Offline detection behind a proxy.** `client.js` maps only network exceptions to "offline" (status 0). Behind the Vite proxy a dead API returns **502**, so the auth page shows no offline notice (§5.2). The workspace is unaffected because its boot treats any `/health` failure as offline. **Port fix:** treat 502, 503 and 504 as offline in the adapter.
2. **Settings overflows by 61px horizontally at 768px** (§5.9).
3. **The sidebar's active label is clipped** ("INVESTIGATION WORKSPAC") at the 248px sidebar width (§5.10).
4. **`IntroLoader` is dead code** (§5.1).

---

## 9. State management and data flow

### 9.1 Ownership model [SRC]

| Scope | Owner | Contents |
|---|---|---|
| Global (workspace) | `AppProvider` in `src/state/AppContext.jsx`, React context | `catalog`, `health`, `providers` (map by id, derived from health), `engineError`, `toasts[]`, `notifications[]`, `activeCase` (`{id,title,revision}` or `{draft:true}` or `null`, shown in the topbar), `prefs {scanEffect, reduceMotion}`, `user`, `logout()`; plus `refreshHealth()` (also on a 30 s interval) and `loadCatalog()` |
| Global (landing) | `EngineProvider` in `src/landing/engine.jsx` | `{status, health, catalog, error}`, `retry()` |
| Route | URL hash (`useRoute`) | `path`, `params` (`sketch`, `rev`, `fresh`) |
| Editor | `NewSketch` (component-local) | `title`, `description`, `mode`, `hist {past,present,future,key,at}` (the profile undo stack), `baseline`, `meta` (last extraction), `sketch` (server object), `viewingRev`, `preview {url,notes,loading,error}`, `gen`, `genError`, `tab`, `reference`, `changeNote`, `downloadBusy`, `showRestored` |
| Panels | each component | tab, busy, error, proposal and so on (see §7) |
| Persistent browser | `localStorage` | `revelio.theme`, `revelio.prefs`, `revelio.draft` (`{title, description, profile, baseline, mode, sketchId, savedAt}`); one-time migration from `verisketch.*` |
| Session | `sessionStorage` | `revelio.intro.seen` (only used by the unused `IntroLoader`) |
| Auth | HttpOnly cookie `revelio_session` | not readable from JS |

### 9.2 Data flow (New Sketch)

```
        ┌───────────────────────── NewSketch (state owner) ─────────────────────────┐
 text ─▶│ DescriptionPanel ──POST /traits/extract──▶ onExtracted(result) ─┐          │
 guided▶│ GuidedForm ───────────────────────────────▶ onGuided(answers)  ─┤          │
 merge ▶│ WitnessMerge ─POST /witnesses/merge──────▶ onMerged(profile)  ─┤          │
        │ TraitPanel / AdjustPanel ─────────────────▶ onChange(profile,key)─┤ setProfile│
        │ RefinePanel ─POST /refine/parse ▶ confirm ▶ POST /refine/apply ─┘ (history) │
        │                                                                 │          │
        │   profile ──(140 ms debounce, AbortController)──▶ POST /render ──▶ blob:svg │
        │                                                     └─▶ SketchViewer       │
        │   Save ─▶ POST /sketches/generate | /sketches/{id}/revisions ─▶ sketch     │
        │            └─▶ revisions list (thumbnails GET …/image.png) · Compare link  │
        │   autosave (500 ms) ─▶ localStorage['revelio.draft']                      │
        └──────────────────────────────────────────────────────────────────────────┘
```

### 9.3 Object contracts (from the Pydantic schemas and captured responses) [SRC][BROWSER]

```ts
// Shown as TypeScript for clarity. The source is plain JS validated by Pydantic in backend/app/schemas.py.
type Source = 'described' | 'extracted' | 'manual' | 'unknown'
type TraitValue = { value: string | null; source: Source; evidence: string | null /*≤300*/;
                    certainty: 'stated' | 'uncertain'; alternatives: string[] /* non-empty = conflict */ }
type Mark = { id: string; type: 'scar'|'mole'|'birthmark'|'tattoo'|'piercing'|'freckles';
              location: string /* 16 values, e.g. 'left_cheek' */; size: 'small'|'medium'|'large';
              dx: number; dy: number /* −1..1 */; side_specified: boolean; source: Source; evidence?: string }
type Profile = { traits: Record<TraitKey, TraitValue> /* 20 keys */; marks: Mark[] /* ≤20 */;
                 adjustments: Partial<Record<AdjustmentKey, number>> /* 16 keys, −1..1 */; observations: string /* ≤1000 */ }
type RenderNote = { trait: string; kind: 'default' | 'tone' | string; message: string }
type Revision = { number: number; method: 'offline_procedural' | string; method_label: string; model: string;
                  is_ai: boolean; created_at: string /*ISO Z*/; change_note: string | null; notes: RenderNote[];
                  profile: Profile; image_url: string /* '/api/sketches/{id}/revisions/{n}/image.png' */; svg_url: string | null }
type Sketch = { id: string /* /^(RV|VS)-\d{8}-[0-9A-F]{4}$/ */; title: string; description: string;
                status: 'draft' | 'final'; notes: string; created_at: string; updated_at: string;
                revisions: Revision[]; current: Revision | null; revision_count: number }
type SketchListItem = Omit<Sketch,'revisions'|'current'> & { rev_number: number; method: string; method_label: string;
                  is_ai: boolean; revision_count: number; thumbnail_url: string }
type Provider = { id: 'offline'|'local'|'hosted'; label: string; kind: 'procedural'|'ai'; runs_locally: boolean;
                  supports_reference_image: boolean; supports_live_edit: boolean; available: boolean;
                  state: 'ready'|'not_installed'|'disabled'|string; reason: string; data_leaves_device: boolean;
                  model?: string; detected?: Record<string, boolean> }
type Catalog = { traits: {key,label,group,options:string[],rendered:'full'|'recorded'|'tone',note?}[] /*20*/,
                 adjustments: {key,label,group}[] /*16*/, marks: {types,locations,sizes}, sources: Source[],
                 limits: { description_min: 10, description_max: 2000 } }
```

**Value lists [BROWSER].**

- **Trait keys:** `presentation`, `age_range`, `face_shape`, `jawline`, `chin`, `hair_length`, `hair_style`, `hair_color`, `hairline`, `eyebrow_thickness`, `eyebrow_shape`, `eye_shape`, `eye_spacing`, `eye_color`, `eyewear`, `nose_shape`, `mouth_shape`, `facial_hair`, `ears`, `skin_tone`.
- **Groups:** General, Face, Hair, Eyes & brows, Nose & mouth.
- **Adjustment keys:** `face_width`, `face_length`, `jaw_width`, `chin_length`, `ear_size`, `hair_volume`, `eyebrow_thickness`, `eyebrow_height`, `eye_spacing`, `eye_size`, `eye_height`, `nose_width`, `nose_length`, `mouth_width`, `lip_fullness`, `mouth_height`.

### 9.4 Coupling and race-condition notes

- **Preview races are handled.** Each profile change cancels the pending timer and aborts the in-flight `/render` (`AbortController`), and the previous blob URL is revoked when a new one is set and on unmount. [SRC]
- **Save is synchronous by assumption.** `save()` awaits a single `POST` that returns the full `Sketch` with the new revision. A **Codex CLI generation that takes tens of seconds or runs as a background job** needs an adapter that returns a job id and polls (or streams) and resolves to the same shape, or a UI change to job-state rendering. The progress bar is already indeterminate, with a live elapsed timer, which suits long jobs. [INFERRED]
- **`activeCase`** is set from `NewSketch` effects and cleared on unmount. WitnessTrace's "current case" must come from its case selection instead. [SRC]
- **The `dirty` check** uses `JSON.stringify` equality of profiles, so key order matters. The server returns traits in catalog order; mirror that in an adapter or use a deep-equal. [SRC]
- **`history.replaceState`** rewrites the hash after the first save without a `hashchange` event, which deliberately avoids remounting. Keep this if WitnessTrace uses hash routing. [SRC]
- **The 30 s health poll** runs whenever the workspace is open. [SRC]

---

## 10. API contracts and backend dependencies

**Base path:** `BASE = import.meta.env.VITE_API_BASE || '/api'`. Every request is same-origin `fetch` with JSON bodies and the default `credentials: 'same-origin'`; the session cookie rides along automatically.

**Error envelope (all routes):**
- `{ "detail": string }`, sometimes with `errors: string[]` (422) or `provider_error: true, offline_available: true` (409/502 provider errors).
- **401** under `/app` triggers a redirect to `/login`.

Shapes below were captured live **[BROWSER]** (full samples in §13 → `api-samples.json`).

| UI function (`api.*`) | Method and path | Request | Response (2xx) | Auth | Consumers | Loading / retry / polling |
|---|---|---|---|---|---|---|
| `me` | GET `/auth/me` | — | `{user:{id,name,email,created_at}}` | cookie | `App`, `AuthPage` | — |
| `register` | POST `/auth/register` | `{name, email, password}` | 201 `{user}` + Set-Cookie | — | `AuthPage` | 409 duplicate email; 422 validation |
| `login` | POST `/auth/login` | `{email, password}` | `{user}` + Set-Cookie | — | `AuthPage` | 401 wrong credentials; 429 + `Retry-After` after 5 failures |
| `logout` | POST `/auth/logout` | — | 204 | cookie | `AppContext.logout` | errors ignored |
| `health` | GET `/health` | — | `{status, app, version, renderer, providers: Provider[]}` | public | boot, `Sidebar`, `Settings`, landing | 30 s poll in the workspace |
| `catalog` | GET `/catalog` | — | `Catalog` | public | boot, all editors | once |
| `extract` | POST `/traits/extract` | `{description}` (10–2000) | `{profile, conflicts, unknown_traits, explicit_unknowns, uncertain_traits, warnings, recognized_count}` | public | `DescriptionPanel`, landing | 422 `"description: Description must be at least 10 characters."` |
| `merge` | POST `/witnesses/merge` | `{descriptions: string[2..6]}` (UI sends 2–4) | `{witnesses, traits[{key,label,status:'shared'|'conflicting'|'single_source'|'unmentioned',mentions[],combined}], marks, combined_profile, requires_review, counts, disclaimer}` | public | `WitnessMerge` | — |
| `parseRefine` | POST `/refine/parse` | `{instruction (3–500), profile}` | `{changes[{id,kind:'trait'|'adjust'|'mark_add'|'mark_remove',key,label,from,to,from_label,to_label,reason,mark?}], unrecognized[], already[], message}` | public | `RefinePanel` | — |
| `applyRefine` | POST `/refine/apply` | `{profile, changes}` | `{profile}` (changed traits `source:'manual'`, evidence "Operator refinement") | public | `RefinePanel` | — |
| `render` | POST `/render` | `{profile, caption?≤60}` | `{svg, notes, method:'offline_procedural', method_label, is_ai:false}` | public | `NewSketch`, landing | **debounced 140 ms + abort** |
| `renderPng` | POST `/render.png` | same | `image/png` (attachment) | public | download of unsaved preview | — |
| `listSketches` | GET `/sketches?q=` | — | `{sketches: SketchListItem[]}` | **login** | `Workspace`, `Library`, `Compare` | search debounce 220 ms |
| `getSketch` | GET `/sketches/{id}` | — | `Sketch` | **login** | `NewSketch`, `Compare`, `HistoryModal` | 404 `"Sketch not found."` (also for malformed ids) |
| `generate` | POST `/sketches/generate` | `{title, description, profile, mode:'offline'|'local'|'hosted', reference_image?: dataURL ≤8MB, note?}` | 201 `Sketch` | **login** | `NewSketch.save` | 409 provider disabled; 502 provider failure |
| `addRevision` | POST `/sketches/{id}/revisions` | `{profile, mode, reference_image?, note?}` | 201 `Sketch` | **login** | `NewSketch.save` | same |
| `updateSketch` | PATCH `/sketches/{id}` | `{title?, status?, notes?}` | `Sketch` | **login** | rename, status | — |
| `deleteSketch` | DELETE `/sketches/{id}` | — | 204 | **login** | `Library` | — |
| `deleteAll` | POST `/data/delete-all` | `{confirm:'DELETE'}` | `{deleted_sketches}` | **login** | `Settings` | 422 if the confirm text is wrong |
| `stats` | GET `/stats` | — | `{sketches, drafts, finals, revisions, last_method, last_generated_at}` | **login** | `Workspace` | — |
| `activity` | GET `/activity?limit=` | — | `{activity[{id, sketch_id, kind:'created'|'revision'|'updated'|'deleted'|'exported', message, created_at}]}` | **login** | `Workspace` | — |
| `storage` | GET `/storage` | — | `{data_dir, database, images, reference_images_stored}` | **login** | `Settings` | — |
| (URL builder) `pngDownloadUrl` | GET `/sketches/{id}/revisions/{n}/image.png?download=true` | — | PNG (900×1125) | **login** (cookie) | viewer, library, history | — |
| (thumbnail) | GET `…/image.png`, `…/image.svg` | — | PNG / SVG | **login** | cards, revision list, compare | `<img loading="lazy">` |
| `exportJsonUrl` | GET `/sketches/{id}/export.json?download=true` | — | JSON with keys `application, export_version, exported_at, sketch_id, title, status, description, created_at, modified_at, operator_notes, current_revision, generation_method, confirmed_traits, unknown_traits, unresolved_conflicts, distinctive_marks, adjustments, observations, revisions, disclaimer` | **login** | `Library` | — |
| `reportUrl` | GET `/sketches/{id}/report` | — | printable HTML (`text/html`) | **login** | `Library` (new tab) | — |

**No polling or streaming endpoints exist** other than the 30 s health poll. There are no WebSockets and no server-sent events. [SRC]

### 10.1 Recommended adapter boundary for WitnessTrace [INFERRED]

```
UI components (ported markup + CSS)
   │ events: describe, setAttribute, refine(text), generate, selectRevision, compare(a,b), export(kind)
   ▼
Frontend state/services (vanilla modules: store.js, router.js, toasts.js)
   ▼
WitnessTraceApi adapter  ← the only module that knows WitnessTrace URLs and payloads
   ▼
Existing WitnessTrace FastAPI (port 8001) → existing worker → Codex CLI subprocess → image file
```

**The adapter must provide:**

1. **`generate(caseId, attributes, text)`** returning a job handle. Poll the existing job/status route (if one exists **[MISSING]**) and resolve to `{revisionId, imageUrl, parentId, createdAt}`.
2. **`listRevisions(caseId)`** returning a parent-child tree plus the preferred flag.
3. **Image URLs that are same-origin**, or proxied, for `<img>`.
4. **Export URLs** for WitnessTrace's PDF, JSON and PNG.
5. **Error normalisation** to `{status, detail}`, with 502, 503 and 504 treated as offline (fixes defect 1 in §8).

**Assumptions in Revelio's UI that block a direct hookup:**

- The `Profile` schema: 20 traits and 16 adjustments, versus WitnessTrace's 45 attributes in 7 groups.
- Synchronous generate.
- `RV-` sketch IDs used as the unit of work, versus WitnessTrace **cases**.
- 4:5 image aspect ratio.
- A live procedural `/render` for instant preview, versus WitnessTrace's **explicit "Update Preview"**.
- Cookie login.
- The `/api` prefix.
- Revision numbering is linear, versus WitnessTrace's parent-child tree.

**Do not** route WitnessTrace generation through Revelio's `/render` or `/sketches/generate`, and do not replace the Codex CLI pipeline.

---

## 11. Image viewer and editor architecture

| Capability | Where | Implementation | Processing type |
|---|---|---|---|
| Image display | `SketchViewer` | `<img>` inside `.viewer__frame` (`aspect-ratio:4/5`), `draggable=false` | Pure frontend display |
| Live preview | `NewSketch` | SVG string from `POST /render` → `Blob(image/svg+xml)` → `URL.createObjectURL` | **Backend** procedural vector rendering (not AI) |
| Saved image | revisions | `<img src="/api/sketches/{id}/revisions/{n}/image.png">` | Backend file (Pillow PNG) |
| Zoom | `SketchViewer` | discrete steps 50–300%; sets frame `width: zoom×100%`; the stage scrolls when zoomed (`.is-zoomed`) | Pure frontend CSS |
| Pan | — | **Not implemented** beyond native scrolling of the zoomed stage | — |
| Fit | `SketchViewer` | zoom = 1 | Frontend |
| Before / after | `CompareSlider` | two stacked `<img>`, top one clipped with `clip-path: inset(0 X% 0 0)`; pointer capture; keyboard | Pure frontend |
| Side-by-side | `Compare` page | CSS grid `.split` with two figures | Frontend |
| Scan-line effect | `.viewer__scan` | CSS animation overlay; never touches pixels | Frontend, cosmetic |
| Download | viewer, library | saved: anchor to the backend route; unsaved: `POST /render.png` → `downloadBlob` | Backend |
| Upload | `ReferenceUpload` | `FileReader.readAsDataURL`; type/size checks; sent as a data URL in JSON; backend re-encodes (EXIF stripped) and never stores it | Frontend read + backend validation |
| Cropping, rotation, flip, filters, drawing, layers, brightness / contrast | — | **None in Revelio** | — |
| Multi-angle viewing | — | **None in Revelio** | — |
| Canvas | `src/landing/Hero.jsx` only | 2D canvas "liquid reveal" mask over a pre-rendered image (pointer-driven brush, DPR-aware), disabled without hover or with reduced motion | Decorative, frontend |

**Guidance for WitnessTrace [INFERRED].**

- **Keep WitnessTrace's existing Sketchpad and Enhance engines.** Revelio has no editor or filter engine to offer and none should be introduced.
- **Reuse Revelio's visual chrome around them:** the `.viewer` panel with corner brackets, the `.viewer__bar` toolbar of ghost icon buttons and separators, the `.viewer__meta` strip, the `.segmented` control, `.range` sliders with fill, `.tabs`, and the `.tag` provenance badges.
- **Use `CompareSlider`** for Enhance before/after and for version comparison.
- **Replace the 4:5 assumptions** with `object-fit: contain` on a neutral stage if Codex outputs are square or another ratio.

---

## 12. Asset manifest and licensing

| Asset | Path | Type / size | Where used | Essential | In Git | Origin / licence | Transfer |
|---|---|---|---|---|---|---|---|
| Owl mark | `src/assets/brand/logo-mark.png` | PNG 256×256, 47 KB | `LogoMark` (topbar on mobile, landing nav, workspace hero reticle, auth header) | For Revelio branding only | Yes | Derived from a logo **supplied by the project owner**; **ownership and licence unknown** | **No.** Use WitnessTrace's own logo. |
| Wordmark | `src/assets/brand/logo-wordmark.png` | PNG 554×170, 63 KB | `BrandLogo` (sidebar, boot, landing nav and menu, footer) | Branding only | Yes | Same as above | **No** |
| Favicon / touch icon | `public/favicon.png`, `public/apple-touch-icon.png` | PNG 64², 180² | `index.html` | Branding | Yes | Derived from the owl | **No** |
| Landing hero images | `public/landing/demo-r1.webp`, `demo-r2.webp` | WebP 900×1125, 26–29 KB | `Hero.jsx` liquid reveal, auth side panel (`demo-r2`) | No | Yes | Generated by this project's renderer from a **fictional** profile (`scripts/render-landing-assets.py`); original | Optional (placeholder art only) |
| Report header logos | `backend/app/assets/logo-mark.png` (96²), `logo-wordmark.png` | PNG | HTML report | Backend | Yes | Same as the brand | **No** |
| Original logo files | `src/images/image-removebg-preview.png` (610×409), `… copy.png` (identical duplicate), `coTHe-removebg-preview.png` (377×261) | PNG | **Not referenced by code** | No | Yes | Supplied by the owner; licence unknown | **No** |
| Icons | inline in `src/components/ui/Icon.jsx` | SVG path data | everywhere | **Yes** | Yes | Authored in this project (simple geometric strokes); original | **Yes** (copy the path map) |
| Background grids / glows | CSS gradients in `index.css`, `app.css`, `landing.css` | CSS | body, hero, viewer, demo | Yes (look) | Yes | Original CSS | **Yes** |
| Select chevron | data-URI SVG in `index.css` `.select` / landing `.lp-select` | CSS | selects | Yes | Yes | Original | **Yes** |
| Fonts | Google Fonts: Inter, IBM Plex Mono, Syne | web fonts | global | **Yes** | No (CDN) | SIL OFL 1.1 [INFERRED] | **Yes.** Self-host for offline Fedora use. |
| README screenshots | `docs/screenshots/*.png` (12) | PNG | docs | Reference | Yes | Captured from this app | As visual reference only |

**Do not transfer:**

- `backend/data/` (contains the owner's real `revelio.db` and images; git-ignored).
- `backend/.venv/`, `node_modules/`, `dist/`.
- Any `.env` (none exists).
- `scripts/` (Revelio-specific).
- The **brand name "Revelio"** and its logos.

---

## 13. Responsive design and screenshots

### 13.1 Where the screenshots are

- **Persistent, committed (12 files):** `docs/screenshots/` contains `landing.png`, `landing-light.png`, `landing-demo.png`, `landing-editor.png`, `workspace.png`, `workspace-light.png`, `new-sketch.png`, `new-sketch-light.png`, `compare.png`, `library.png`, `settings.png` and `composites.png` (renderer output samples). They were taken before the accounts feature, so the topbar has no account avatar.
- **Captured for this handoff (75 files, temporary):** `/private/tmp/claude-501/-Users-shridharbhat-Downloads-ShareLock-main-2/0ba29ce9-01b5-447a-871c-8eb837bc1386/scratchpad/handoff/shots/`
  - These live **outside the repository** in a session scratch area and **may be deleted when the session ends**. Ask the project owner to copy them into the repo (for example `docs/ui-handoff/`) if they are needed for visual QA.
  - In the same folder:
    - `browser-results.json` holds the tokens, element metrics, interaction checks and viewport data.
    - `api-samples.json` holds the request and response samples.
  - Filenames used in this document:
    - **Landing:** `landing-hero-dark`, `landing-hero-light`, `landing-platform`, `landing-features`, `landing-how`, `landing-privacy`, `landing-pricing`, `landing-faq`, `landing-demo-generated`, `landing-editor-compare`, `landing-pricing-modal`.
    - **Auth:** `auth-login-dark`, `auth-register-dark`, `auth-login-light`, `auth-register-light`, `auth-register-errors`, `auth-login-error`.
    - **Offline states:** `app-engine-offline`, `auth-offline`, `landing-demo-offline`.
    - **Workspace:** `app-boot`, `app-workspace-dark`, `app-workspace-light`, `app-notifications`, `app-account-menu`.
    - **Studio:** `app-new-empty`, `app-new-extracted`, `app-new-editor-tab`, `app-viewer-zoomed`, `app-viewer-compare`, `app-new-refine`, `app-new-guided`, `app-new-witnesses`, `app-new-light`.
    - **Library:** `app-library`, `app-library-empty-search`, `app-library-history`, `app-library-delete-confirm`, `app-library-light`.
    - **Compare:** `app-compare-slider`, `app-compare-split`, `app-compare-light`.
    - **Settings:** `app-settings`, `app-settings-delete-all`, `app-settings-light`.
    - **Responsive:** `vp-{1440|1280|768|390}-{landing|login|workspace|new|library|compare|settings}`, plus `vp-390-sidebar-open` and `vp-390-landing-menu`.
- **How they were captured:**
  - **Browser and data:** headless Brave (Chromium) driven over the DevTools protocol, logged in as a throwaway test account on isolated test data. The API ran on 8021 and Vite on 5182; a second Vite on 5183 pointed at a dead port for the offline captures.
  - **Viewport:** device scale factor 1. Mobile emulation was used at 390px.
  - **Theme:** dark unless the name says `-light`.

### 13.2 Viewport results [BROWSER]

Horizontal overflow means `scrollWidth > innerWidth`.

| Viewport | Landing | Login | Workspace | New Sketch | Library | Compare | Settings |
|---|---|---|---|---|---|---|---|
| **1440×900** | Stacked top-right links, toggle beside them; no overflow | Two-column auth | Sidebar fixed; 4 stats; 2-column grid | Studio `340 / 412 / 360` px | Card grid | Two columns | Three-column grids |
| **1280×800** | Same | Same | Stats become 2×2 | Studio `330 / 638`; side panel drops below the centre | OK | OK | Providers and settings 2-column |
| **768×1024** | ☰ menu (links hidden) | Single-column card | **Sidebar becomes a drawer** (☰ in the topbar); single column; hero visual hidden | One column (720px) | OK | One column | ❌ **overflow 61px** (provider cards) |
| **390×844** | ☰ full-screen menu; "Open Workspace" and "Log in" hidden from the bar | Single column | Drawer; stats one column; topbar hides the engine dot, clock date and case label | One column (362px); pipeline text hidden; viewer height auto | One column | One column | OK |

- **Touch targets:** most controls are ≥30px tall. `.btn--sm` is 30px, and tags and chips are 20–24px, but those are non-interactive or secondary.
- **Small (<24px) interactive targets counted:** landing 19–21 (inline text links and FAQ summaries), New Sketch 3, Settings 2. **[BROWSER]**
- **Modals:** these are centred cards; on mobile they span the width minus a gutter. **[INFERRED from CSS; screenshots at 1440 only]**

---

## 14. Exact reusable source files

This is what to hand over, in priority order. These are **source files only**, sanitised. **No** backend code, database, `.env`, `node_modules` or brand images.

| Priority | File | Why | Expected handling |
|---|---|---|---|
| 1 | `src/index.css` | All tokens, reset, buttons, inputs, range, segmented, chips, tags, alerts, skeleton, keyframes, scrollbars, reduced motion | **Flatten** the four palette layers into a single token block (§6.6); keep the component classes |
| 1 | `src/styles/app.css` | Shell, sidebar, topbar, boot, toasts, modals, hero, stats, cards, studio grid, viewer, traits, adjust, refine, merge, revisions, library, compare, settings, responsive rules | Port the **shell, panel, viewer, toolbar, tabs, cards, compare, settings, toasts, modal and responsive** sections; drop Revelio-only sections as features are mapped |
| 1 | `src/components/sketch/CompareSlider.css` | Compare slider look | Copy as-is |
| 1 | `src/components/ui/Icon.jsx` | Icon path data | Extract the `P` map into a JS object or SVG sprite |
| 2 | `src/components/sketch/CompareSlider.jsx` | Behaviour reference (≈50 lines) | Re-implement in vanilla JS |
| 2 | `src/components/sketch/SketchViewer.jsx` | Viewer toolbar, zoom steps, compare toggle, meta strip | Re-implement |
| 2 | `src/components/ui/Modal.jsx` | Focus trap, Esc, scroll lock, type-to-confirm | Re-implement |
| 2 | `src/components/shell/Toasts.jsx` + `notify` in `src/state/AppContext.jsx` | Toast stack and notification log | Re-implement |
| 2 | `src/components/shell/Sidebar.jsx`, `Topbar.jsx`, `BootScreen.jsx`; `src/App.jsx` (shell markup and `EngineOffline`) | Shell markup reference | Re-implement |
| 2 | `src/components/sketch/Pipeline.jsx` | Step strip | Re-implement (tiny) |
| 2 | `src/lib/theme.js`, `src/components/ui/ThemeToggle.jsx` | Theme mechanism | Re-implement (rename the storage key) |
| 3 | `src/pages/Workspace.jsx`, `NewSketch.jsx`, `Library.jsx`, `Compare.jsx`, `Settings.jsx` | Layout and composition reference | Use as **markup and behaviour reference only** |
| 3 | `src/components/sketch/TraitPanel.jsx`, `AdjustPanel.jsx`, `RefinePanel.jsx`, `DescriptionPanel.jsx`, `ModeSelector.jsx`, `RenderNotes.jsx` | Character Lab, refinement and input visuals | Adapt to WitnessTrace data |
| 4 (optional) | `src/components/ui/DictateButton.jsx`, `src/components/sketch/WitnessMerge.jsx`, `src/landing/*`, `src/auth/*` | Enhancements | Only if wanted (§15.2) |
| Ref | `index.html` (font link) | Font loading | Replace with self-hosted `@font-face` |
| Ref | `docs/screenshots/*.png` + the §13 captures | Visual targets | QA reference |

This Markdown is **not sufficient by itself.** The receiving agent needs at minimum the **Priority 1 files** to reproduce the appearance faithfully, because `app.css` alone is about 3,600 lines of specific values.

---

## 15. UI-to-WitnessTrace feature mapping

WitnessTrace's routes, payloads and markup were **not available** [MISSING]. The targets below come from the feature list in the integration brief and must be confirmed in M0.

### 15.1 Mapping table

| Revelio source UI (actual component) | WitnessTrace feature | Integration requirement |
|---|---|---|
| Shell: `Sidebar` + `Topbar` + `.content` (`App.jsx`) | Main application shell and navigation | Rebuild the markup; nav items become WitnessTrace sections (Dashboard, Case, Character Lab, Refine, Sketchpad, Enhance, Multi-view, Reports, Settings); the case chip shows the **current case** |
| `Workspace` overview (hero, `.stats`, recent cards, unfinished, activity, providers) | Main dashboard | Stats → case counts and revisions; recent cards → recent cases or revisions; providers → **Codex CLI auth/availability**; activity → WitnessTrace audit or provenance log if one exists |
| `DescriptionPanel` free-text tab (textarea, char counter, examples, primary CTA, `⌘↵`) | Text input + **immutable original witness statement** | Post to WitnessTrace's statement/case route; after the first save, render the statement **read-only** (it is immutable), with clarifications appended separately |
| `TraitPanel` (grouped selects, provenance tags *Described/Extracted/Manual/Unknown/Conflict/Uncertain*, evidence quotes, conflict chips) | Structured facial description + **sourced clarifications** + **uncertainty annotations** | Map WitnessTrace's 45 attributes in 7 groups to `traits__group` sections; map source and uncertainty fields to the `.tag--*` variants; evidence → clarification source text |
| `AdjustPanel` (feature selects + `.range` sliders with fill, value read-out, per-slider reset, double-click reset) | **Character Lab** sliders and selectors + saved drafts | Bind to WitnessTrace attribute values and ranges; **no live render.** Show a "Preview pending" state, and bind the primary button to WitnessTrace's **explicit "Update Preview"** generation |
| `RefinePanel` (input + example chips + "Interpret" + confirm list) | **Iterative natural-language refinement** | Keep the input and example chips. If WitnessTrace sends the instruction straight to Codex, replace the parse/confirm list with a confirmation summary and submit to the existing refinement route, which creates a child revision |
| `SketchViewer` (tag *AI-generated*, zoom, fit, before/after, PNG, meta strip) | Image preview for revisions | `src` = WitnessTrace revision image URL; `kind='ai'`; meta = case id, revision id, parent, created, preferred flag; download → existing PNG export |
| `.generate` panel (note input, primary button, indeterminate progress + `Elapsed`, provider error with fallback) | Codex CLI generation trigger and job feedback | Primary button → existing generate route; progress bar for the job duration; errors → `.generate__error`. **Remove the "offline composite" fallback**, which is a Revelio concept |
| `Pipeline` | Generation job / case workflow status | Steps such as Statement → Attributes → Generating → Revision saved → Preferred selected |
| `.revisions` list (thumbnails, R#, tag, time, note) | Version history with **parent-child** links and **preferred** version | Extend: indent or show a "from R#" parent label, plus a star toggle for preferred (new UI, built from `.chip`/`.tag` styles) |
| `CompareSlider` + `Compare` page (pickers, slider/split, diff table) | Before/after comparison and version comparison | Pickers list WitnessTrace revisions; the diff table compares attribute values between revisions |
| `Library` (`.lib-card` grid, search, rename, status chip, history modal, delete confirm, export row) | **Case management** (create, select, list) + case image history | Cards = cases (thumbnail = preferred or latest revision); "Open" selects the case; history modal = revision tree; export row → PDF/JSON/PNG routes |
| Export buttons (PNG / JSON / Report) | **Case reporting:** PDF, JSON, PNG, provenance, SHA-256 | Point the links at WitnessTrace exports; add a **PDF** button and show the **SHA-256** in the history modal / meta strip (`.mono` value + copy icon) |
| `Settings` (provider cards, privacy list, interface switches, danger zone) | Settings | Provider card → Codex CLI status; keep the theme and reduce-motion switches; the danger zone only if WitnessTrace supports deletion |
| `ReferenceUpload` | **Enhance workspace** image upload | Restyle WitnessTrace's existing upload input with this card; keep WitnessTrace's processing |
| `Toasts`, `Modal`/`ConfirmModal`, `EmptyState`, skeletons, `BootScreen`, `EngineOffline` | Global feedback and states | Re-implement once and reuse everywhere |

### 15.2 WitnessTrace features with no Revelio UI: design recommendations [INFERRED]

These must **not be lost**. Build them from Revelio primitives:

- **Digital Sketchpad** (pencil, brush, eraser, shapes, undo/redo, zoom/pan, crop/rotate/flip, layers): keep WitnessTrace's canvas engine. Wrap it in a `.viewer.panel.panel--corners` with a `.viewer__bar` tool row (ghost icon buttons, `.viewer__sep`, an active tool = `aria-pressed` + accent), a right-side `.studio__side`-style panel with tabs **Tools / Layers / Transform**, and layer rows styled like `.rev` items.
- **Enhance** (brightness, contrast, exposure, gamma, sharpen, smooth, colour, presets, before/after): `.range` sliders grouped like `AdjustPanel` (`adjust__group` + `.label` headings + per-slider reset), presets as `.segmented` or `.chip` buttons, compare via `CompareSlider`.
- **Multi-view** (2D multi-angle sheets, angle navigation, downloads): the viewer stage plus a `.segmented` angle switcher (Front / ¾ / Profile…) and a thumbnail strip using `.revisions__list` styles. **Label it "AI-generated 2D reference sheet"** with `.tag--ai`, not 3D.
- **Case creation and selection:** a `Modal` form (title, case number) and a case switcher in the topbar `case-chip` (make it a button that opens a picker).
- **Immutable statements and sourced clarifications:** the read-only statement in a `.panel` with `.mono` metadata (timestamp, SHA-256), and clarifications as a `.timeline` list with source tags.
- **Preferred version:** a star icon (add an icon path) plus a `.chip--green` "Preferred" badge.

### 15.3 Revelio features WitnessTrace does not have (optional enhancements)

- Multi-witness merge (`WitnessMerge`)
- Guided questions (`GuidedForm`)
- Browser dictation (`DictateButton`)
- Light/dark theme toggle
- Draft autosave and restore banner
- Instant live preview (procedural; **not applicable** to Codex generation)
- Renderer honesty notes (`RenderNotes`)
- Boot checklist
- Notifications log
- Local accounts
- Marketing landing page

---

## 16. Framework compatibility recommendations

| | Option 1: bring React + Vite into WitnessTrace | Option 2: recreate the visuals inside WitnessTrace's vanilla frontend **(recommended)** |
|---|---|---|
| What moves | A Vite build (`dist/`) served by FastAPI `StaticFiles`; a new adapter layer | Token CSS, component CSS, icon map and about 6 small vanilla widgets |
| New dependencies | react, react-dom, vite, plugin-react, a Node toolchain on Fedora | **None** (fonts self-hosted) |
| Reuse of Revelio JS | Shell and widgets yes; **domain components mostly rewritten anyway** (Profile model, sync generate, IDs) | JS used as a reference only |
| Risk to WitnessTrace's working features | **High.** Every existing screen (Sketchpad, Enhance, Multi-view, cases, reports) must be rewritten in React or embedded | **Low.** Restyle existing pages in place, one screen at a time |
| Reversibility | Hard (a parallel frontend) | Easy (CSS file plus per-screen markup commits) |
| Effort | High | Medium |

**Why Option 2 [INFERRED from the source architecture].**

- Revelio's look comes almost entirely from **plain CSS classes and tokens**. There is no Tailwind, no CSS-in-JS and no component library, so it ports to vanilla HTML without a framework.
- The React parts that carry interaction quality (compare slider, modal, toasts, viewer toolbar, theme toggle, pipeline) are each under about 150 lines and depend only on DOM APIs.
- The domain components would need rewriting for WitnessTrace's data model in either option.
- A framework migration would put the working Codex, Sketchpad and Enhance flows at risk.

**Key porting rules:**

- **Scope the CSS** so generic class names don't collide with WitnessTrace's: either adopt the class names wholesale on restyled screens, or prefix them (for example `.wt-btn`).
- **Keep WitnessTrace's routing.** If it has none, the 24-line hash router pattern is enough.
- **Keep WitnessTrace's existing JS modules** for data. Add a thin `api-adapter.js` (§10.1).

---

## 17. Step-by-step migration strategy

Every phase is designed to be one or more small commits on a branch, testable alone, and reversible with `git revert`. **Do not implement during this handoff.**

| Phase | Objective | Source files needed | Target features | Dependencies | Complexity | Verification | Rollback | Done when |
|---|---|---|---|---|---|---|---|---|
| **M0: intake and baseline** | Inventory WitnessTrace routes, payloads, templates and JS; capture baseline screenshots and a functional test run; confirm font and logo licensing | This doc, `docs/screenshots`, §13 captures | All | WitnessTrace repo access [MISSING] | Low | Baseline Playwright run green; a list of every WitnessTrace screen and endpoint | n/a (read-only) | Gap list signed off; §21 questions answered |
| **M1: design system** | Add `wt-tokens.css` (flattened §6.6 values, dark/light via `html[data-theme]`), self-hosted fonts, base reset **scoped**, buttons, inputs, range, tabs, segmented, chips, tags, alerts, panels, skeleton, keyframes, reduced motion, icon helper | `src/index.css`, parts of `src/styles/app.css`, `Icon.jsx`, `CompareSlider.css` | none functionally | M0 | Medium | Visual diff of a component gallery page against Revelio screenshots; computed-style assertions (§19); WitnessTrace tests unchanged | Remove the CSS link and helper | Gallery matches tokens; no existing screen regresses |
| **M2: shell and dashboard** | Sidebar, topbar (case chip, status dot, clock, theme toggle, notifications), toasts, modal, boot and offline states, dashboard layout | `Sidebar.jsx`, `Topbar.jsx`, `Toasts.jsx`, `Modal.jsx`, `BootScreen.jsx`, `App.jsx`, `Workspace.jsx`, `app.css` shell sections | Dashboard, navigation | M1 | Medium | Every nav target reachable; **a Codex generation still runs end-to-end**; no console errors; 1440/1280/768/390 screenshots | Revert the shell template | Navigation parity plus generation unchanged |
| **M3: text input and Character Lab** | Restyle statement input and Character Lab with `DescriptionPanel`, `TraitPanel` and `AdjustPanel` patterns; provenance and uncertainty tags; explicit Update Preview | those components + `app.css` (traits, adjust, describe) | Text input, immutable statement, 45 attributes, drafts | M2 | High | All 45 attributes render, save and reload; uncertainty annotations persist; Update Preview triggers the existing worker | Revert the per-screen commit | Feature parity verified against the M0 list |
| **M4: preview, refinement and history** | `SketchViewer` chrome, generate panel with progress and errors, revision list with parent/preferred, `CompareSlider`, Compare page | `SketchViewer.jsx`, `CompareSlider.*`, `NewSketch.jsx` (generate and revisions markup), `Compare.jsx`, `RefinePanel.jsx` | Refinement, revisions, before/after, preferred version | M3 | High | Refinement creates a child revision; parent link displayed; preferred toggle persists; compare works with keyboard | Revert | All revision features pass |
| **M5: Sketchpad and Enhance chrome** | Wrap the existing canvas and enhance tools in viewer, toolbar and side-panel styling; sliders for adjustments; before/after | `app.css` viewer, tabs, adjust; `CompareSlider` | Sketchpad, Enhance | M4 | Medium–High | Every tool still works (draw, erase, shapes, undo/redo, zoom/pan, crop/rotate/flip, layers; each enhancement and preset); saved revisions identical | Revert | Tool-by-tool checklist green |
| **M6: Multi-view, cases and exports** | Angle switcher and strip; case list/cards (`Library` pattern), case picker; export row with PDF/JSON/PNG and SHA-256 display | `Library.jsx`, `app.css` library and compare; `Modal.jsx` | Multi-view, case management, reports | M2 | Medium | Exports download byte-identical to before (hash compare); case switching keeps data; multi-view labelled 2D | Revert | Parity plus provenance visible |
| **M7: visual QA and regression** | Cross-screen visual QA, accessibility, responsive, performance | §19 plan | All | M1–M6 | Medium | §19 pass criteria | Per-phase reverts | Sign-off |

---

## 18. Integration risks and mitigations

| Risk | Evidence | Mitigation |
|---|---|---|
| **Global reset and body styling** | `index.css` sets `*{margin:0;padding:0;box-sizing}`, `body` font 14px, background grid and `transition`; `html{scroll-behavior:smooth}` | Load the reset only on restyled pages or scope it under a root class; audit existing WitnessTrace layouts |
| **Generic class-name collisions** | `.panel .btn .tag .chip .label .input .select .range .modal .toast .tabs .icon .dot .alert .field .switch .hero .stats .content .app` | Prefix (`wt-`) or migrate whole screens at once; grep WitnessTrace CSS for overlaps in M0 |
| **Layered palette overrides** | Four `:root` layers in `index.css` plus duplicate layers in `landing.css` (§6.0) | Port only the **effective** values (§6.1) as one file |
| **Misleading token names** | `--cyan` = accent, `--blue` = neutral | Rename to semantic names (§6.6) |
| **Hard-coded legacy colours** | `app.css`: 47 hex + 56 rgba literals, 16 legacy cyan; `landing.css`: 209 hex, 26 legacy cyan; e.g. the viewer stage `rgb(6,9,14)` with a cyan glow, the selected mode-card cyan glow, tag backgrounds `rgba(8,11,18,.85)` | Replace with tokens while porting; review each component in both themes |
| **Light-theme status colours unset** | `--red/--amber/--green` stay dark-palette brights in light (§6.1) | Define light values (§6.6) |
| **landing.css styles workspace classes** | `landing.css` lines ~3106–3155 target `.topbar` and `.sidebar` in light theme; only loaded with the landing chunk | Ignore for WitnessTrace (don't port landing.css wholesale) |
| **Fonts from a CDN** | Google Fonts link in `index.html` | Self-host the OFL fonts for an offline Fedora deployment |
| **Framework mismatch** | React 19 vs vanilla | Option 2 (§16) |
| **Synchronous generate assumption** | `NewSketch.save` awaits one POST | Adapter with job polling; keep the indeterminate progress UI |
| **Live preview assumption** | debounced `/render` on every change | Replace with the explicit "Update Preview" button and a stale-preview badge |
| **Data-model mismatch** | 20 traits / 16 adjustments vs 45 attributes / 7 groups | Drive the panels from WitnessTrace's attribute schema; reuse only the row and slider markup |
| **Image aspect ratio** | 4:5 hard-coded in viewer, compare, cards and thumbnails | Make the ratio a CSS variable; use `object-fit: contain` |
| **Blob URL memory** | SVG previews are blob URLs (revoked correctly) | If WitnessTrace previews are blobs, revoke on replace and unmount; prefer server URLs for large PNGs |
| **Large images** | Zoom changes `<img>` width up to 300% | Fine for single images; for very large Codex outputs consider `decoding="async"` and size limits |
| **Auth and cookie assumptions** | 401 redirect in `client.js`; cookie session | Drop unless WitnessTrace adds auth |
| **Offline detection bug** | 502 behind a proxy not treated as offline (§8) | Adapter treats 0/502/503/504 as offline |
| **Responsive defects** | Settings overflow at 768; sidebar label clipping | Fix during the port (`minmax(0,1fr)` on `.providers`; shorten the label or widen the sidebar to ~264px) |
| **Port collisions on the target machine** | Revelio defaults 8000/5173; WitnessTrace 8001; another app on 8000 | Never run Revelio dev servers there with default ports |
| **Licensing** | Logo ownership unknown; "Revelio" brand | Do not transfer the brand assets; fonts OFL; icons original |
| **Dead code carried over** | `IntroLoader.jsx`, `Wordmark`, `src/images/*` | Exclude |
| **Accessibility regressions** | Revelio has skip links, focus rings (`--focus`), `aria-*` on tabs, sliders, dialogs and live regions | Keep these patterns; include an axe/Lighthouse pass in M7 |

---

## 19. Visual and functional test plan

These tests are **for the receiving team.** **None has been run against WitnessTrace.**

### 19.1 Visual

1. **Reference set.** Use Revelio screenshots (§13) at 1440, 1280, 768 and 390, dark and light.
2. **Capture.** Use Playwright (Chromium) with the same viewports, `deviceScaleFactor: 1`, `reducedMotion: 'reduce'` for stable frames, and fonts loaded (`document.fonts.ready`).
3. **Compare.** Content differs between the apps, so **do not rely on whole-page pixel diffs.** Instead:
   - **(a) Token assertions:** read `getComputedStyle(document.documentElement)` and the key elements, and compare with §6.1 and §6.3. **Pass:** exact hex and px matches.
   - **(b) Layout assertions:**
     - sidebar 248px (drawer ≤1080px);
     - topbar 60px;
     - panel radius 14px;
     - button heights 36/30/44;
     - studio-equivalent grid columns per §6.4;
     - **pass:** within ±1px.
   - **(c) Component gallery pixel diff:** render the same static gallery page (buttons, inputs, tags, chips, panel, toast, modal, viewer chrome, compare slider with fixed images) in both apps. **Pass:** ≤2% pixel difference.
   - **(d) Side-by-side human review** of each screen pair.
4. **Pass gate:** no horizontal overflow at any viewport, both themes render every screen, and no unreadable text (contrast ≥4.5:1 for body text, checked with axe).

### 19.2 Functional regression

Each item is pass/fail against the M0 baseline.

| Area | Test | Pass criterion |
|---|---|---|
| Navigation | Visit every nav target; browser back and forward; reload on each | Correct screen; no console errors |
| Text generation | Enter a statement → generate | Existing Codex flow produces an image file; preview shows it; revision persisted |
| Codex CLI integration | Generate while the CLI is unauthenticated, then authenticated | Clear error state; successful job after auth; **no change to the worker or subprocess code** |
| Character Lab | Change each of the 45 attributes (sliders and selects), add uncertainty, save draft, reload | Values and annotations persist; Update Preview generates |
| Case selection | Create, switch and reopen cases | Case-specific history only; original statement immutable |
| Revisions | Refine twice; open the parent; mark preferred | Parent-child chain correct; preferred persists after a server restart |
| Comparison | Slider drag, ← → keys, side-by-side | Correct images; `aria-valuenow` updates |
| Sketchpad | Each tool, undo/redo, zoom/pan, crop/rotate/flip, layers, save | Identical results to baseline; saved revision |
| Enhance | Each adjustment and preset, before/after, save | Same output hashes as baseline for the same inputs |
| Multi-view | Navigate angles, download | Files download; labelled 2D |
| Reports | PDF, JSON, PNG | Downloads succeed; SHA-256 values unchanged for unchanged data |
| Loading and errors | Stop the backend; slow network | Offline state shown (including 502 behind a proxy); spinners and progress visible; no blank screens |
| Refresh and restart | Reload mid-workflow; restart the server | State restored from the server; nothing lost |
| Mobile | 390 and 768 | Drawer nav works; no overflow; tap targets ≥30px |
| Console | Every screen | 0 errors, 0 unhandled rejections |
| Data preservation | Before and after migration | Original files, DB rows and image files untouched (checksum the data directory) |

---

## 20. Complete transfer checklist

- [ ] WitnessTrace repository access and M0 inventory (routes, payloads, templates, JS, tests) **[MISSING today]**
- [ ] `src/index.css`, `src/styles/app.css`, `src/components/sketch/CompareSlider.css` (source CSS)
- [ ] `src/components/ui/Icon.jsx` (icon path map)
- [ ] Behaviour references: `CompareSlider.jsx`, `SketchViewer.jsx`, `Modal.jsx`, `Toasts.jsx` + `AppContext.jsx` `notify`, `Sidebar.jsx`, `Topbar.jsx`, `BootScreen.jsx`, `Pipeline.jsx`, `theme.js`, `ThemeToggle.jsx`, `App.jsx`
- [ ] Layout references: `src/pages/*.jsx`, `src/components/sketch/{TraitPanel,AdjustPanel,RefinePanel,DescriptionPanel,ModeSelector,RenderNotes}.jsx`
- [ ] Self-hosted font files: Inter 400–700, IBM Plex Mono 400–600, Syne 600–800 (download from the official OFL sources)
- [ ] Reference screenshots: `docs/screenshots/*.png` + the §13 capture folder (copy it into the repo before it expires)
- [ ] `browser-results.json` (computed tokens and metrics) and `api-samples.json` (contracts) from the §13 folder
- [ ] **Exclude:** `backend/**`, `backend/data/**`, `.venv`, `node_modules`, `dist`, `.env*` values, `src/assets/brand/*`, `public/*.png`, `src/images/*`, `scripts/*`, `IntroLoader.jsx`, the brand name
- [ ] Confirm WitnessTrace's own logo, name and favicon for the shell's brand slots
- [ ] Owner confirmation that sharing the listed source files is authorised (no archive was created)

---

## 21. Unresolved questions and missing information

1. **WitnessTrace source.** Its endpoints, request and response schemas, job/status mechanism, image URL format, frontend file layout, CSS and test suite were **not supplied**. The whole of §15 is therefore provisional.
2. **Generation latency and job model.** Is Codex generation synchronous HTTP, or a background job with a status route? This determines the adapter design (§10.1).
3. **Image dimensions and aspect ratio** of Codex outputs, Sketchpad canvases and multi-view sheets. This affects the 4:5 assumptions.
4. **Character Lab schema.** The exact 45 attributes, 7 groups, value ranges and uncertainty model.
5. **Revision tree.** How parent-child links and "preferred" are stored and exposed.
6. **Accounts.** Does WitnessTrace need login? If not, drop the auth UI and the 401 handling.
7. **Theme.** Keep both themes, or ship dark only?
8. **Branding.** WitnessTrace logo and colours: adopt Revelio's coral/sage palette as-is, or map it to WitnessTrace brand colours?
9. **Logo licensing.** The Revelio logo came from the project owner and its origin was not verified. It is not to be transferred.
10. **Font licensing.** OFL status is inferred from public knowledge. Confirm from the font repositories during M0.
11. **Not exercised in the browser:** hosted Gemini generation (no key); actual speech dictation (headless Brave has no speech service); deletion of a sketch and delete-all execution (gating verified only; backend tests cover the routes); mark add/remove; conflict-chip resolution; per-revision thumbnail navigation; title rename from the studio.
12. **Uncommitted change.** `src/landing/landing.css` has an uncommitted light-theme block (landing demo and editor showcase). Commit or discard it before using this file as the reference.

---

## 22. Final recommendation

**Adopt Revelio's design system and interaction patterns, not its code or backend.**

1. **Port the CSS.**
   - Port `index.css`, the relevant `app.css` sections and `CompareSlider.css` into WitnessTrace as a **single flattened token file plus component CSS**.
   - Rename the tokens semantically.
   - Fix the light-theme status colours and the two responsive defects.
2. **Re-implement the shell and the six behaviour widgets in vanilla JS:**
   - sidebar and topbar;
   - toasts;
   - modal and confirm modal;
   - viewer toolbar with zoom and before/after;
   - compare slider;
   - pipeline;
   - theme toggle.
3. **Restyle WitnessTrace screens in place, one phase at a time** (M2–M6). Feed them from a thin **WitnessTrace API adapter** that wraps the **existing** FastAPI routes and the **unchanged Codex CLI worker**, with job polling and normalised errors.
4. **Rebuild missing features with the same primitives.** Use Revelio primitives (panels, toolbars, tabs, sliders, tags, compare) to give Sketchpad, Enhance, Multi-view, cases and reports the same look. Never remove or replace their processing.
5. **Don't introduce React or Vite** unless the WitnessTrace team separately decides on a full frontend rewrite.

**Handoff sufficiency.** This document plus the Priority 1–2 source files (§14) and the screenshot and JSON artifacts (§13) are sufficient to reproduce Revelio's appearance and interaction quality. Mapping to WitnessTrace's functions stays **partial until M0** supplies WitnessTrace's code and contracts.

*Source changes made by this inspection: none. The only file added is `UI_INTEGRATION_HANDOFF.md`.*
