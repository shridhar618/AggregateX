# Security review — local integrated application

## Scope and design

This is a loopback-only, shared-collection application. React, gateway and WitnessTrace bind to 127.0.0.1. The original scrypt account/password verification and opaque, hashed server-side sessions remain responsible for authentication. Every `/wt-api` route, including images, reports, schema and engine assets, uses the server-side `require_user` dependency. A React login screen alone is not the security boundary.

The original WitnessTrace service remains unauthenticated. Local processes can call its loopback port directly. The gateway does not make that service safe to expose publicly. Do not bind it to 0.0.0.0, forward/tunnel it, or deploy this configuration as a public service. All authenticated local users intentionally share the same collection; no user-level tenancy or cross-user isolation is claimed. Backend ownership validation prevents using a version/report/layout ID under the wrong case.

## Verified controls

- Original auth tests cover unauthenticated and expired sessions. Browser registration/login redirect uses the real session service.
- Gateway tests cover unauthenticated case/generation/image requests; all newly exposed feature paths are checked with and without sessions.
- The gateway rejects non-loopback targets and ports 8000/8001, unknown paths, non-JSON mutations and foreign Origin. No upstream credentials or browser cookies are forwarded; redirects are disabled.
- Static code is an allowlist, plus strictly named existing SVG icons. Traversal and arbitrary filenames are rejected. Engine documents use same-origin framing restrictions and no-store responses.
- Original stores validate case ownership, prompt review, quote sources, immutable testimony, stale drafts, image decoding/type/size/pixel budgets, edit operations, crop rectangles, checksums and report manifests. These original suites were rerun.
- The final browser run verifies hashes of six immutable revisions and all persisted report files after backend restart, plus SQLite integrity and foreign keys.
- Gateway request bodies are bounded to 48 MiB; original image-specific limits remain in the underlying validators. No arbitrary upload is treated as generated AI output.
- The launcher refuses occupied isolated ports, uses a private umask, starts loopback processes only and stops only its own children. Protected-port listener snapshots were compared unchanged during verification.

An OS-local caller can bypass web sessions by contacting WitnessTrace directly. This is an explicit limitation of the preserved local architecture, not a claimed authenticated public API. Removing that limitation would require a separately scoped service-auth/deployment design. Host authentication and local machine access remain relevant.

## Newly introduced files and dependencies

Only reviewed source/config/tests/docs and synthetic screenshots/log summaries are committed. Runtime databases, case images, worker logs, Codex homes, real generated faces and account credentials are excluded. Existing runtime paths were not reset, stashed, cleaned, copied over or published. The final staging audit checks path exclusions, SQLite signatures, common token/private-key patterns and screenshot provenance; it is not a guarantee that arbitrary historical repository content is non-sensitive.

Compatible npm updates resolved the historical 13 development-toolchain advisories. Final `npm audit` reports **zero vulnerabilities**. The integrated launcher uses the WitnessTrace runtime lock, also verified against the complete Revelio test suite. Legacy backend requirements retain historical pins and are not the integrated installation path. Existing dependency deprecation warnings are recorded in test logs.

## OWNER-SEC-01 — OPEN, owner action required before remote publication

Remote branch b (`49f63ee…`) already contains private runtime artifacts, as documented in INTEGRATION_BASELINE.md: databases, case images/reports, worker artifacts and private migration/evidence material. Ignore rules cannot remove material already present in Git history. This integration starts from main plus the safe I2 source-only import; b is **not** an ancestor of the final branch, and b was not merged wholesale.

Owners must inventory/classify the exposed historical material, assess whether any credentials need revocation, decide the appropriate retention/removal/history remediation with collaborators, and record clearance for shared publication. Rewriting shared history, deleting branches and force-pushing require owner authorization and were not performed.

**Locally integrated and tested: PASS. Safe remote main publication: BLOCKED pending owner remediation.** No remote push was made. This security issue did not prevent safe local engineering or the local main fast-forward. See FINAL_INTEGRATION_REPORT.md for the exact delivered Git state.
