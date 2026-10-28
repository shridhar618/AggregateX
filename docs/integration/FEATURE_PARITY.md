# Feature parity

React is the primary interface. WitnessTrace is the sole owner of integrated case/image records. Legacy Revelio source remains available explicitly; its procedural renderer is never an integrated generation fallback.

| Feature | Integrated behavior | Verification |
|---|---|---|
| Landing, auth, shell | Existing landing, registration/login, sidebar, topbar, fonts, themes, dialogs/toasts and responsive shell retained | I1 reference captures; final screenshots; real session browser flow |
| Dashboard | Original hero/reticle and card layout; real cases, unfrozen count, selected-case revisions, job status and persisted events | Final browser navigation and screenshot |
| Cases/testimony | Witness or explicitly synthetic cases; original exact frozen account; append-only sourced clarifications; optimistic revisions | Backend suites; browser freeze, addendum, case switch, refresh/restart |
| Generation | Explicit request through session gateway to unchanged Codex worker; real job polling, saved image, failure recovery | I3 real-generation evidence; I3 30-check regression; final fixture workflow |
| Character Lab | Backend schema renders all **45** attributes in **seven** groups; Unknown, uncertainty, operator/witness quote, sliders/selections, reset group, undo, saved draft, prompt review and explicit Update Preview | Schema count, persisted slider, explicit Lab revision in browser; quote validation in backend |
| Refinement | Explicit text, reviewed validated prompt, immutable child with parent ID, no silent retry | Browser child lineage; backend idempotency/failure tests |
| History/preferred | Actual revision thumbnails, parent IDs, source checksums, server-side selection and preferred version, full image and PNG | Browser preferred selection; backend ownership/persistence |
| Compare | Existing React CompareSlider with keyboard arrows and side-by-side display; saved revision selection | Browser keyboard check; actual comparison screenshot |
| Sketchpad | Original pencil/brush/eraser/shape/text/layer/undo/redo/zoom/pan/crop/rotate/flip engine in a bounded same-origin document; saved PNG plus editable project | Browser drawing/save and retained document across hash navigation; backend operations tests |
| Enhance | Original upload consent/validation, controls, presets, reset/undo/redo, worker pixels, before/after, saved parameters and revision | Browser adjustment/save and exact RGBA preview-to-save comparison; backend upload/processing tests |
| Multi-view | Original explicit sheet prompt review/generation, layout confirmation, reviewed angle buttons/navigation/downloads, revision lineage | Browser fixture sheet, four reviewed test rectangles, navigation and authenticated crop download; backend bounds/ownership tests |
| Reports | Persisted selected-image PDF/JSON/PNG bundles; testimony, sourced attributes, provenance, lineage and checksums | Browser download/manifest hashes; backend PDF text/content tests |
| Library | Existing card styling with actual persisted thumbnails/metadata; search titles, case selection, history and export controls | Browser navigation/screenshot; no unsupported deletion controls |
| Settings | Health/CLI-installation caveat, backend-reported directory, storage ownership explanation, persistent theme and reduced motion | Ten viewport/theme captures, no overflow; account/health suites |
| Persistence | Selected ID restored; backend records/images/edit projects/reports survive refresh and process restart | Six revisions, all source/report hashes, SQLite integrity/FKs in final browser test |

## Engine lifecycle and limitations

Sketchpad and Enhance use the source engine document rather than rewritten processing algorithms. The authenticated gateway serves an explicit code-asset allowlist. A small bridge routes requests/download URLs through the gateway, selects the parent's case, synchronizes saved backend records and follows the parent theme. The editor stays mounted while hidden on other hash routes; switching Sketch/Enhance uses the same document. Case switching asks before discarding dirty image edits. A full browser refresh still discards unsaved pixels, as the UI explains.

Multi-view has a separate bounded engine document, selected to the same canonical case. The fixture is a geometric test pattern; its crop test verifies geometry/persistence, not facial pose accuracy. Actual AI sheets require operator review of returned poses. They are **2D interpretations, not geometrically accurate reconstructed 3D models**.

No scientific face accuracy, image-reference conditioning, automatic identity consistency, public tenancy, interrupted-worker continuation or quota guarantee is claimed. Codex generation remains the original text-driven pipeline. Existing original case stores were untouched; connecting one is an explicit storage configuration choice, not an automatic migration.
