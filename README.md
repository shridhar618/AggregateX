<img src="src/assets/brand/logo-wordmark.png" alt="Revelio" height="64" />

# Revelio + WitnessTrace AI

The default application combines Revelio's React interface with WitnessTrace's FastAPI/SQLite backend and existing authenticated Codex CLI generation pipeline. It includes the 45-attribute Character Lab, immutable testimony/revisions, refinement, comparison, Digital Sketchpad, enhancement, reviewed 2D multi-view, case library and persisted PDF/JSON/PNG exports.

```bash
npm ci
python3 -m venv witness-backend/.venv
witness-backend/.venv/bin/python -m pip install -r witness-backend/requirements-test.txt
npm run dev
```

Open **http://127.0.0.1:5182/register** or `/login`. The launcher uses loopback ports **5182 / 8021 / 8022**, refuses occupied ports and stores runtime data outside Git. AI generation requires the existing authenticated Codex CLI; it never falls back to the procedural renderer or another provider.

### Run with Docker

One container runs the React build (nginx), the Revelio gateway and WitnessTrace. Only port 8080 is exposed, bound to localhost.

```bash
docker compose up -d --build     # first build takes a few minutes
docker compose logs -f           # follow logs
docker compose down              # stop (data is kept)
```

Open **http://127.0.0.1:8080/register**. Cases, accounts and images persist in the `revelio-data` volume. Compose mounts your signed-in `~/.codex` for AI generation (run `codex login` on the host first, or remove that volume line to run without it).

| Build argument | Default | Effect |
|---|---|---|
| `INSTALL_CODEX` | `1` | `0` leaves out Node and the Codex CLI (smaller image; no AI generation) |
| `CODEX_VERSION` | `latest` | Pin the Codex CLI version |
| `WHISPER_MODEL` | `base.en` | Local speech-to-text model baked into the image (e.g. `small.en` for better accuracy, `base` for other languages) |

Example: `docker compose build --build-arg WHISPER_MODEL=small.en`. The image is about 1.8 GB with Codex and the speech model. Codex generation inside the container has not been verified with a real generation; Codex's own sandbox may need adjusting there.

### Voice dictation

Every description field has a **Dictate** button: Revelio description, guided observations, multi-witness accounts, refinement, and WitnessTrace testimony, clarification and refinement instructions.

- **Local transcription (default in Docker):** press *Dictate*, speak, press *Stop*. The recording is transcribed on this machine by [faster-whisper](https://github.com/SYSTRAN/faster-whisper) and appended to the field. Audio never leaves the machine, works offline, and works in any browser with a microphone. Recordings are capped at 3 minutes.
- **Browser fallback:** when the server lacks the speech package (e.g. `npm run dev` without it), the button uses the browser's Web Speech API with live text. That sends audio to the browser vendor's cloud service and only works in Google Chrome, Edge and Safari.

To enable local transcription outside Docker:

```bash
witness-backend/.venv/bin/python -m pip install -r backend/requirements-speech.txt
```

The model (about 140 MB for `base.en`) downloads on first use. Set `REVELIO_WHISPER_MODEL` to choose another one.

See the [startup and rollback guide](docs/integration/STARTUP_GUIDE.md), [final integration report](docs/integration/FINAL_INTEGRATION_REPORT.md), [feature parity](docs/integration/FEATURE_PARITY.md), and [security review](docs/integration/SECURITY_REVIEW.md). Local integration is tested; remote publication remains gated by owner remediation of private artifacts already in b history. This is a local shared collection, not a public multi-tenant deployment.

## Legacy Revelio design reference

The original product description, screenshots, renderer/provider notes and historical commands below are retained as reference for explicit legacy mode (`VITE_WITNESSTRACE_LOCAL=0`). Use the linked startup guide for the default integrated app; the historical port-8000/provider instructions below are not its startup path.

**From Witness Description to Forensic Sketch.**

Revelio is an offline-first workstation for AI-assisted facial composite generation. An operator converts a witness's verbal description into an editable, structured facial profile. The profile then renders as a monochrome forensic-style composite. The operator can refine it, compare revisions and export it with a printable report.

> **Investigative assistance only.** A generated composite is not proof of identity, does not identify anyone automatically, and must never be presented as evidence that a particular person committed a crime. Revelio performs no face recognition and no identity matching.

![Revelio landing page](docs/screenshots/landing.png)

---

## The problem

Building a facial composite from a verbal description is slow. Witnesses remember features unevenly, contradict themselves, and hedge. Separate accounts from different witnesses rarely agree. Most tools either demand a complete description or fill in the gaps silently with invented detail.

## What Revelio does

| | |
|---|---|
| **Description → structured profile** | Deterministic, local extraction of about 20 facial traits plus distinctive marks. Unmentioned traits stay **unknown**. Contradictions are flagged and left **unresolved**. Hedged statements (“maybe”, “I think”) are marked **uncertain**. “I don’t remember his eyes” is recorded as an explicit unknown. |
| **Real offline composite renderer** | A procedural vector renderer draws the face from the profile: face shape, jaw, chin, hairline, hair, brows, eyes, nose, mouth, ears, facial hair, eyewear, age lines and marks. It uses no network, no GPU and no model download. It outputs SVG for live preview and PNG for export, both from the same geometry. |
| **Honest renderer report** | Every result lists which traits were drawn with a neutral default, which are recorded but not drawable (eye colour and skin tone in a monochrome sketch), and which conflicts are pending. Undescribed hair is drawn as a dashed “unspecified” outline, not an invented hairstyle. |
| **Three ways to describe** | A free-text **Description** tab, a **Guided** tab that asks about every trait in turn, and a **Witnesses** tab for separate accounts. Extract with the button or <kbd>⌘/Ctrl</kbd> + <kbd>Enter</kbd>. |
| **Voice dictation** | A *Dictate* button on the description, observations, witness and refinement fields. It transcribes locally with faster-whisper when installed (see [Voice dictation](#voice-dictation)), otherwise it uses the browser's built-in speech recognition. It appends to the text you already have and never submits anything on its own. |
| **Interactive editor** | Trait editor with provenance badges (*Described / Extracted / Manual / Unknown / Conflict / Uncertain*). Sixteen proportion sliders, mark placement, live re-rendering, undo/redo (<kbd>⌘/Ctrl</kbd> + <kbd>Z</kbd>) and reset. A pipeline bar across the top shows the real state of each step: description, trait profile, operator review, composite and revision. |
| **Natural-language refinement** | Commands like “Make the eyebrows thicker”, “Add a small scar on the left cheek” or “Make the jaw narrower” are parsed locally. You review and edit the proposed changes before anything is applied. Requests that are no-ops are reported as such, never faked. |
| **Investigation workspace** | The overview shows saved sketches, drafts in progress, revisions recorded and the last-used generation mode, plus recent sketches, unfinished work, recent activity and provider status. The library supports search by title, sketch ID or description, and you can switch a sketch between draft and final. |
| **Revisions & comparison** | Every save is an immutable revision in SQLite. Compare any two revisions with a drag-to-reveal slider or side by side, alongside a trait-by-trait diff. There are no similarity scores or identity probabilities. |
| **Multi-witness merge** | Compare 2–4 independent accounts. Traits are classified as shared, conflicting, single-source or unmentioned. The operator must resolve every conflict before the combined profile can be applied. |
| **Exports** | PNG, JSON (confirmed traits, unknown traits, conflicts, revision history) and a printable HTML report (print to PDF) with the required disclaimer. |
| **Local accounts** | Register with your name, email and password at `/register`, and log in at `/login`. You need an account to use the workspace and saved sketches. Accounts live in the local database only. See [Accounts](#accounts). |
| **Light and dark themes** | A theme toggle in the workspace top bar and the landing-page nav. Dark uses charcoal with coral accents, and light uses cream with green accents. The choice is remembered in this browser. |
| **Optional AI providers** | A replaceable provider interface. Hosted Gemini is **off by default** and configured on the backend only. A local diffusion model is detected and documented, but not shipped (see below). AI output is always labelled AI-generated, and failures never fall back silently. |

### Screenshots

| Workspace overview (`/app`) | New sketch editor (`/app#/new`) |
|---|---|
| ![Workspace](docs/screenshots/workspace.png) | ![New sketch](docs/screenshots/new-sketch.png) |
| **Light theme · workspace** | **Light theme · editor** |
| ![Workspace, light theme](docs/screenshots/workspace-light.png) | ![Editor, light theme](docs/screenshots/new-sketch-light.png) |
| **Landing · live demo** | **Landing · editor showcase** |
| ![Landing live demo](docs/screenshots/landing-demo.png) | ![Landing editor showcase](docs/screenshots/landing-editor.png) |
| **Compare revisions** | **Library** |
| ![Compare](docs/screenshots/compare.png) | ![Library](docs/screenshots/library.png) |
| **Settings & providers** | **Landing · light theme** |
| ![Settings](docs/screenshots/settings.png) | ![Landing, light theme](docs/screenshots/landing-light.png) |

Procedural composites generated from eight different descriptions. The bottom-left one has no hair description, so its hair is drawn as “unspecified”:

![Procedural composites](docs/screenshots/composites.png)

---

## Architecture

```mermaid
flowchart LR
  subgraph Browser["Browser · React 19 + Vite"]
    UI["Workspace · New Sketch · Library · Compare · Settings"]
  end
  subgraph Engine["Local engine · FastAPI on 127.0.0.1:8000"]
    API["/api routes<br/>Pydantic validation"]
    EX["Trait extractor<br/>(deterministic)"]
    RF["Refinement parser"]
    MG["Multi-witness merge"]
    REG["Provider registry"]
    OFF["Offline procedural renderer<br/>SVG + Pillow PNG"]
    LOC["Local model<br/>(detection only)"]
    HOST["Hosted Gemini<br/>(opt-in, server-side key)"]
    DB[("SQLite<br/>+ PNG/SVG files")]
  end
  UI -- "/api (Vite proxy)" --> API
  API --> EX & RF & MG & REG
  REG --> OFF & LOC & HOST
  API --> DB
  HOST -. "only if configured<br/>and selected" .-> G["Google Gemini API"]
```

```
backend/
  app/
    main.py              FastAPI app, CORS, error mapping (no secrets in errors)
    config.py            Environment-based settings (+ backend/.env loader)
    catalog.py           Trait catalog — single source of truth for options & renderability
    schemas.py           Pydantic models and validation
    database.py          SQLite (stdlib) schema and helpers
    api/                 auth.py · system.py · traits.py · sketches.py · speech.py
    services/            auth_service · trait_extractor · procedural_renderer · refinement_service
                         merge_service · sketch_service · report · uploads · speech (local Whisper)
    providers/           base · offline_provider · local_provider · hosted_provider · registry
  tests/                 76 pytest tests
src/
  main.jsx             Route switch: / → landing page, /app → workspace (separate lazy bundles)
  auth/                  Login and registration pages
  landing/             Landing page (Lumora-inspired); reuses the API client, renderer and CompareSlider
  api/client.js          API client (no credentials ever pass through the browser)
  state/AppContext.jsx   Catalog, engine status, toasts, preferences, active case
  components/            brand · shell (sidebar, top bar, boot screen) · sketch (viewer, editor,
                         refine, merge, pipeline…) · ui (dictation, theme toggle, modals…)
  lib/                   router · nav · format · theme
  pages/                 Workspace · NewSketch · Library · Compare · Settings
public/landing/          Hero sketches (demo-r1/r2) and the pencil reference set in sketches/
scripts/                 run-api.mjs · dev-all.mjs · render-landing-assets.py
```

**Technology:** React 19, Vite 8, plain CSS design system with dark and light themes (Syne for display type, Inter for text, IBM Plex Mono for data), FastAPI, Pydantic 2, SQLite, Pillow and pytest. The frontend adds no new dependencies. Animations are CSS keyframes, with `requestAnimationFrame` only where needed, and they respect `prefers-reduced-motion`.

---

## Getting started

Requirements: **Node 20+** and **Python 3.11+**.

```bash
# 1. Frontend dependencies
npm install

# 2. Backend virtual environment (about 60 MB, one time)
python3 -m venv backend/.venv
backend/.venv/bin/pip install -r backend/requirements.txt      # Windows: backend\.venv\Scripts\pip

# 3. Run the API and the interface together
npm run dev         # starts the API and the interface together
```

Open **http://127.0.0.1:5173** for the landing page, or **http://127.0.0.1:5173/register** to create an account and open the workspace. The workspace boot screen checks the local engine. If the engine isn't running, you'll see instructions instead of a broken UI.

| Route | What it is |
|---|---|
| `/` | Marketing landing page with a live demo running on the real procedural renderer (no account needed) |
| `/register` · `/login` | Create a local account or log in |
| `/app` | The Revelio workspace (`/app#/new`, `/app#/library`, `/app#/compare`, `/app#/settings`). Redirects to `/login` when you're not logged in, then returns you to the page you asked for. |

Old links such as `/#/library` redirect to `/app#/library`. For static hosting, serve `index.html` for `/app` as an SPA fallback. Vite's dev and preview servers already do this.

Run the pieces separately if you prefer:

```bash
npm run dev:api     # FastAPI on http://127.0.0.1:8000 (docs at /docs)
npm run dev:web     # Vite only, on http://127.0.0.1:5173 (proxies /api to the engine)
```

### Quality checks

```bash
npm run lint        # ESLint
npm run build       # production build
npm run test:api    # backend pytest suite (76 tests)
```

### Offline use

After installation, the whole core workflow runs with **no network access**: extraction, refinement, merge, rendering, saving, comparison and export. A test (`test_offline_workflow_without_network`) blocks all sockets and runs the workflow. Without internet, the interface falls back from the Google-hosted fonts to system fonts.

Voice dictation also works offline when local transcription is installed (it is in the Docker image). The browser fallback relies on the browser's speech service, which may process audio on a remote server. Typing always works offline.

---

### Landing page

The landing page at `/` opens with a short intro (skip it with <kbd>Esc</kbd> or <kbd>Enter</kbd>; it plays once per browser session and never with reduced motion). It then runs through the hero, a live demo, the editor showcase, features, how it works, privacy and capabilities, pricing and an FAQ. The nav has the same light/dark toggle as the workspace. Its demos are real:

- **Live demo:** a visitor types a fictional description, and the page calls the local engine to extract traits, then shows the closest pencil sketch from a fictional, AI-generated reference set (`public/landing/sketches/`, matched in `src/landing/sketches.js` on facial hair, eyewear, hair and scars). Visitors can change those traits and download the sketch.
- **Editor showcase:** trait buttons that swap the matched sketch, in-page demo revisions and a before/after slider.
- **Hero imagery:** a before/after pair of pencil sketches (`public/landing/demo-r1.webp`, `demo-r2.webp`). `scripts/render-landing-assets.py` would overwrite them with procedural renders, so don't run it unless you want those back.
- **Pricing:** Pro and Team are labelled as proposals. Their buttons open a notice that collects no data, and only implemented features get a checkmark.

If the local engine isn't running, the demos say so and offer a retry. They never fall back to a static image.

## Accounts

Revelio has simple **local** accounts. They protect the workspace on a shared computer. They are not cloud sign-in.

- **What you need to register:** your full name, an email address and a password of 8–128 characters. The email is only a login name. Revelio never sends email, so there is no verification email and no password reset.
- **Storage:** accounts are stored in `revelio.db` next to your sketches. Passwords are stored as salted **scrypt** hashes, using Python's standard library with no new dependencies, and are never logged or returned by the API.
- **Sessions:** logging in sets an `HttpOnly`, `SameSite=Strict` cookie that lasts 7 days. The database stores only a SHA-256 hash of the session token. Logging out deletes the session and clears the unsaved draft in that browser.
- **Failed logins:** a wrong email and a wrong password give the same message, so the login page doesn't reveal which emails are registered. After 5 failed attempts, that email is locked out for 60 seconds.
- **What needs a login:** everything that reads or changes saved data: sketches, revisions, images, exports, reports, stats, activity, storage info and *delete all*. The landing page's demos stay public because they store nothing: health, catalog, trait extraction, refinement, merge and live rendering.
- **Shared library:** all accounts on one machine share **one sketch library**. Accounts control who can open the workspace. They don't keep each person's cases separate.

## Generation modes

| Mode | Default | Runs | Cost | Status in this build |
|---|---|---|---|---|
| **Offline Composite** | ✅ on | This machine | Free | Fully implemented and tested |
| **Local AI Model** | off | This machine | Free (hardware) | Detection and documentation only |
| **Hosted AI (Gemini)** | off | Google | **May be billed** | Implemented; tested against a mocked API, **not against a real key** |

Every result shows its method next to the image (*Procedural · not AI* or *AI-generated*). The method is also stored with each revision and printed in reports.

### Optional hosted AI (Gemini)

The key lives **only** on the backend. It is sent in the `x-goog-api-key` header, never in the URL, and it is redacted from any error text.

```bash
cp backend/.env.example backend/.env
# then edit backend/.env:
REVELIO_HOSTED_PROVIDER=gemini
GEMINI_API_KEY=your-key-here
GEMINI_IMAGE_MODEL=gemini-3-pro-image-preview
```

Restart the API. The provider then shows as *configured*. It is not verified until a generation succeeds. Revelio makes no claim that this service is free, so check your own quota and pricing. When used, the prompt is built only from **described** traits, with unknown traits explicitly marked unspecified. An optional reference image is sent with that one request. If the provider fails, you see the real error and a one-click option to save an offline composite instead. Nothing switches over silently.

### Optional local model

A local diffusion model (for example Stable Diffusion 1.5) needs roughly **8 GB of free RAM or unified memory** and **5–10 GB of disk**. That is more than a typical student laptop can spare while running a browser and dev servers, and inference couldn't be tested reliably here. So this build ships **detection only**: Settings reports whether PyTorch, `diffusers` and a model path (`REVELIO_LOCAL_MODEL_PATH`) are present. The provider interface (`backend/app/providers/base.py`) is the place to add it.

---

## Security & privacy

- **Local by default.** The engine binds to `127.0.0.1` and CORS allows only the local dev origins. Offline features make no network requests.
- **No secrets in the frontend.** Provider credentials come from backend environment variables. `.env` and `backend/.env` are git-ignored, and `.env.example` files contain placeholders only.
- **Validated input.** Pydantic validates description length, trait options, slider ranges and IDs. Sketch IDs are pattern-checked, and image paths are resolved inside the data directory only.
- **Safe uploads.** Reference images are checked for type allow-list, magic bytes, size (5 MB by default), dimensions and decompression bombs. They are then re-encoded, which strips EXIF and GPS metadata, used for one hosted request, and **never stored**.
- **No biometric processing.** There is no face detection, recognition, identity matching or sensitive-attribute inference.
- **Local accounts.** You must log in to see saved sketches and exports. Passwords are hashed with scrypt, and session cookies can't be read by page scripts. See [Accounts](#accounts).
- **Deletion.** Delete a single sketch with all its revisions and image files from the Library, or wipe all local data from Settings (type `DELETE` to confirm).
- **Data location.** `backend/data/` holds `revelio.db` and `images/` (override with `REVELIO_DATA_DIR`).
- **Browser storage.** The browser keeps only interface preferences, the theme choice and one unsaved draft (`revelio.*` keys in local storage).
- **Dictation.** With local transcription, audio is sent only to the local engine, transcribed in memory and never stored. With the browser fallback, the browser's speech service may send audio off the device.

These are engineering safeguards for a local demo. They are not a claim of legal compliance or enterprise-grade security.

### Upgrading from VeriSketch AI

The project was previously called VeriSketch AI. Existing installs keep working:

- `VERISKETCH_*` environment variables are still read when the matching `REVELIO_*` variable isn't set.
- An existing `backend/data/verisketch.db` is renamed to `revelio.db` the first time the engine starts.
- Old `VS-…` sketch IDs stay valid. New sketches get `RV-…` IDs.
- Saved browser drafts and preferences are carried over automatically.

## Known limitations

- The procedural renderer is stylised and monochrome. It draws a front-facing composite, not a photorealistic likeness. Eye colour and skin tone are recorded but not drawn.
- Trait extraction is rule-based English. Unusual phrasing may be missed, but missed traits stay **unknown** rather than becoming wrong. The guided questions cover every trait.
- Real hosted generation has not been verified with a working API key.
- Local-only: accounts share one sketch library, and there are no roles, no password reset, no sync and no audit-grade chain of custody.
- Local dictation shows the text after you press *Stop*, not word by word. The browser fallback is unavailable in Firefox, Brave and embedded browser views.

## Future improvements

- Optional local diffusion provider with img2img conditioning from the procedural sketch.
- More feature variants (hair textures, headwear, three-quarter view).
- Multilingual extraction and witness-interview scripts.
- Signed, tamper-evident export bundles with a full audit log.

---

Built for HackFest 2026 by team SSDNexus (T1-20).
