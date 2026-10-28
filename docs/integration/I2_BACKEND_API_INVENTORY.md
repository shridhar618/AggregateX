# I2 WitnessTrace backend API inventory

Source of truth for future I3 adapter work: imported `witness-backend/` from b `49f63ee4e242efe0c5aa4aef0a524652e75cfd5a`, with only output/work path initialization changed in app.py. All route handlers and models remain unchanged. This document inventories the backend; **no React adapter, new auth boundary or proxy connection was implemented in I2**.

Verified by reading app.py, case_store.py, lab_schema.py and all editing/report stores, extracting the actual running app’s [OpenAPI](evidence/i2/openapi.json), running 54 original pytest tests (+2 relocation tests) and 33 synthetic HTTP checks against port 8022. Response shapes are also recorded without body values in [server-checks.json](evidence/i2/server-checks.json). The verifier uses an explicitly fake CLI, never live AI. No original records or images were inspected through these routes.

## Cross-cutting contract

- Independent reference origin `http://127.0.0.1:8022`. API paths begin `/api`; images are `/images/{job_id}` and static engines `/static/...` (not under `/api`). No permissive CORS or React proxy change was introduced.
- **No authentication exists in this preserved backend.** Case-scoped ownership checks validate record relationships, not user ownership. Global case lists/jobs/images are not tenant-isolated. This is localhost-only preservation, not a safe public service. The architecture decision requires real Revelio cookie enforcement during I3; do not fake successful login.
- Case, version/job, request key, layout and report IDs are 32 lowercase hexadecimal UUID strings; helper/model validation rejects invalid IDs (often 404 for lookup, 422 for request-model patterns). Use actual IDs returned, not RV sketch IDs or display revision numbers.
- JSON models generally inherit `Strict(extra="forbid")`; GenerateRequest inherits plain BaseModel instead. Validation errors are 422 `{detail:[{loc,msg,type,...}]}`. Domain HTTP errors are `{detail:string}`. Storage/service failures can be 500; selected local-save/report wrappers return 503. Normalize array/string detail in I3 without exposing records/CLI output.
- All timestamp fields come from persisted UTC ISO timestamps. Original Unicode/whitespace is preserved. Original testimony max length 1800; complete generated prompt budget 2500. No silent truncation. Unknown fields have null value and confidence unknown.
- This API offers no case delete/rename, no user/session routes, no Revelio catalog/trait-extract/procedural-render contracts, no job cancel and no progress percentage/streaming transport.

## Every explicit application endpoint

Auth is none for every row. Isolation details describe case/version relationships only. JSON uses the named shapes defined below. Status is 200 unless specified.

| Method | Exact route | Input shape | Successful output | Authentication / case isolation | Error behavior | I3 considerations |
|---|---|---|---|---|---|---|
| `GET` | `/` | `—` | HTML of the original preserved standalone workbench | No auth | File missing → server error | Reference backend verification only; not the integrated React entry |
| `POST` | `/api/generate` | `GenerateRequest` | 202 Job | No auth; validates case revision/freeze when case_id supplied | 409 busy, unresolved DB job, stale case or unfrozen witness; 422 prompt/input; 404 case | Explicit submission; persist job_id and poll; never auto-submit on sliders |
| `GET` | `/api/jobs/{job_id}` | `UUID path` | Job | No auth; global ID lookup | 404 invalid/unknown job | Poll working/complete/failed; persisted messages are safe classifications |
| `GET` | `/images/{job_id}` | `UUID path` | Original validated image bytes, PNG/JPEG/WebP | No auth; global version/job ID, checksum/freeze/path validation | 404 invalid/missing image; 409 frozen-account or integrity failure | Use the returned URL; global IDs do not establish user tenancy |
| `GET` | `/api/health` | `—` | {codex_installed:boolean, generated_images_directory:string, message:string} | No auth | Ordinary service failures may be 500 | Installation only, not login/quota/tool success; directory is a local path |
| `GET` | `/api/cases` | `—` | CaseSummary[] (bare array) | No auth; entire local collection | Storage failures may be 500 | Not {cases:...}; no built-in search, rename or delete endpoint |
| `POST` | `/api/cases` | `NewCase` | 201 Case | No auth | 422 blank/invalid title | Returns real case ID, empty original statement and complete Unknown draft |
| `GET` | `/api/cases/{case_id}` | `UUID path` | Case | No auth; case lookup; unfrozen witness face history withheld | 404 invalid/unknown case | Canonical refresh after save/job/edit; selected/preferred stored server-side |
| `PUT` | `/api/cases/{case_id}` | `SaveCase` | Case | No auth; optimistic revision and quote/freeze checks | 404 case; 409 stale revision or original frozen; 422 attribute/quote | Persist draft; optional original allowed only before freeze; retain exact text |
| `POST` | `/api/cases/{case_id}/freeze` | `Freeze` | Case | No auth; atomic revision/freeze check | 404 case; 409 already frozen/stale; 422 short text or quote | Exact Unicode/whitespace retained; first account read-only afterward |
| `POST` | `/api/cases/{case_id}/clarifications` | `Clarification` | 201 Case | No auth; requires witness original frozen unless synthetic | 404 case; 409 unfrozen; 422 blank text/source | Append separately sourced notes, refresh incremented revision |
| `GET` | `/api/lab-schema` | `—` | {groups:[{id,label,short,icon,fields:Field[]}]} | No auth | Ordinary service failures | 45 fields/seven groups; drives all controls; field details below |
| `POST` | `/api/cases/{case_id}/prompt-preview` | `Draft` | PromptPreview | No auth; case/freeze/exact witness quote checks | 404 case; 409 unfrozen/pending note; 422 invalid draft/short original | Returns over_limit instead of truncating; does not persist draft or start job |
| `POST` | `/api/cases/{case_id}/selection` | `Selection` | Case | No auth; version must belong to case; verifies image | 404 case/wrong-case version; 409 image integrity | preferred=true changes preferred only; default changes selected |
| `POST` | `/api/cases/{case_id}/refinement-preview` | `Refinement` | PromptPreview + {mode:"prompt_regeneration"} | No auth; parent must belong to case, image/freeze/quotes checked | 404 case/parent; 409 state/integrity; 422 instruction/draft | reviewed_prompt is not required yet; no generation or persistence |
| `POST` | `/api/cases/{case_id}/refine` | `Refinement` | 202 Job (same job for identical request_key replay) | No auth; case revision/parent/frozen checks | 404 ownership; 409 busy/stale/key collision/reviewed prompt changed; 422 budget/input | Submit exact preview description as reviewed_prompt; keep request_key across retries |
| `GET` | `/api/cases/{case_id}/versions/{version_id}/sketch` | `UUID paths` | {version_id,project,source_url,modified_illustration} | No auth; owned version and project source within case | 404 wrong case/source/missing image; 409 unfrozen/integrity | Load retained editable operations; source_url points to canonical pixels |
| `POST` | `/api/cases/{case_id}/local-edits` | `SaveEdit` | 201 SaveResult | No auth; parent and project source lineage within case | 404 ownership; 409 unfrozen/key collision; 422 PNG/project/geometry; 503 storage | Creates immutable child; refresh case after response; server validates shape, not full pixel replay |
| `POST` | `/api/cases/{case_id}/imports` | `ImportImage` | 201 SaveResult | No auth; case freeze unless synthetic; consent=true | 404 case; 409 unfrozen/key collision; 422 format/size/consent; 503 storage | Raw upload bytes retained; filename display only; no AI call |
| `GET` | `/api/cases/{case_id}/versions/{version_id}/enhance` | `UUID paths` | {source_id,parent_id,source_url,adjustments,engine} | No auth; owned version and non-destructive source | 404 ownership/missing; 409 unfrozen/integrity | Saved enhancement reopens source + settings, not re-filtered flattened result |
| `GET` | `/api/cases/{case_id}/versions/{version_id}/pixels` | `UUID paths` | Canonical EXIF-oriented RGBA PNG bytes | No auth; owned version and checksum validation | 404 ownership/missing; 409 unfrozen/integrity; 422 decode/budget | Used by real browser engines; differs from raw uploaded original bytes |
| `POST` | `/api/cases/{case_id}/enhancements` | `SaveEnhancement` | 201 SaveResult | No auth; parent/source lineage within case | 404 ownership; 409 frozen/key/integrity; 422 PNG/resize/source; 503 storage | Save committed worker PNG and params; backend does not rerun the RGBA filter algorithm |
| `GET` | `/api/enhance-schema` | `—` | {defaults,controls:[{group,key,label,min,max,step}],presets,engine} | No auth | Ordinary service failures | 11 control entries plus booleans/resize; five real preset parameter sets |
| `POST` | `/api/cases/{case_id}/multiview-preview` | `MultiViewRequest` | PromptPreview + {route,image_reference_used:false} | No auth; owned parent, freeze/quotes/image checked | 404 parent/case; 409 state/integrity; 422 draft | Text-only 2D prompt preview; no source pixels and no new job |
| `GET` | `/api/cases/{case_id}/multiview` | `UUID case path` | {requests:[SheetRequest],route,image_reference_used:false} | No auth; case lookup | 404 case | Completed requests include image_url, sha256, image_format, latest reviewed layout |
| `POST` | `/api/cases/{case_id}/multiview` | `MultiViewRequest` | 202 Job; identical request_key reuses job | No auth; parent/case/revision/freeze checks | 404 ownership; 409 busy/stale/key/reviewed prompt; 422 budget | Explicit 2D sheet generation; poll then fetch history/review layout |
| `POST` | `/api/cases/{case_id}/views/{version_id}/layouts` | `Layout` | 201 ReviewedLayout | No auth; version must be this case’s generated sheet | 404 case/sheet; 409 image integrity; 422 incomplete/overlapping/outside rectangles | Append-only operator review; exactly four unique angles, no assumed automatic crop layout |
| `GET` | `/api/cases/{case_id}/views/{version_id}/layouts/{layout_id}/{angle}.png` | `UUID paths; angle front/left/right/three_quarter` | Reviewed PNG crop download | No auth; sheet/layout/case and both checksums validated | 404 unknown/wrong-case angle/layout; 409 integrity | Use only available reviewed angles; original sheet remains separate |
| `POST` | `/api/cases/{case_id}/reports` | `ReportRequest` | 201 Report; same key replays original bundle | No auth; selected version must belong to case | 404 ownership; 409 key/integrity; 422 font/glyph/image budget; 503 generation/storage | Persisted records only, immutable bundle; do not pass unsaved browser testimony |
| `GET` | `/api/cases/{case_id}/reports` | `UUID case path` | Report[] (bare array) | No auth; case lookup | 404 case | Newest first; records hold original export snapshots |
| `GET` | `/api/cases/{case_id}/versions/{version_id}/export.png` | `UUID paths` | Normalized PNG attachment | No auth; owned version and integrity validation | 404 ownership; 409 decode/integrity; 422 >16MP | Export SHA may differ from raw original; distinguish source/export checksum labels |
| `GET` | `/api/cases/{case_id}/reports/{report_id}/preview` | `UUID paths` | HTML persisted report preview with CSP | No auth; report belongs to case and JSON hash checked | 404 ownership/missing; 409 integrity | Same-origin images; embedded styles allowed; snapshot, not editable case UI |
| `GET` | `/api/cases/{case_id}/reports/{report_id}/{extension}` | `UUID paths; extension pdf/json/png; query inline:boolean=false` | Persisted file; no-store; attachment unless inline | No auth; report belongs to case; file/path/checksum validated | 404 invalid extension/ownership/missing; 409 hash mismatch | Manifest provides exact bytes/SHA/filename; inline supports report image/preview |
| `GET` | `/api/cases/{case_id}/versions/{version_id}/export.json` | `UUID paths` | Fresh ReportSnapshot JSON attachment | No auth; owned selected version and integrity checked | 404 ownership; 409 image integrity; 422 image export budget | Fresh report UUID/timestamp each request; use persisted reports for byte-stable JSON downloads |

Additional framework routes: GET/HEAD `/openapi.json` returns the actual generated schema without authentication; `/docs` and `/redoc` are disabled. The `/static` mount serves existing HTML/JS/CSS/logo/icons/license (GET/HEAD, Starlette static-file behavior, missing/traversal → 404). All 35 static files matched source hashes over HTTP in the isolated check. Do not carry an unguarded original `/`/`static` application into a public deployment by accident.

## Request shapes and validation

`UUID` below means a real returned lowercase 32-hex identifier; `Draft` contains existing persisted field keys, not arbitrary front-end trait names. Exact required/default/range/enum/nullable/array properties are preserved in the linked OpenAPI JSON; its response schemas are untyped because the original routes return Python dicts/Responses without response_model. Output shapes below therefore come from service code and actual responses, not inferred OpenAPI typing.

| Model | Fields / rules |
|---|---|
| GenerateRequest | description:string 10–2500; style:forensic/portrait/illustration default forensic; case_id:string/null; case_revision:int/null; workspace:text/lab default text. With a case, persisted testimony/draft override caller description/style and case_revision must match. |
| NewCase | title:string 1–120, nonblank after trim; synthetic:boolean default false |
| SaveCase | revision:int ≥0; original:string/null ≤1800 optional; draft:Draft required |
| Freeze | revision:int ≥0; text:string 10–1800, at least ten non-whitespace characters; exact bytes retained |
| Clarification | text:string 1–1800 nonblank; source:operator/witness default operator |
| Attribute | value:string/null ≤100; confidence:unknown/tentative/certain; source:operator/witness; quote:string ≤1800. Null requires unknown; known requires tentative/certain. Witness source requires an exact quote occurring in original or witness/synthetic-sourced statements. |
| Draft | attributes:five shared Text fields (`age`,`complexion`,`hair`,`eyes`,`facial-hair`); lab:40 remaining fields; style:forensic/portrait; view:Portrait/16:9/Upper Body; note:string ≤1800; note_source:operator/witness. Sliders 0–100 integer strings or null; age 18–100 or null; enums exactly from schema. Missing fields filled Unknown; old Text-only saves preserve existing Lab. Pending note must be appended as clarification before generating. |
| Selection | version_id:UUID; preferred:boolean default false |
| Refinement | parent_id:UUID; instruction:string 1–1800 nonblank; draft:Draft; revision:int ≥0; request_key:UUID; reviewed_prompt:string ≤2500 default empty. Generation requires exact final preview text. |
| MultiViewRequest | parent_id:UUID; draft:Draft; revision:int ≥0; request_key:UUID; reviewed_prompt:string ≤2500 default empty. Generation requires exact preview. |
| Project | schema_version:1; source_version_id:UUID; operations:Operation[] ≤2000, total points ≤100000, serialized project ≤2 MiB |
| Operation | tool:pencil/brush/eraser/line/rectangle/ellipse/arrow/text/crop/rotate/flip/clear; points:[x,y,pressure][] ≤20000/op, finite coords/pressure0–1; color:#RRGGBB; width1–120; opacity.05–1; text≤240; rect:[x,y,width,height]/null. Required points/text/rect depend on tool. Crop ≥32px and contained; rotations swap dimensions. |
| SaveEdit | parent_id:UUID; request_key:UUID; png:PNG base64 data URL; project:Project. Decoded PNG64bytes–12MiB, 32–8192px sides, ≤16MP; dimensions must agree with source/operations. |
| ImportImage | request_key:UUID; image:PNG/JPEG/WebP base64 data URL; filename:string1–180; consent:true. MIME must match decoded format; one frame, 32–8192px sides, ≤16MP and ≤12MiB. No multipart route. Raw original retained; filename sanitized as a display label, never a path. |
| SaveEnhancement | parent_id:UUID; source_id:UUID; request_key:UUID; png:PNG base64 data URL; adjustments:Adjustments; engine:rgba-worker-v1. Parent must reopen the same non-destructive source; dimensions match resize. Saves normalized PNG, with parameters/provenance; does not independently reapply pixel math. |
| Adjustments | brightness/highlights/shadows −100..100; contrast −95..95; exposure −3..3; gamma .2..3; saturation0..200; temperature−100..100; sharpen/smoothing0..200 and0..100; blur integer0..5; grayscale/invert booleans; resize integer25..150%. Defaults/steps/presets come from `/api/enhance-schema`. |
| Layout | checked:true; panels:exactly four Panel entries, unique all four angles; note≤500 |
| Panel | angle:front/left/right/three_quarter; rect:[x,y,width,height] ints, inside sheet, each dimension≥32, no overlap |
| ReportRequest | version_id:UUID; request_key:UUID |

Character Lab groups are Structure & Shape, Eyes & Nose, Mouth & Jaw, Hair Analysis, Physical Build, Distinguishing Details, Appearance & Presentation. The shared Text fields account for five of the 45 schema entries. `Field` has key,label,kind and optional low/high/options/shared; kinds include slider/select/text/age. `source`/`confidence` annotations belong to Attribute, not the field schema. Numerical values are subjective relative directions, not calibrated probabilities or anatomical measurements.

## Output shapes

| Shape | Fields and semantics |
|---|---|
| Job | `{job_id,status,message,image_url}`. status working/complete/failed; image_url null until real persisted completion. Safe failure classification, not raw CLI response. |
| CaseSummary | `{id,title,synthetic,created_at,frozen_at,revision}`. SQLite returns synthetic as integer0/1; normalize deliberately if UI requires boolean. |
| Case | Summary + `{draft,statements,events,versions,last_generated_draft,selected_version_id,preferred_version_id,refinements,jobs}`. `statements` include `{id,case_id,kind,text,source,created_at}`. `events` include `{id,case_id,kind,created_at,detail}`. Case `jobs` use `id`, not top-level Job’s `job_id`. |
| Version | `{id,parent_id,created_at,sha256,style,image_url,case_revision,workspace,...metadata}`. Workspaces text/lab/refinement/sketch/upload/enhance/multiview. Metadata varies by creation kind, with mode, dimensions, attribute_snapshot, original/refinement/generation prompts, source/editing parameters. No single artificial RV numbering or identity consistency flag. |
| PromptPreview | `{description,style,length,limit:2500,over_limit}`; previews may exceed limit for review, submission rejects over-budget prompts. Refinement/multi-view add their documented mode/route flags. |
| SaveResult | `{version_id,sha256,replayed}`. Does not return a full Case. Duplicate request key with identical payload returns prior version; mismatch is 409. |
| ReviewedLayout | `{id,created_at,source_sha256,source:"operator visual layout review",note,panels:[{angle,rect,width,height,sha256}]}` |
| SheetRequest | `{job_id,parent_id,created_at,status,message}`; completed versions add `{image_url,sha256,image_format,layout}`. layout may be null before operator review. |
| Report | `{id,case_id,version_id,created_at,files,preview_url}`; files maps pdf/json/png to `{sha256,bytes,url,filename}`. Immutable saved bundle, byte-checksummed on download. |
| ReportSnapshot | `{schema_version,report_id,report_created_at,heading,disclaimer,case,statements,selected_version,selected_image_export,persisted_case_settings,selected_attribute_snapshot,attribute_summary,revision_history,refinement_history,generation_jobs,case_events,notices,multi_view_requests,panel_reviews}`. Image export distinguishes normalized PNG SHA from original source SHA. |

Do not treat every version as an AI job. Uploads, artist saves and local adjustments store completed records but generation_job_id=null and explicit local provenance. Original `/images` bytes, canonical `/pixels`, normalized PNG exports and rendered crop/report files have distinct checksum scopes.

## Async execution and retries

- `/api/generate`, `/refine`, `/multiview` persist a working job before starting a daemon thread and return 202. The original process guard plus persisted working-record check prevents concurrent generation in one process. No progress percentage or cancellation endpoint exists. The preserved UI polls every two seconds.
- Original `codex exec -C <job_workdir> --sandbox workspace-write --skip-git-repo-check -o <response.txt> -` receives the existing prompt on stdin; inherited OPENAI_API_KEY/OPENAI_BASE_URL are removed. Default timeout is 600s (`CODEX_GENERATION_TIMEOUT`). No provider/API fallback or source pixels were added.
- Text claims alone cannot finish a job: the worker detects a new raster in the configured Codex generated-images directory, validates type/size/dimensions/readability and saves it. Durable finish validates/copies bytes, computes SHA, stores immutable version/lineage and sanitizes persisted failure text.
- Poll until complete/failed. On complete, refresh the Case, retrieve a validated image and verify a saved version exists. Retain prior image while working/failure; accepted submission is not completion.
- Initial `/api/generate` has no request_key; do not automatically resubmit after ambiguous connection loss. First inspect current persisted case jobs. Refinement/multi-view/local edits/imports/enhancements/reports use request keys: reuse the exact original body/key for safe retry; do not create a new key on every network retry.
- Saves/freezes/generation use optimistic case revision; clarifications increment it. Local image saves and selection do not use the same revision token. Fetch current Case at appropriate operation boundaries. Parent links are explicit, not necessarily previous array entry.
- Startup/import calls case_store.initialize(), marks interrupted working jobs failed and retains files/records; it does not resume a subprocess. Run one owner process per store. The shared Codex output folder attribution still requires unrelated generation sessions to be idle.

## Tested boundaries and limitations

Fresh HTTP checks exercised every explicit route with synthetic cases: frozen testimony, Unknown/uncertainty, generation/polling, source images, refinement retry, local project/identity enhancement/upload, multi-view review/crops, preferred/selected state, report snapshots/exports, static assets and negative ownership/path checks. An actual owned-process restart retained six versions, two cases, exact statements, selections and byte-identical revision/report downloads. SQLite integrity/FK checks passed. The 56 pytest tests include broader failure/format/quote/idempotency/rollback/restart checks.

No real image generation was requested; fake-CLI pattern images are not AI results. HTTP enhancement used identity/default parameters; actual nontrivial browser-worker pixel parity and React flows remain I4/I7 work. No authentication, tenant enforcement or I3 adapter has been added. Failed write paths, glyph restrictions and image drift remain the original application's behavior, not solved production guarantees.
