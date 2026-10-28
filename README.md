# VeriSketch AI

**From Witness Description to Forensic Sketch.**

VeriSketch AI is an offline-first workstation for AI-assisted facial composite generation. An operator converts a witness's verbal description into an editable, structured facial profile. The profile then renders as a monochrome forensic-style composite. The operator can refine it, compare revisions and export it with a printable report.

> **Investigative assistance only.** A generated composite is not proof of identity, does not identify anyone automatically, and must never be presented as evidence that a particular person committed a crime. VeriSketch performs no face recognition and no identity matching.

![VeriSketch AI — New Sketch workspace](docs/screenshots/new-sketch.png)

---

## The problem

Building a facial composite from a verbal description is slow. Witnesses remember features unevenly, contradict themselves, and hedge. Separate accounts from different witnesses rarely agree. Most tools either demand a complete description or fill in the gaps silently with invented detail.

## What VeriSketch does

| | |
|---|---|
| **Description → structured profile** | Deterministic, local extraction of about 20 facial traits plus distinctive marks. Unmentioned traits stay **unknown**. Contradictions are flagged and left **unresolved**. Hedged statements (“maybe”, “I think”) are marked **uncertain**. “I don’t remember his eyes” is recorded as an explicit unknown. |
| **Real offline composite renderer** | A procedural vector renderer draws the face from the profile: face shape, jaw, chin, hairline, hair, brows, eyes, nose, mouth, ears, facial hair, eyewear, age lines and marks. It uses no network, no GPU and no model download. It outputs SVG for live preview and PNG for export, both from the same geometry. |
| **Honest renderer report** | Every result lists which traits were drawn with a neutral default, which are recorded but not drawable (eye colour and skin tone in a monochrome sketch), and which conflicts are pending. Undescribed hair is drawn as a dashed “unspecified” outline, not an invented hairstyle. |
| **Interactive editor** | Trait editor with provenance badges (*Described / Extracted / Manual / Unknown / Conflict / Uncertain*). Sixteen proportion sliders, mark placement, live re-rendering, undo/redo and reset. |
| **Natural-language refinement** | Commands like “Make the eyebrows thicker”, “Add a small scar on the left cheek” or “Make the jaw narrower” are parsed locally. You review and edit the proposed changes before anything is applied. Requests that are no-ops are reported as such, never faked. |
| **Revisions & comparison** | Every save is an immutable revision in SQLite. Compare any two revisions with a drag-to-reveal slider or side by side, alongside a trait-by-trait diff. There are no similarity scores or identity probabilities. |
| **Multi-witness merge** | Compare 2–4 independent accounts. Traits are classified as shared, conflicting, single-source or unmentioned. The operator must resolve every conflict before the combined profile can be applied. |
| **Exports** | PNG, JSON (confirmed traits, unknown traits, conflicts, revision history) and a printable HTML report (print to PDF) with the required disclaimer. |
| **Optional AI providers** | A replaceable provider interface. Hosted Gemini is **off by default** and configured on the backend only. A local diffusion model is detected and documented, but not shipped (see below). AI output is always labelled AI-generated, and failures never fall back silently. |

### Screenshots

| Workspace | Before / after |
|---|---|
| ![Workspace](docs/screenshots/workspace.png) | ![Before and after](docs/screenshots/before-after.png) |
| **Compare revisions** | **Library** |
| ![Compare](docs/screenshots/compare.png) | ![Library](docs/screenshots/library.png) |
| **Settings & providers** | **Boot sequence** |
| ![Settings](docs/screenshots/settings.png) | ![Boot](docs/screenshots/boot.png) |

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
    api/                 system.py · traits.py · sketches.py
    services/            trait_extractor · procedural_renderer · refinement_service
                         merge_service · sketch_service · report · uploads
    providers/           base · offline_provider · local_provider · hosted_provider · registry
  tests/                 56 pytest tests
src/
  api/client.js          API client (no credentials ever pass through the browser)
  state/AppContext.jsx   Catalog, engine status, toasts, preferences, active case
  components/            brand · shell · ui · sketch (viewer, editor, refine, merge…)
  pages/                 Workspace · NewSketch · Library · Compare · Settings
scripts/                 run-api.mjs · dev-all.mjs
```

**Technology:** React 19, Vite 8, plain CSS design system (Inter + IBM Plex Mono), FastAPI, Pydantic 2, SQLite, Pillow and pytest. The frontend adds no new dependencies. Animations are CSS keyframes, with `requestAnimationFrame` only where needed, and they respect `prefers-reduced-motion`.

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

Open **http://127.0.0.1:5173**. The boot screen checks the local engine; if it is not running you'll see instructions instead of a broken UI.

Run the pieces separately if you prefer:

```bash
npm run dev:api     # FastAPI on http://127.0.0.1:8000 (docs at /docs)
npm run dev:web     # Vite only, on http://127.0.0.1:5173 (proxies /api to the engine)
```

### Quality checks

```bash
npm run lint        # ESLint
npm run build       # production build
npm run test:api    # backend pytest suite (56 tests)
```

### Offline use

After installation, the whole core workflow runs with **no network access**: extraction, refinement, merge, rendering, saving, comparison and export. A test (`test_offline_workflow_without_network`) blocks all sockets and runs the workflow. Without internet, the interface falls back from the Google-hosted fonts to system fonts.

---

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
VERISKETCH_HOSTED_PROVIDER=gemini
GEMINI_API_KEY=your-key-here
GEMINI_IMAGE_MODEL=gemini-3-pro-image-preview
```

Restart the API. The provider then shows as *configured*. It is not verified until a generation succeeds. VeriSketch makes no claim that this service is free, so check your own quota and pricing. When used, the prompt is built only from **described** traits, with unknown traits explicitly marked unspecified. An optional reference image is sent with that one request. If the provider fails, you see the real error and a one-click option to save an offline composite instead. Nothing switches over silently.

### Optional local model

A local diffusion model (for example Stable Diffusion 1.5) needs roughly **8 GB of free RAM or unified memory** and **5–10 GB of disk**. That is more than a typical student laptop can spare while running a browser and dev servers, and inference couldn't be tested reliably here. So this build ships **detection only**: Settings reports whether PyTorch, `diffusers` and a model path (`VERISKETCH_LOCAL_MODEL_PATH`) are present. The provider interface (`backend/app/providers/base.py`) is the place to add it.

---

## Security & privacy

- **Local by default.** The engine binds to `127.0.0.1` and CORS allows only the local dev origins. Offline features make no network requests.
- **No secrets in the frontend.** Provider credentials come from backend environment variables. `.env` and `backend/.env` are git-ignored, and `.env.example` files contain placeholders only.
- **Validated input.** Pydantic validates description length, trait options, slider ranges and IDs. Sketch IDs are pattern-checked, and image paths are resolved inside the data directory only.
- **Safe uploads.** Reference images are checked for type allow-list, magic bytes, size (5 MB by default), dimensions and decompression bombs. They are then re-encoded, which strips EXIF and GPS metadata, used for one hosted request, and **never stored**.
- **No biometric processing.** There is no face detection, recognition, identity matching or sensitive-attribute inference.
- **Deletion.** Delete a single sketch with all its revisions and image files from the Library, or wipe all local data from Settings (type `DELETE` to confirm).
- **Data location.** `backend/data/` holds `verisketch.db` and `images/` (override with `VERISKETCH_DATA_DIR`).

These are engineering safeguards for a local demo. They are not a claim of legal compliance or enterprise-grade security.

## Known limitations

- The procedural renderer is stylised and monochrome. It draws a front-facing composite, not a photorealistic likeness. Eye colour and skin tone are recorded but not drawn.
- Trait extraction is rule-based English. Unusual phrasing may be missed, but missed traits stay **unknown** rather than becoming wrong. The guided questions cover every trait.
- Real hosted generation has not been verified with a working API key.
- Single-user, local-only: no accounts, sync or audit-grade chain of custody.

## Future improvements

- Optional local diffusion provider with img2img conditioning from the procedural sketch.
- More feature variants (hair textures, headwear, three-quarter view).
- Multilingual extraction and witness-interview scripts.
- Signed, tamper-evident export bundles with a full audit log.

---

Built for HackFest 2026 by team SSDNexus (T1-20).
