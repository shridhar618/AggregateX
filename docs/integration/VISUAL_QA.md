# Final visual QA

The existing UI handoff's shell/design inventory and I1 screenshots were used as reference: charcoal/coral dark palette, cream/sage light palette, Syne headings, Inter controls, IBM Plex Mono metadata, 248px desktop sidebar, topbar, reticle hero, panels, buttons, studio columns, image viewer and mobile drawer. Landing/auth source was preserved. WitnessTrace records replace the procedural domain model; no procedural composite is an integrated fallback.

## Captures and review

Actual Chromium screenshots are in `evidence/final/`:

- `studio-{dark,light}-{1920,1440,1280,768,390}.png`: ten actual viewport/theme states, full-page captures.
- `settings-{dark,light}-{1920,1440,1280,768,390}.png`: ten actual Settings states.
- `workspace.png`, `library.png`, `compare.png`, `settings.png`: populated navigation surfaces.
- `sketch-edit.png`, `enhance-light.png`, `layout-review.png`, `multiview.png`: actual editing and reviewed-layout workflows.

The studio matrix was reviewed in a contact sheet and selected native captures, with comparison to the I1 studio reference. Dashboard, library, light tablet settings and image-processing screenshots were inspected separately. These images use an invented case and labelled geometric CLI fixtures. They do not represent generated faces or scientific accuracy. Full-page screenshots can place sticky shell elements at the captured scroll position; this is a capture artifact, not an additional navigation bar.

## Corrections

- Settings now uses the real integrated health/preferences panel; all ten sizes/themes have no horizontal document overflow, including the former 768px defect.
- Sidebar labels wrap instead of clipping the long Investigation Workspace label.
- Light-theme status roles have darker readable colors; the viewer well follows the light palette. Bounded processing surfaces inherit the parent theme, with readable histories/labels/buttons instead of dark-block/light-caption defects.
- Saved image viewers contain the actual image proportions, including landscape 720×480 fixtures. The former forced 4:5 display is not used for integrated full images.
- The original three-column studio presentation remains on wide desktops and collapses responsively. Full Character Lab/refinement/report controls follow the main studio; the long editing tool surface remains within the same Revelio shell.
- The dashboard retains the original owl/reticle hero, flow list and statistics/grid composition, with actual counts and activity.
- Library uses existing card classes with persisted thumbnails and metadata. Unsupported delete/provider controls are not shown in integration mode.
- Engine documents retain their original interaction DOM and processing algorithms with scoped theme/layout overrides. Enhancement's committed local preview opens automatically; Sketch/Enhance switches preserve the document.

Browser assertions verify no horizontal overflow for studio and Settings at every requested width/theme, working keyboard comparison, successful images and zero JavaScript page exceptions. This is targeted functional/visual QA, not a claim of a full accessibility audit or physical-device testing. The preserved 131-check I1 driver also passed freshly in explicit legacy mode with external captures; its original baseline files were not rewritten. Current integrated checks are recorded in `evidence/final/browser-result.json`.
