# Integrated API mapping — I3 checkpoint

The active adapter is `src/api/witnesstrace.js`; authenticated gateway is `backend/app/api/witness_gateway.py`. The complete verified I3 request/response table, errors, polling and startup commands are in [I3_API_ADAPTER.md](I3_API_ADAPTER.md). The complete preserved upstream inventory remains [I2_BACKEND_API_INVENTORY.md](I2_BACKEND_API_INVENTORY.md).

| React owner | Current domain operations | State/error handling | Status |
|---|---|---|---|
| App / AppProvider | Existing session/me; shared WitnessTrace case/job state | Real login redirect; sign-in-service failure stays outside app | Implemented and browser-tested |
| WitnessWorkspace / CaseControls | Health, list/create/select Case | Live connection, canonical case list/count, errors/reconnect | Implemented and browser-tested |
| WitnessStudio | Freeze exact original, append clarification, prompt preview, submit generation | Explicit button, immutable testimony, ref submission lock, backend revision and prompt budget | Implemented and browser-tested |
| useWitnessCases | Canonical Case + jobs, poll GET job, refresh saved versions | Provider lifetime, selected ID storage, abort polling, stale-result guard, no automatic POST retry | Implemented and browser-tested |
| SketchViewer | Canonical saved image and normalized PNG export | Existing zoom/Fit; scoped flexible layout; image error; prior output retained | Implemented; synthetic and one real output verified |
| Original Library / Compare / Settings | Original Revelio API retained | Explicit disconnected notice in local integration mode | WitnessTrace mapping deferred I4 |
| Full Lab/refinement/Sketchpad/Enhance/Multi-view/Reports | Preserved upstream services only | Not exposed by I3 gateway | Deferred I4 |

There is one WitnessTrace case/revision store. Existing Revelio account storage is reused solely for verified sessions in the integrated path. No RV identifier conversion or second case schema is introduced.
