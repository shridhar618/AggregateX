# I1 frontend API dependencies

Scope: existing Revelio React contracts at main base `f89093e`; I1 does not implement WitnessTrace adapters. Source: `src/api/client.js`, all page consumers, AppContext, landing EngineProvider, and original FastAPI schemas/routes. Browser evidence exercises the real Revelio reference API with synthetic procedural sketches.

## State ownership and routes

| Owner | State and lifetime | Consumers / later change |
|---|---|---|
| `src/main.jsx` | Pathname chooses landing, login/register or App; global persisted theme; old /#/ routes redirect | Keep entry surfaces; preserve authentication and SPA deep links |
| `App.jsx` | auth check, boot steps, offline/retry, sidebar drawer; hash page selection | `/auth/me` must stay real. Boot health/catalog dependencies need case/Lab capability checks |
| `state/AppContext.jsx` | catalog, health/provider map; toast stack and notification log; activeCase label; preferences; user/logout | Replace sketch-only activeCase with persistent selected WitnessTrace case; keep shared UI preferences |
| `pages/Workspace.jsx` | parallel dashboard load; draft snapshot from localStorage | Derive case/revision counts/activity from actual persisted data; no invented totals |
| `pages/NewSketch.jsx` | description/title/mode; history reducer (80 snapshots, 900ms coalescing); profile/baseline; selected sketch/revision; SVG blob preview; save/error; revision note; reference image; panel tabs | Main domain adaptation point. Preserve visual composition and local undo; move persistent case ownership out of this component |
| `DescriptionPanel` / GuidedForm / WitnessMerge | description tab, extraction busy/errors, guided answers/marks, merge conflicts | Frozen testimony must become read-only; corrections are sourced append operations; original multi-witness merge is not a WitnessTrace capability |
| `TraitPanel`, `AdjustPanel` | value updates passed to NewSketch; local showUnknown setting | Render WitnessTrace schema with full 45 attributes/seven groups, Unknown, uncertainty and exact quotes |
| `RefinePanel` | instruction, parsed proposal/selected changes, busy/error | Use WitnessTrace prompt-preview/refine flow and immutable child revision; do not imply guaranteed image-to-image editing |
| `SketchViewer`, `CompareSlider` | local zoom/reveal position; source from props | Keep interactions; image source becomes validated revision URL, variable aspect ratio |
| `Library` / HistoryModal | query, list, rename/status/delete/history dialogs | Use cases/versions; expose only supported mutation operations |
| `Compare` | selected A/B sketch/revision; per-ID cache; reveal/split; changed-only filter | Real version IDs, parent lineage, preferred selection; prevent stale cross-case cache/state |
| `Settings` | storage, wipe dialog, health recheck; preferences in context | Show actual CLI and storage state; remove unsupported providers/delete-all |
| `AuthPage` | form validation, server error/busy, show password, engine availability | Preserve real HttpOnly cookie login; do not fake success or bypass boundary |
| `landing/engine.jsx` | public health/catalog availability | Independent context for landing; adapt truthfully without starting Codex on slider movement |
| `LiveDemo` | input/extraction/profile, render blob, render count | Public procedural demo today; future saved examples or explicit workflow entry must be labelled accurately |
| `EditorShowcase` | seeded profile, local revisions, current SVG URL, comparison | Revisions are in page memory only; not saved case history |

`revelio.theme`, `revelio.prefs`, `revelio.draft` persist in localStorage. Logout clears the browser draft. The selected sketch label is reset when NewSketch unmounts; this must not erase future case selection. Requests use same-origin fetch/cookies; no browser credentials or API keys are sent explicitly.

## Verified current endpoint contracts

Base: `VITE_API_BASE` or `/api`. Paths below are appended to this base. Models come from `backend/app/schemas.py` / route code, not guessed WitnessTrace aliases.

| Client function / consumer | Method/path | Request | Expected response | Loading and error presentation |
|---|---|---|---|---|
| `me`: App/AuthPage | GET `/auth/me` | session cookie | `{user:{id,name,email,created_at}}` | Auth gate; 401 redirects App to login; AuthPage stays form |
| `register`: AuthPage | POST `/auth/register` | `{name,email,password}` | 201 `{user}`, real session cookie | Disabled submit/spinner; field validation, server error; redirect on success |
| `login`: AuthPage | POST `/auth/login` | `{email,password}` | `{user}`, session cookie | Busy/server error; 401 invalid credentials, 429 throttling |
| `logout`: AppContext/AccountMenu | POST `/auth/logout` | none | 204 | Clears draft; redirects login even if logout request fails |
| `health`: context, shell, settings, landing | GET `/health` | none | `{status,app,version,renderer,providers[]}` | Boot steps/status/recheck; offline shell/retry |
| `catalog`: context, landing | GET `/catalog` | none | `{traits[20],adjustments[16],marks,sources,limits}` | Boot/catalog failure; controls unavailable |
| `stats`: Workspace | GET `/stats` | none | `{sketches,drafts,revisions,last_method,last_generated_at,...}` | Skeletons then real values; alert on parallel load failure |
| `activity`: Workspace | GET `/activity?limit=12` | none | `{activity:[{id,kind,message,created_at,...}]}` | Skeleton/empty timeline/alert |
| `storage`: Settings | GET `/storage` | none | `{data_dir,database,images,reference_images_stored}` | Missing storage silently hides details |
| `extract`: DescriptionPanel, landing, showcase | POST `/traits/extract` | `{description}` | `{profile,recognized_count,conflicts,explicit_unknowns,...}` | Busy extraction; inline field error; extraction toast/conflict alerts |
| `merge`: WitnessMerge | POST `/witnesses/merge` | `{descriptions:[string,...]}` | combined `profile`, counts, shared/conflict/single-source results | Busy compare; decisions gate Apply; error field |
| `parseRefine`: RefinePanel | POST `/refine/parse` | `{instruction,profile}` | `{changes[],already[],unrecognized[],message,...}` | Busy Interpret; proposed editable changes, warn/no-op/error |
| `applyRefine`: RefinePanel | POST `/refine/apply` | `{profile,changes}` | `{profile}` | Busy Apply; updates local profile and revision note, no new image revision until Save |
| `render`: NewSketch/LiveDemo/EditorShowcase | POST `/render` | `{profile,caption}` | `{svg,notes,method,method_label,is_ai:false}` | Rendering pill; SVG Blob URL; inline error; last preview retained on error |
| `renderPng`: unsaved viewer/landing | POST `/render.png` | `{profile,caption}` | PNG response blob | Download spinner; toast/inline error |
| `listSketches`: Workspace/Library/Compare | GET `/sketches?q=...` | query optional | `{sketches:[listItem]}` | Skeleton, empty state/search message, alert |
| `getSketch`: NewSketch/Compare/HistoryModal | GET `/sketches/{id}` | URL ID | full Sketch (below) | Load skeleton/error; history modal/error |
| `generate`: NewSketch | POST `/sketches/generate` | `{title,description,profile,mode,note?,reference_image?}` | 201 full Sketch synchronously | Saving spinner, elapsed progress; provider-error/offline-fallback actions |
| `addRevision`: NewSketch | POST `/sketches/{id}/revisions` | `{profile,mode,note?,reference_image?}` | 201 full Sketch synchronously | Same saving states; immutable numbered revision list |
| `updateSketch`: NewSketch/Library | PATCH `/sketches/{id}` | `{title?,status?,notes?}` | full Sketch | Inline edit then toast; error toast |
| `deleteSketch`: Library | DELETE `/sketches/{id}` | none | 204 | Confirm modal/busy; list reload or error toast |
| `deleteAll`: Settings | POST `/data/delete-all` | `{confirm:'DELETE'}` | `{deleted_sketches,...}` | Type-to-confirm modal/busy; toast |
| PNG URL builder: viewer/library/history | GET `/sketches/{id}/revisions/{n}/image.png?download=true` | URL | PNG download (900×1125 procedural source) | Anchor; response errors not rendered by client wrapper |
| image sources | GET same revision `/image.png` (or `/image.svg`) | URL | Raster/SVG | `<img>`; img decoding/loading |
| JSON URL builder: Library | GET `/sketches/{id}/export.json?download=true` | URL | sketch metadata/profiles/revisions/disclaimer JSON | Download link |
| report URL builder: Library | GET `/sketches/{id}/report` | URL | printable HTML report, not PDF | New tab |

Public routes: health/catalog, traits/merge/refine and procedural render. Saved records/stats/activity/storage/deletion/downloads require the original auth dependency. The reference backend is isolated and hosted provider is explicitly disabled. No paid generation was used.

### Core data shapes

- `Profile`: `{traits:{key:{value,source,evidence,certainty,alternatives}},marks:[],adjustments:{key:number},observations}`. 20 keys, 16 adjustment controls. Adjustment range −1..1; source = described/extracted/manual/unknown; certainty = stated/uncertain. Description contract = 10–2000 characters.
- `Sketch`: `{id,title,description,status,notes,created_at,updated_at,revisions,current,revision_count}`. ID format RV/legacy VS-date-hex. Status draft/final.
- `Revision`: `{number,method,method_label,model,is_ai,created_at,change_note,notes,profile,image_url,svg_url}`. Linear numbers and `current`, no parent/preferred metadata in this frontend.
- `listItem`: sketch metadata plus `rev_number`, `method`, `method_label`, `is_ai`, `revision_count`, `thumbnail_url`.
- `Provider`: offline/local/hosted IDs with availability, reason, kind, local/remote flags, supports_reference_image/live_edit and optional model/detection map.
- Error wrapper: `ApiError(status,message,data)`, `isProviderError` uses `provider_error`; **isOffline only tests status 0**, so proxy 502/503/504 do not become auth-page offline notices. AbortError propagates separately. Mid-session non-auth 401 redirects to login. String detail is displayed; non-string validation details become generic status text.

## Required I3 adapter changes — not implemented

| Existing assumption | WitnessTrace requirement | Affected UI |
|---|---|---|
| Save POST returns completed sketch immediately | 202 job handle → poll persisted job → validated image/version → refresh case | NewSketch, Pipeline, viewer, notifications/boot |
| 20 traits / 16 sliders | Full 45 fields, seven groups; shared Text fields plus Lab fields, sourced exact quotes | TraitPanel, AdjustPanel, Guided/input, Compare |
| Editable description on a sketch | Exact frozen original, append-only clarifications and revision-checked drafts | DescriptionPanel, NewSketch, case context |
| RV IDs and numbered revisions | Case UUID and version/job UUID; parent-child history, selected/preferred | Router params, activeCase, Library, Compare, viewer |
| 140ms/120ms/90ms automatic procedural renders | Explicit generate/Update Preview; no Codex calls on controls; stale-preview indicator | NewSketch, LiveDemo, EditorShowcase |
| String SVG converted to blob URL | Actual validated PNG/JPEG/WebP URL from `/images/{job_id}`; retain validation/result semantics | Viewer, thumbnails, downloads, compare |
| 4:5 frame/image assumption | Variable dimensions and object-fit contain; maintain image coordinates | CSS/viewer/compare/cards/editor hosts |
| Local/hosted/offline provider choices | Only original authenticated Codex pipeline; health installation ≠ live tool success | ModeSelector, boot, sidebar, Settings, dashboard |
| Refine changes local profile | Preview prompt then create new immutable image with parent linkage | RefinePanel, revisions, Compare |
| Sketch rename/delete/delete-all exist | Do not offer unsupported case operations | Library/Settings |
| HTML printable report | Existing WitnessTrace PDF/JSON/PNG and provenance/checksum services | Export links/report UI |
| Cookie auth only covers original routes | Reuse real auth and gate WitnessTrace data/images/reports; no fake login | App/AuthPage/client/backend wrapper |
| `/api` only proxy | Same origin API + images + worker/static paths and SPA fallbacks | Vite configuration/production serving |
| No drawing/image-processing workspaces | Preserve Sketchpad/Enhance engines in lifecycle-safe hosts; full Multi-view/report UI | New routed workspaces and shared case selection |

Adapter URL/payload mapping is I3 work; I2 preserves backend first. No API service was added or modified in I1.
