# MIGRATION_REPORT.md — Revelio → AggregateX AI (Phase 0: backend cleanup)

> **Scope.** This phase removed the old backend and preserved the frontend. The new backend was **not** implemented. No PostgreSQL, Kafka, Spark, Airflow or Redis was introduced.
>
> **Branch:** `aggregatex-migration` (created from `shridhar` @ `3786c31`) · **Recovery point:** tag `pre-aggregatex-cleanup` · **Date:** 2026-10-31
>
> Everything marked ✅ below was checked by running the command or test shown. The detailed pre-migration architecture is in [`MITIGATA.md`](MITIGATA.md).

---

## 1. Original project architecture

The project was **Revelio**, a forensic-composite workspace. It had four parts (details in `MITIGATA.md` §1):

| Part | Technology | Location (before) | Fate |
|---|---|---|---|
| Frontend SPA (landing, login/register, `/app` workspace) | React 19, Vite 8, plain CSS, ethers 6 | `src/`, `public/`, `index.html` | **Preserved** → `frontend/` |
| Revelio API + `/wt-api` gateway | FastAPI, SQLite (`revelio.db`), scrypt sessions | `backend/app/` | **Removed** |
| WitnessTrace case service | FastAPI, SQLite (WAL), Codex CLI subprocess jobs, ReportLab, Base Sepolia RPC | `witness-backend/` | **Removed** |
| Vanilla iframe editors (Sketchpad / Enhance / Multi-view) | Plain JS served by WitnessTrace | `witness-backend/static/` | **Removed** (backend-served, project-specific; category C in MITIGATA §4.3) |

The browser called two same-origin prefixes: `/api` through `src/api/client.js` and `/wt-api` through `src/api/witnesstrace.js`. Vite (dev) or nginx (Docker) proxied both to `127.0.0.1:8021`.

## 2. Safety steps taken (Step 2)

| Action | Result |
|---|---|
| Inspected `git status` | 4 uncommitted changes in `witness-backend/` and an untracked `MITIGATA.md` |
| Created branch `aggregatex-migration` | ✅ `shridhar` and `main` are untouched |
| Committed the uncommitted work as a snapshot (`e355718`) and tagged it `pre-aggregatex-cleanup` | ✅ Every removed file can be restored: `git checkout pre-aggregatex-cleanup -- <path>` |
| Archived **untracked** runtime data (`backend/data/`, 43 MB: accounts DB, WitnessTrace SQLite, generated images) | ✅ `.legacy-runtime-backup/revelio-backend-data-2026-10-31.tar.gz` (45 entries, git-ignored). Git never contained this data |
| Nothing pushed | The `origin` remote still points to the **original team repository** (`Hackfest-X-Saividya/ssdnexus-t1-20`). Re-point it before any push (MITIGATA risk R1) |

## 3. Old backend components removed (Step 3)

113 tracked files under `backend/` and `witness-backend/`, plus 14 deployment and script files.

| Removed | What it was |
|---|---|
| `backend/app/main.py`, `config.py`, `database.py`, `schemas.py`, `catalog.py` | Revelio FastAPI app factory, env config, SQLite schema (`users`, `sessions`, `sketches`, `revisions`, `activity`), Pydantic models, facial-trait catalog |
| `backend/app/api/` (`auth`, `system`, `sketches`, `traits`, `speech`, `witness_gateway`) | All `/api/*` routes and the `/wt-api` allowlist proxy |
| `backend/app/services/` (`auth_service`, `sketch_service`, `procedural_renderer`, `trait_extractor`, `refinement_service`, `merge_service`, `report`, `uploads`, `speech`) | Authentication backend (scrypt + session tokens) and all sketch business logic |
| `backend/app/providers/` | Generation provider interface + offline/local/hosted (Gemini) providers |
| `backend/tests/`, `pytest.ini`, `.env.example`, `requirements*.txt` | 72 pytest tests, backend env template, pins |
| `witness-backend/*.py` (`app`, `case_store`, `sketch_store`, `enhance_store`, `multiview_store`, `report_store`, `integrity_store`, `lab_schema`) | WitnessTrace routes, Codex job runner, case DB, PDF reports, blockchain integrity verification |
| `witness-backend/static/`, `tests/`, `start.sh`, `requirements*.txt`, `README.md`, `DEMO_GUIDE.md`, `PHASE_STATUS.md` | Vanilla editors + Bootstrap Icons, 72 pytest tests + fixtures, launcher, docs |
| `Dockerfile`, `docker-compose.yml`, `.dockerignore`, `docker/nginx.conf`, `docker/entrypoint.sh` | Single-container image: frontend build + Codex CLI + Python runtime + nginx |
| `render.yaml` | Render.com blueprint for that image |
| `scripts/dev-integrated.mjs`, `dev-all.mjs`, `run-api.mjs` | Launchers that started the Python services |
| `scripts/render-landing-assets.py` | Imported backend renderer services to pre-render landing images (the rendered `.webp` files in `public/landing/` are kept) |
| `scripts/tests/verify_startup.py`, `verify_integrity.py` | Python/Playwright E2E checks that launched both backends |
| Untracked: `witness-backend/.venv` (206 MB), `__pycache__/`, `.pytest_cache/`, root `dist/` | Regenerable environments and build output (deleted; `backend/data` archived first, see §2) |

### Endpoint configuration removed

| Where | Before | After |
|---|---|---|
| `vite.config.js` | Proxies `/api` → `REVELIO_API_URL` and `/wt-api` → `REVELIO_GATEWAY_URL` (both `127.0.0.1:8021`) | No proxies |
| `package.json` scripts | `dev` (3-process launcher), `dev:web`, `dev:api`, `dev:all`, `dev:legacy`, `test:api`, `test:adapter` | `dev` (Vite), `build`, `lint`, `preview`, `test` |
| `eslint.config.js` | Ignored `backend`, `witness-backend` | Ignores `dist` only |
| `.gitignore` | WitnessTrace-specific runtime paths | Generic Python/secret rules kept for the future backend; backup dir ignored |
| `.env.example` | Stale note about a `127.0.0.1:8000` proxy | Documents `VITE_BACKEND_ENABLED` and `VITE_API_BASE` |

## 4. Dependencies removed

**npm: none.** All three runtime dependencies are still used by preserved frontend code: `react`, `react-dom`, and `ethers` (`src/components/integrity/wallet.js`, used by the preserved `BlockchainIntegrity` component). `package-lock.json` is unchanged, and `npm ci` installs it as-is.

**Python** (all removed together with the backends):

| Package | Pinned version(s) | Used for |
|---|---|---|
| fastapi / starlette | 0.135.1, 0.162.0 / 1.10.0 | Both APIs |
| uvicorn | 0.38.0, 0.54.0 | ASGI server |
| pydantic | 2.12.1, 2.14.1 | Schemas |
| pillow | 12.0.0, 12.3.0 | Image rendering/validation |
| reportlab | 4.5.1 | PDF reports |
| httpx | 0.28.1 | Gateway proxy, tests |
| faster-whisper / av | 1.2.1 / 18.1.0 | Server-side dictation |
| pytest / playwright | 8.4.2, 9.2.0 / 1.63.0 | Backend tests |

**System/runtime:** nginx, tini, the Codex CLI (`@openai/codex`, installed in the Docker image), the baked-in Whisper model, and the `python:3.14-slim` / `node:22` images.

## 5. Frontend components preserved (Step 4)

The frontend moved from the repo root to `frontend/` using `git mv`, so per-file history is kept (`git log --follow`).

- **102 of 105 frontend files are byte-identical** to the snapshot, and so is `package-lock.json`. This was verified with a rename-aware `git diff -M` against `pre-aggregatex-cleanup`: every one shows as `R100`.
- **Every stylesheet is untouched:** `index.css`, `styles/app.css`, `styles/motion.css`, `landing/landing.css`, `auth/auth.css`, `pages/witness.css`, `CompareSlider.css`. The production CSS bundles have **the same content hashes** before and after (`index-C-u8dOPZ.css`, `App-C39MCYjg.css`, `landing-CF9AkGf6.css`, `AuthPage-RJNTwVKY.css`, `CompareSlider-BPpXF4z6.css`).
- **Preserved unchanged:** all pages (`Workspace`, `NewSketch`, `Library`, `Compare`, `Settings`, `WitnessStudio`/`WitnessWorkspace`, `WitnessTools`); the shell (`Sidebar`, `Topbar`, `BootScreen`, `Toasts`); UI primitives (`Icon` set, `Modal`/`ConfirmModal`, `EmptyState`, `ThemeToggle`, `CaseClock`, `DictateButton`); workflow and visualisation components (`WorkflowStepper`, `GenerationStatus`, `Pipeline`, `CompareSlider`, `SketchViewer`, `IntegrityVisuals`, `BlockchainIntegrity`); every `components/sketch/*` component; the landing page (all sections, the canvas hero, `motion.jsx`, `playOrb.js`, `IntroLoader`); routing (`main.jsx`, `lib/router.js`, `lib/nav.js`); theme, format and auth helpers; global state (`AppContext`, `useWitnessCases`); brand assets, `src/images/*`, `public/*`; and the Google Fonts links in `index.html`.
- **Test suites kept:** `scripts/tests/witnesstrace.test.mjs` and `integrity-wallet.test.mjs` test frontend modules, not the backend.

### The only frontend source edits

| File | Change |
|---|---|
| `src/services/previewBackend.js` | **New.** The temporary placeholder (see §7) |
| `src/api/client.js` | `fetch` → `send`, which is `previewFetch` in preview mode; removed the "start npm run dev:api" offline message |
| `src/api/witnesstrace.js` | Default `witness` client uses `previewFetch` in preview mode (`createWitnessClient` itself is unchanged) |
| `src/App.jsx` | Ready gate also passes in preview + witness mode; the existing `.alert` banner says "Preview mode · No backend connected"; `EngineOffline` copy no longer tells users to run removed scripts |
| `src/auth/AuthPage.jsx` | No auto-redirect in preview mode; the existing offline notice explains that there is no backend and links to `/app` |
| `src/landing/EditorShowcase.jsx`, `LiveDemo.jsx`, `LandingNav.jsx`, `src/pages/WitnessTools.jsx` | One copy string each: removed instructions to run `npm run dev` or install `backend/requirements-speech.txt` |

No layout, class names, styles or component structure changed.

## 6. Validation results (Step 7)

| Check | Command / method | Result |
|---|---|---|
| Dependencies install | `cd frontend && npm ci` (from a clean `node_modules`) | ✅ Installs. `npm audit` reports 6 moderate advisories in the ESLint dev toolchain (`minimatch` via `@eslint/eslintrc`). These were already present in the unchanged lockfile and are not fixed here |
| Lint | `npm run lint` | ✅ 0 problems |
| Build | `npm run build` | ✅ Succeeds; CSS hashes identical to the pre-migration build |
| Unit tests | `npm test` | ✅ 15/15 pass: the 11 original adapter/wallet tests and 4 new preview-mode tests |
| Routes render | Headless Chromium on `vite preview`: `/`, `/login`, `/register`, `/app#/workspace`, `#/new`, `#/library`, `#/compare`, `#/settings`, unknown hash route | ✅ Every route renders its page (sidebar with 5 nav items, topbar, page content); unknown routes fall back to Workspace; **0 console errors, 0 page errors** |
| No old backend calls | The same run recorded every browser request | ✅ **0 requests** to `/api/*`, `/wt-api/*` or ports 8000/8021/8022. A unit test also asserts that the default WitnessTrace client never calls `fetch` |
| Responsive | 390 × 844 viewport | ✅ No horizontal overflow; off-canvas sidebar opens from the menu button |
| Theme toggle | Click in topbar | ✅ dark → light |
| Login in preview mode | Submit the form | ✅ Stays on `/login` and shows the "No backend connected…" message; no request is sent |

**Not verified:** pixel-level comparison against the original running app. The original app cannot render its workspace without its backend. Visual preservation is instead shown by the byte-identical CSS and components and by screenshots of every route.

### Broken or unavailable interactions (expected without a backend)

These now show their **existing** error, offline or empty states. They do not fail silently:

- Login, registration and logout (logout returns to `/login`)
- Creating or selecting cases, saving testimony, Codex generation, refinement, the Character Lab schema, reports, PNG/JSON downloads and blockchain integrity verification (witness mode)
- Server-side dictation (`DictateButton` still falls back to the browser Web Speech API where available)
- The landing-page live demo and editor showcase (they show "No backend is connected yet")
- The Image editing and Multi-view iframes, which only render once a case is selected and pointed at `witness-backend/static`, now removed
- **Legacy page set** (`VITE_WITNESSTRACE_LOCAL=0`): `Workspace`, `NewSketch`, `Library`, `Compare` and `Settings` need `/api/catalog`, so in preview mode the shell shows the "Backend not connected" panel instead. The code is preserved, but the default build does not use these pages

### Pre-existing issues observed (not caused by this migration)

- In the **light** theme on mobile, the open off-canvas sidebar is noticeably translucent. Its final background is `rgba(221,235,157,.32) → rgba(250,246,233,.98)` (`styles/app.css` ~line 3395). The CSS is unchanged, so this was already present.
- Domain copy still describes Revelio and a local engine (for example "Local engine offline", "WitnessTrace: OFFLINE", "Codex CLI: UNAVAILABLE", the landing "127.0.0.1" trust claims, and the `backend/.env` snippet in the legacy `Settings` page). These are rebranding items, so they were left alone.

## 7. Temporary mock data

There is **one** placeholder module: `frontend/src/services/previewBackend.js`. It is marked `TEMPORARY` at the top of the file.

| What it does | What it does not do |
|---|---|
| `previewMode` is on unless `VITE_BACKEND_ENABLED=1` | It returns no fake records, metrics, KPIs, health or statuses |
| `GET …/auth/me` → `{ user: { id: 'preview', name: 'Preview user', email: 'preview@localhost', preview: true } }` so `/app` can be opened | It does not accept credentials or simulate login |
| Every other call → `503 { detail: "No backend connected…", preview: true }` | It never calls the network |

Because health returns 503, the sidebar, topbar and Settings honestly show **offline**, KPI tiles show `—`, and lists show their empty states.

**To remove it:** delete the file and its two imports. The steps are listed in [`backend/README.md`](../backend/README.md).

## 8. Remaining frontend/backend integration points

These are what the new backend (or a frontend refactor) has to satisfy or replace:

| Integration point | File(s) | Notes |
|---|---|---|
| Generic request helper, `ApiError`, 401 → `/login` | `src/api/client.js` | Keep. It is domain-neutral |
| Auth: `me`, `login`, `register`, `logout` | `client.js`, `App.jsx`, `AuthPage.jsx`, `AppContext.jsx` | `App` requires `me()` before rendering `/app` |
| Boot gate: `health` + `catalog` | `App.jsx` (`ready`), `BootScreen.jsx`, `AppContext.jsx` (30 s health poll) | Redefine for AggregateX (MITIGATA risk R5) |
| Domain endpoints (sketches, traits, render, stats, activity, storage, speech) | `client.js` `api.*`; used by `pages/*`, `components/sketch/*`, `landing/*` | Revelio-specific; replace per domain |
| WitnessTrace client and job polling | `src/api/witnesstrace.js`, `state/useWitnessCases.js` | `createWitnessClient` and `pollJob` are a good **template** for AggregateX jobs |
| Hard-coded `/wt-api/...` URLs | `pages/WitnessTools.jsx` (iframes, downloads), `components/integrity/BlockchainIntegrity.jsx` | Inert until a case record exists; remove when witness pages are replaced |
| Header and status UI bound to the old domain | `Sidebar.jsx`, `Topbar.jsx` (`activeCase` chip), `WitnessSettings` | Rebind to AggregateX health and tenant context |

## 9. How to run the preserved frontend

```bash
cd frontend
npm ci
npm run dev       # http://127.0.0.1:5182  →  /, /login, /register, /app
npm run build     # → frontend/dist
npm run preview   # serve the production build on :5182
npm run lint
npm test
```

There is nothing else to start. Open `/app` directly to browse the workspace in preview mode.

## 10. Recommended next steps for AggregateX AI

1. **Fix the git remote first.** `git remote rename origin upstream`, then add the AggregateX repository as `origin`. Until then, do not push.
2. **Write the requirements and the API contract.** This covers tenants, users and roles; data sources and ingestion; aggregation and query model; analytics and AI features; and the job contract. Decide the tenancy model (the old code had none) before designing the schema.
3. **Rebrand the frontend** in its own phase, changing copy and assets but not layout: `package.json` name, `index.html` title and meta, `main.jsx` titles, `NAV` + `TITLES`, Sidebar/Topbar status text, BootScreen labels, landing copy, logo PNGs.
4. **Choose one page set.** Retire either witness mode or legacy mode (MITIGATA risk R6). Then map the AggregateX screens (overview dashboard, data sources, aggregations, reports, tenant settings) onto the existing layouts, using the mapping in MITIGATA §7.1.
5. **Fill the UI gaps deliberately.** The frontend has no data-table component and no chart library (MITIGATA §2.7, §2.9, R17). An analytics platform will need both. Choose and justify them, with exact pinned versions, before building dashboards.
6. **Build the backend** in `backend/`, starting with health, auth and tenancy. Add infrastructure (databases, queues, stream or batch processing) only when a requirement calls for it.
7. **Connect the frontend:** add the Vite proxy, set `VITE_BACKEND_ENABLED=1`, delete `previewBackend.js`, and add one `src/api/<domain>.js` module per domain.
8. **Restore deployment** (Dockerfile or Render) for the new stack. The old ones are recoverable from the tag for reference.
9. Optionally rename the API folders to match the suggested layout: `src/api` → `src/services`, `src/state` → `src/hooks`, shell → `src/layouts`. This was deliberately **not** done now, to avoid churning working imports during cleanup.

## 11. Recovery

```bash
git checkout pre-aggregatex-cleanup -- backend witness-backend docker Dockerfile docker-compose.yml render.yaml scripts
tar -xzf .legacy-runtime-backup/revelio-backend-data-2026-10-31.tar.gz -C backend   # restores backend/data
```
