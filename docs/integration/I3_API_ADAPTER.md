# I3 API adapter and authentication boundary

Scope: the existing Revelio React application remains primary. A local-only, opt-in case/description/generation slice is implemented; no I4 tools are ported. Baseline: I2 `333f824b5d87e7e4b8fd47133c23a1fbc9c8978c`.

## Architecture and security

Browser `/app` → existing real Revelio session gate → React `src/api/witnesstrace.js` → same-origin `/wt-api` Vite proxy → Revelio FastAPI `witness_gateway.py` → fixed loopback WitnessTrace service → unchanged existing Codex worker/store.

The gateway reuses `require_user` and the real HttpOnly SameSite=Strict session cookie, not a synthetic user. Every gateway operation including health, image and download requires a session. Cookies/authorization are never forwarded to WitnessTrace. Auth service outage now shows a sign-in retry screen rather than rendering the app without a verified user. Existing `/api` authentication and legacy functionality remain available; no provider substitution occurs in the WitnessTrace flow.

`WITNESSTRACE_GATEWAY_TARGET` must explicitly select `http://127.0.0.1:<port>`; protected ports 8000/8001, external hosts and URL credentials/paths are rejected. Gateway paths/methods have a narrow I3 allowlist. JSON is mandatory for mutations; cross-origin browser mutations are rejected. Replies are no-store, errors do not reveal proxy internals. Gateway timeout is 20 seconds; this is submission/poll request timeout, not Codex's 600-second worker deadline. A separate `backend/requirements-integration.txt` records the httpx dependency.

This is **not public-deployment security**. The independently running WitnessTrace port remains unauthenticated and must bind to 127.0.0.1 with isolated synthetic runtime storage. Signed-in local users share this one collection; no per-user tenancy is claimed. Vite must bind to loopback too. Do not expose either port through forwarding/tunnels. OWNER-SEC-01 and dependency remediation DEP-01 remain open before shared/public delivery.

## Verified request mappings

Gateway prefix `/wt-api` preserves the exact upstream paths below.

| Adapter operation | Upstream request | Response / use |
|---|---|---|
| health | GET `/api/health` | codex_installed boolean; installation is not quota/tool readiness |
| listCases | GET `/api/cases` | bare CaseSummary array, real UUIDs |
| createCase | POST `/api/cases` `{title,synthetic:true}` | full persisted Case; UI explicitly creates synthetic cases |
| getCase | GET `/api/cases/{id}` | revision, frozen_at, statements, draft, versions, jobs, selected version |
| freeze | POST `/api/cases/{id}/freeze` `{revision,text}` | immutable exact original; 10–1800 chars, optimistic revision |
| clarify | POST `/api/cases/{id}/clarifications` `{text,source}` | source operator/witness; append-only Case response |
| preview | POST `/api/cases/{id}/prompt-preview` persisted Draft | exact generated description/style and over_limit flag; no truncation |
| submitGeneration | POST `/api/generate` `{description,style,case_id,case_revision,workspace:'text'}` | accepted Job, not image success |
| getGenerationStatus | GET `/api/jobs/{job_id}` | real working/complete/failed and persisted message |
| getRevision | GET canonical Case, find owned version ID | no invented revision endpoint or RV identifiers |
| imageUrl | GET `/images/{version.id}` | only the canonical returned same-service image path is accepted |
| downloadUrl | GET `/api/cases/{case}/versions/{version}/export.png` | existing case-owned normalized PNG attachment |

No arbitrary URL/base override is allowed in the browser adapter: same-origin `/wt-api` is the development base. Request/response shapes are based on the I2 inventory and actual handlers, not Revelio sketches. The gateway deliberately does not expose Lab/refine/edit/enhance/multiview/report operations in I3.

## State, lifetime and errors

`useWitnessCases` is consumed by the existing AppProvider; there is no second global context/database. It owns cases, current Case, backend health, job and errors. Only the selected case ID is persisted in browser storage (`revelio.witness.case`), not witness testimony. On refresh it reads the canonical Case and resumes polling an existing working job. The provider survives hash navigation; unmount aborts browser polling only. Changing cases aborts old polling and uses an epoch to discard stale results. Studio input remounts for each selected case so an unsaved description is not transferred between cases.

A ref lock blocks duplicate UI operations before React state updates. Before submission the client refreshes durable jobs and checks prompt budget; only an explicit button starts generation. The adapter never retries a POST automatically. Ambiguous acceptance/network loss instructs the user to reconnect and inspect existing jobs. There is no backend cancellation endpoint and none is invented.

Polling is every 1.5 seconds, indeterminate and bounded at 660 seconds. Each request is separately bounded at 15 seconds. working, accepted/submitting, complete-verification and failed are distinct. Completion refreshes the Case and requires the job's saved revision; only saved version URLs enter the viewer. Previous saved images remain during work/failure. Missing images produce a visible viewer error; zoom/Fit/download retain the original viewer controls. Variable image proportions use containment in scoped integration CSS.

The adapter checks IDs, Case/job/list/health response shapes and canonical image URLs. HTTP detail arrays become field messages; 401 asks for sign-in, network/timeout errors ask for reconnect, malformed results fail visibly. External AbortSignal cancels requests and polling without resubmitting. No fake progress percentage is shown.

## Local startup (three separate terminals)

Use fresh external synthetic storage directories, not original project data. Check ports first. Install the existing WitnessTrace lock/test environment per I2 and `backend/requirements-integration.txt` in the Revelio environment if needed. The verification uses the WitnessTrace venv for both services, and the original Revelio suite is additionally run with its original environment.

```bash
# Terminal 1: explicit external paths; start.sh binds 127.0.0.1:8022
export WITNESSTRACE_DATA_DIR="$HOME/.local/share/revelio-i3-synthetic/data"
export WITNESSTRACE_OUTPUTS_DIR="$HOME/.local/share/revelio-i3-synthetic/outputs"
export WITNESSTRACE_WORK_DIR="$HOME/.local/share/revelio-i3-synthetic/work"
./witness-backend/start.sh

# Terminal 2: isolated account DB and authenticated gateway
REVELIO_DATA_DIR="$HOME/.local/share/revelio-i3-synthetic/accounts" \
WITNESSTRACE_GATEWAY_TARGET=http://127.0.0.1:8022 REVELIO_HOSTED_PROVIDER= \
witness-backend/.venv/bin/python -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8021

# Terminal 3: existing /api and new /wt-api are unambiguous
REVELIO_API_URL=http://127.0.0.1:8021 REVELIO_GATEWAY_URL=http://127.0.0.1:8021 \
VITE_WITNESSTRACE_LOCAL=1 npm run dev:web -- --host 127.0.0.1 --port 5182 --strictPort
```

Open `http://127.0.0.1:5182/register`, register a local synthetic account and open `/app#/new`. The mode is opt-in at Vite build/start time; legacy mode remains available. Do not use default `npm run dev` for this isolated phase because its legacy API launcher targets 8000. The `/api` default remains unchanged for existing users; isolated commands explicitly override it.

## Backend preservation

No files in `witness-backend/` changed in I3: command/model/provider/output validation/case schema and storage are preserved. Only the existing Revelio backend gains the narrow authenticated proxy router. Full Lab, preferred/selected-version UI, Library, Compare, refinement, Sketchpad, Enhance, Multi-view and reports remain I4 work; legacy screens are labelled as disconnected from WitnessTrace.
