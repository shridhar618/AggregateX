# Final API mapping and ownership

React requests same-origin `/wt-api/<upstream-path>`. The gateway reuses `require_user` from Revelio's account/session service and forwards only allowlisted paths to the configured loopback WitnessTrace target. `/api/auth/*`, `/api/health` and `/api/catalog` remain Revelio-owned shell/auth operations. No WitnessTrace records are copied into Revelio's database.

| UI operation | Method and WitnessTrace path | Persisted owner / contract |
|---|---|---|
| Health | GET `/api/health` | WitnessTrace CLI installation and generated-images directory; not auth/quota proof |
| Case cards/search | GET `/api/cases`; GET `/api/cases/{case}` | SQLite summaries/full canonical Case; title search is client-side |
| Create | POST `/api/cases` | `{title, synthetic}` |
| Save draft | PUT `/api/cases/{case}` | `{revision, draft}`; full original 45-field schema |
| Freeze testimony | POST `/api/cases/{case}/freeze` | `{revision,text}`; immutable exact original |
| Sourced addendum | POST `/api/cases/{case}/clarifications` | `{text,source}`; append-only |
| Lab schema | GET `/api/lab-schema` | Seven groups/45 fields from original lab_schema.py |
| Prompt review | POST `/api/cases/{case}/prompt-preview` | Complete Draft; returns description/style/length/limit/over_limit |
| Text/Lab generation | POST `/api/generate` | `{description,style,case_id,case_revision,workspace}`; original worker, asynchronous handle |
| Poll | GET `/api/jobs/{job}` | Working/complete/failed; canonical saved Case refreshed on completion |
| Image | GET `/images/{version}` | Saved source bytes; React accepts only canonical same-service image URL |
| Select/prefer | POST `/api/cases/{case}/selection` | `{version_id,preferred}`; backend verifies case ownership |
| Refine review/submit | POST `/api/cases/{case}/refinement-preview`; POST `…/refine` | `{parent_id,instruction,draft,revision,request_key,reviewed_prompt}`; backend prompt match and deduplication |
| Sketch project | GET `/api/cases/{case}/versions/{version}/sketch` | Owned base image and editable operations |
| Save sketch | POST `/api/cases/{case}/local-edits` | Original SaveEdit: parent/request_key/png/project; immutable child |
| Import | POST `/api/cases/{case}/imports` | Original ImportImage: request_key/image/filename/consent; decoded/size-checked |
| Enhance source | GET `/api/cases/{case}/versions/{version}/enhance`; GET `…/pixels` | Owned source/settings/raw RGBA response |
| Enhance schema/save | GET `/api/enhance-schema`; POST `/api/cases/{case}/enhancements` | parent/source/request key, committed PNG, adjustments, engine |
| Multi-view list/review/submit | GET `/api/cases/{case}/multiview`; POST `…/multiview-preview`; POST `…/multiview` | Original Request including parent/draft/revision/request key/reviewed prompt |
| Review sheet layout | POST `/api/cases/{case}/views/{version}/layouts` | `{checked:true,panels:[{angle,rect}],note}`; four bounded/non-overlapping rectangles |
| Reviewed angle | GET `/api/cases/{case}/views/{version}/layouts/{layout}/{angle}.png` | `front`, `left`, `right`, `three_quarter`; persisted layout and source hash validated |
| Create/list reports | POST/GET `/api/cases/{case}/reports` | POST `{version_id,request_key}`; immutable persisted bundle |
| Report preview/download | GET `/api/cases/{case}/reports/{report}/preview`; GET `…/{pdf,json,png}` | Persisted manifest, SHA-256 checked by original store |
| Selected export | GET `/api/cases/{case}/versions/{version}/export.png`; GET `…/export.json` | Owned persisted records, normalized PNG, provenance JSON |
| Editing code assets | GET `/wt-api/tools/{asset}` at gateway | Reviewed static allowlist and named SVG icons; session required, no filesystem/path proxy |

IDs must be lowercase 32-hex; no arbitrary upstream/browser URL override. Mutations require JSON and same-origin browser Origin. POST/PUT bodies are bounded to 48 MiB to accommodate the original image/project contracts; image decoders enforce their original type/pixel/size and ownership limits. The gateway forwards no session cookies/authorization upstream and does not follow redirects. Responses are no-store; tool documents forbid external framing. Request timeouts do not resubmit mutations.

The original underlying WitnessTrace API is unauthenticated and must remain loopback-only. All local signed-in users share the collection. Cross-case IDs are rejected by the original stores; this is case-resource integrity, not user tenancy. See SECURITY_REVIEW.md.
