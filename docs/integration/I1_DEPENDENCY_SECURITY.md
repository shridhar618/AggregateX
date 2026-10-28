# I1 dependency and Git-history security findings

Audit date: 2026-10-28. No dependency versions, framework, lockfile, production source or remote refs changed in I1.

## npm audit: 13 affected packages

Fresh `npm audit --json` reports **10 high, 2 moderate, 1 low, 0 critical** affected packages. These are package-level totals, not 13 unique advisories; several packages carry multiple advisories. `npm audit --omit=dev --json` reports **zero production dependency vulnerabilities**. React/ReactDOM are the application runtime dependencies; all 13 affected packages are marked `dev: true` by the lockfile. Vite is the only direct affected dependency; the others are transitive.

Evidence: [full audit](evidence/i1/npm-audit.json), [runtime-only audit](evidence/i1/npm-audit-runtime.json). Both contain npm registry advisory data and package names, no local credentials or records.

| Package / locked version | Severity | Reachability in this project | Candidate outside all reported affected ranges |
|---|---|---|---|
| `@babel/core` 7.29.0 | low | Lint tooling via react-hooks/Babel; malicious source-map comments are the relevant input, not a normal browser form. | `>7.29.0` |
| `@humanfs/node` 0.16.7 | moderate | ESLint filesystem operations; outside-tree copies require symlinked/untrusted source inputs. | `>=0.16.8` |
| `baseline-browser-mapping` 2.10.8 | moderate | Build/lint browser-target lookup; invalid-input termination is a tool-process risk. | `>=2.11.0` |
| `brace-expansion` 1.1.12 | high | ESLint/minimatch glob handling; crafted glob recursion/expansion can exhaust resources. | `>=1.1.21` |
| `browserslist` 4.28.1 | high | Babel target resolution; untrusted stats/config/query input is the risk. | `>4.28.6` |
| `flatted` 3.4.1 | high | ESLint cache serialization; malicious serialized cache input can pollute prototypes. | `>3.4.1` |
| `js-yaml` 4.1.1 | high | ESLint configuration parsing; YAML aliases/merge chains can consume CPU. | `>=4.3.2` |
| `nanoid` 3.3.11 | high | PostCSS toolchain ID generation; crafted size/custom-generator inputs are needed for the reported flaws. | `>=3.3.18` |
| `picomatch` 4.0.3 | high | Vite/tinyglobby matching; crafted globs/character classes can affect matching or CPU. | `>=4.0.4` |
| `postcss` 8.5.8 | high | Vite CSS processing; malicious source-map comments/CSS can cause local file reads or unsafe output. | `>8.5.22` |
| `source-map-js` 1.2.1 | high | PostCSS source-map parsing; malicious indexed map section offsets can block the tool process. | `>=1.2.2` |
| `vite` 8.0.0 | high | Actual reference dev server is reachable on loopback; file-read/WebSocket/fs-deny and editor-launch advisories matter to developer machines. Windows-only findings are not directly exercised on Fedora; do not treat that as general clearance. | `>=8.1.6 within ^8.0.0` |
| `zod` 4.3.6 | high | React-hooks ESLint tooling parser; oversized constrained collections can exhaust lint-process memory. | `>=4.6.6` |

The candidate thresholds are derived from the returned advisory ranges; they are **not an installed or regression-tested remediation**. Parent ranges permit same-major candidates (e.g. Vite ^8.0.0, PostCSS ^8.5.8, Babel ^7.24.4). A dry-run audit-fix preview was run only in an external copy of the manifests, without `--force` or lifecycle scripts; it did not establish a clean upgraded audit and did not modify this application. Its proposed same-major resolutions included Vite 8.3.5, Babel 7.29.7, humanfs/node 0.16.8, baseline-browser-mapping 2.11.34, brace-expansion 1.1.21, Browserslist 4.29.5, flatted 3.4.4, js-yaml 4.3.2, nanoid 3.3.20, picomatch 4.0.7, PostCSS 8.5.32, source-map-js 1.2.2 and Zod 4.6.7. These are available preview candidates, not approved upgrades. No patch release is presumed behavior-neutral: Vite/plugin/Rolldown requirements, Node engine support, source-map handling, ESLint/config changes and visual/build output need testing. Do not upgrade React or switch frameworks to remediate these toolchain advisories.

### Deployment interpretation and required follow-up

Source inspection shows the client imports React/ReactDOM and project code; these Node build/lint packages are not intentionally shipped as browser runtime dependencies. Normal description form input is sent to FastAPI, not to npm parsers. This reduces runtime reachability for a static `dist/` deployment, but is not proof that every transitive vulnerable function is unreachable or that generated output is safe for untrusted build inputs. No exploit attempts were performed.

Vite is used during local development and preview. Its vulnerable dev endpoints are real server surfaces, even on localhost. I1 bound it strictly to 127.0.0.1:5182, ran only this trusted checkout and stopped it afterward. Do not deploy this affected dev server publicly. Do not treat `--omit=dev` as remediation for developers/CI still running vulnerable build tools.

**Gate DEP-01 — before final deployment:** owners/integration maintainer must choose compatible patched toolchain versions, regenerate the lock in a scoped change, inspect the resulting dependency diff, rerun full and runtime audits, lint/build, and affected browser baselines. Any unresolved high advisory needs an explicit documented reachability/risk decision. I1 intentionally establishes the baseline before those changes.

The existing Python yanked Pydantic/core pins noted in I0 are unchanged and remain a backend/dependency follow-up; this npm report does not audit Python dependencies.

## Existing remote Git exposure — OWNER-SEC-01

**OPEN: owner remediation/clearance is required before the final shared merge.** This gate is independent of I1's successful preservation/capture work. It cannot be closed by adding `.gitignore`.

Verified branch `b` / fetched `origin/b` SHA: `49f63ee4e242efe0c5aa4aef0a524652e75cfd5a`. I1 did not push or change it. The following tracked paths contain runtime material; the records' real-person/private classification cannot be ruled out:

| Tracked path family | Files | Exposure category |
|---|---:|---|
| `data/` including `data/witness.sqlite3` | 56 | Case statements, descriptions/attributes, metadata, revision files, imported images and PDF/JSON/PNG exports |
| `outputs/` | 14 | Saved generated composite images |
| `work/` | 34 | Raw worker replies, generation prompts and output images |
| `evidence/` | 434 | Historical screenshots, database snapshots, live job/record JSON, reports and prompt captures; `evidence/phase08/auth-status.json` may reveal authentication/environment status |
| `migration-private/` | 12 | Database backup, baseline-record manifests, verification logs and local runtime/process metadata |

These are source-tree counts for the committed ref, not counts of people or proven leaked credentials. SQLite schemas and the I0 database audit confirm records are present. The migration calls some fixtures synthetic, but that does not prove that every statement, screenshot, report or uploaded image throughout history is safe to publish. Do not reproduce raw records or images in the audit documents.

A limited secret-shape scan examined 291 committed text blobs for provider-key patterns, private-key PEM headers and long access/refresh/id-token JSON values. It found **zero matches**. No credential-named paths beyond `.env.example` were found in I0. This does **not** exclude differently formatted credentials, secrets in images/databases/other history, identifiers, local paths or private testimony. The scan records only counts/path categories in [git-history-risk-summary.json](evidence/i1/git-history-risk-summary.json); it prints no matching values.

### Gate closure belongs to repository owners

Before final shared merge, owners must classify the already-pushed runtime material, determine repository visibility/access and possible forks/clones/caches/PR artifacts, perform an authorized full secret/privacy review, and record the disposition. Revoke/rotate any credentials if exposure is confirmed. Decide whether to restrict access, remove runtime paths in future commits and request hosting-provider cleanup, or authorize coordinated history cleanup. Any history rewrite, deletion or force-push requires explicit separate approval; none was performed or prepared as an automatic step here. Deleting files in a new commit does not remove historical blobs or copies.

Future integration imports must explicitly allowlist source-only backend files, exclude runtime material, and inspect staged paths. Do not merge/cherry-pick b's wholesale replacement commit. Existing private backups are local and outside Git. I1 commits only synthetic, password-masked UI screenshots, source/config hashes, test harness/results and documentation. No account database, password/session storage state, generated personal image, WitnessTrace record or raw worker artifact is added.

Brand ownership for the existing owl/wordmark is still unverified. It remains preserved in the source UI and reference captures; I1 adds no new endorsement or external logo. Font loading remains the source Google Fonts integration; offline font provisioning/licence packaging is not changed or certified in this phase.

## Advisory references

Each entry below is the source advisory URL returned by npm audit. The complete ranges, severity and titles remain in the JSON evidence.

- **@babel/core:** [GHSA-4x5r-pxfx-6jf8](https://github.com/advisories/GHSA-4x5r-pxfx-6jf8)
- **@humanfs/node:** [GHSA-p498-v437-472g](https://github.com/advisories/GHSA-p498-v437-472g)
- **baseline-browser-mapping:** [GHSA-w5vr-8v7q-w6rv](https://github.com/advisories/GHSA-w5vr-8v7q-w6rv)
- **brace-expansion:** [GHSA-f886-m6hf-6m8v](https://github.com/advisories/GHSA-f886-m6hf-6m8v), [GHSA-3jxr-9vmj-r5cp](https://github.com/advisories/GHSA-3jxr-9vmj-r5cp), [GHSA-mh99-v99m-4gvg](https://github.com/advisories/GHSA-mh99-v99m-4gvg), [GHSA-rgw5-rvv9-x895](https://github.com/advisories/GHSA-rgw5-rvv9-x895), [GHSA-q2hr-2g5m-vwhr](https://github.com/advisories/GHSA-q2hr-2g5m-vwhr), [GHSA-qhr7-859c-m2p7](https://github.com/advisories/GHSA-qhr7-859c-m2p7), [GHSA-6j4f-fj2g-mc7p](https://github.com/advisories/GHSA-6j4f-fj2g-mc7p)
- **browserslist:** [GHSA-c83g-rgw3-j3cx](https://github.com/advisories/GHSA-c83g-rgw3-j3cx), [GHSA-73wf-gq98-2v4g](https://github.com/advisories/GHSA-73wf-gq98-2v4g)
- **flatted:** [GHSA-rf6f-7fwh-wjgh](https://github.com/advisories/GHSA-rf6f-7fwh-wjgh)
- **js-yaml:** [GHSA-h67p-54hq-rp68](https://github.com/advisories/GHSA-h67p-54hq-rp68), [GHSA-52cp-r559-cp3m](https://github.com/advisories/GHSA-52cp-r559-cp3m), [GHSA-5p4m-2wfm-xmqj](https://github.com/advisories/GHSA-5p4m-2wfm-xmqj), [GHSA-2883-xcg3-v3hh](https://github.com/advisories/GHSA-2883-xcg3-v3hh)
- **nanoid:** [GHSA-28wg-ghj8-5hjv](https://github.com/advisories/GHSA-28wg-ghj8-5hjv), [GHSA-2v37-7h3g-55p8](https://github.com/advisories/GHSA-2v37-7h3g-55p8), [GHSA-xwg4-73v4-xw9w](https://github.com/advisories/GHSA-xwg4-73v4-xw9w)
- **picomatch:** [GHSA-3v7f-55p6-f55p](https://github.com/advisories/GHSA-3v7f-55p6-f55p), [GHSA-c2c7-rcm5-vvqj](https://github.com/advisories/GHSA-c2c7-rcm5-vvqj)
- **postcss:** [GHSA-qx2v-qp2m-jg93](https://github.com/advisories/GHSA-qx2v-qp2m-jg93), [GHSA-6g55-p6wh-862q](https://github.com/advisories/GHSA-6g55-p6wh-862q), [GHSA-fxqj-rqcc-2cmp](https://github.com/advisories/GHSA-fxqj-rqcc-2cmp), [GHSA-r28c-9q8g-f849](https://github.com/advisories/GHSA-r28c-9q8g-f849)
- **source-map-js:** [GHSA-68fv-2mgg-jv7q](https://github.com/advisories/GHSA-68fv-2mgg-jv7q)
- **vite:** [GHSA-4w7w-66w2-5vf9](https://github.com/advisories/GHSA-4w7w-66w2-5vf9), [GHSA-v2wj-q39q-566r](https://github.com/advisories/GHSA-v2wj-q39q-566r), [GHSA-p9ff-h696-f583](https://github.com/advisories/GHSA-p9ff-h696-f583), [GHSA-v6wh-96g9-6wx3](https://github.com/advisories/GHSA-v6wh-96g9-6wx3), [GHSA-698v-4r3x-3vcv](https://github.com/advisories/GHSA-698v-4r3x-3vcv), [GHSA-r825-w8mm-5pxw](https://github.com/advisories/GHSA-r825-w8mm-5pxw), [GHSA-587h-7wmj-h5pm](https://github.com/advisories/GHSA-587h-7wmj-h5pm), [GHSA-9jrq-w75r-8gcw](https://github.com/advisories/GHSA-9jrq-w75r-8gcw), [GHSA-rq7h-c2jc-7f22](https://github.com/advisories/GHSA-rq7h-c2jc-7f22), [GHSA-fx2h-pf6j-xcff](https://github.com/advisories/GHSA-fx2h-pf6j-xcff)
- **zod:** [GHSA-mrhx-c7xc-m3w5](https://github.com/advisories/GHSA-mrhx-c7xc-m3w5)
