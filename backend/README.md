# AggregateX AI — backend (not implemented yet)

This folder is reserved for the **AggregateX AI** backend: the intelligent multi-tenant analytics and aggregation API.

It is intentionally empty. The previous Revelio API (`backend/app`, FastAPI) and the WitnessTrace service (`witness-backend/`) were removed in the cleanup phase. See [`docs/MIGRATION_REPORT.md`](../docs/MIGRATION_REPORT.md) for what was removed and how to recover it (git tag `pre-aggregatex-cleanup`).

## Contract the existing frontend expects

The frontend (`frontend/`) currently runs in **preview mode** and makes no API requests. When this backend exists, it will connect through `frontend/src/api/client.js` (base `/api`). The frontend already depends on these shapes:

| Need | Current frontend expectation |
|---|---|
| Session check | `GET /api/auth/me` → `{ user: { id, name, email } }`; `401` redirects to `/login` |
| Login / register / logout | `POST /api/auth/login`, `/api/auth/register`, `/api/auth/logout` |
| Health (polled every 30 s) | `GET /api/health` → at least `{ status, version }` |
| Errors | JSON `{ "detail": "<message>" }` |
| Long-running jobs | `202 { job_id, status: "working" }` then poll `GET …/jobs/{id}` → `working \| complete \| failed` |

These are the existing frontend's expectations. They are not a design decision for AggregateX. The backend design phase may change them, provided the matching frontend clients change too.

## To connect the frontend once this exists

1. Add a dev proxy for `/api` in `frontend/vite.config.js`.
2. Build or run the frontend with `VITE_BACKEND_ENABLED=1`.
3. Delete `frontend/src/services/previewBackend.js` and its two imports (`src/api/client.js`, `src/api/witnesstrace.js`).
