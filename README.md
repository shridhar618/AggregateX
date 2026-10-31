# AggregateX AI

Intelligent multi-tenant analytics and aggregation platform.

> **Status: migration in progress.** The frontend is the original UI, preserved unchanged. The previous backend has been removed and the AggregateX backend has **not** been implemented yet. The app runs in **preview mode**: every page renders and navigates, but no data is loaded or saved.

```
frontend/   React 19 + Vite 8 single-page app (landing, auth pages, workspace)
backend/    Reserved for the AggregateX backend (README only)
docs/       MITIGATA.md (codebase reference), MIGRATION_REPORT.md, legacy/ (Revelio-era docs)
```

## Run the frontend

```bash
cd frontend
npm ci
npm run dev        # http://127.0.0.1:5182  (/, /login, /register, /app)
npm run build      # production build → frontend/dist
npm run lint
npm test           # node --test unit tests for the API adapters
```

See [`docs/MIGRATION_REPORT.md`](docs/MIGRATION_REPORT.md) for what was removed, what was preserved and the recommended next steps.
