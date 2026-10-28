# Image integrity on Base Sepolia

Open a saved case revision in the composite studio. The Blockchain Integrity panel offers Connect MetaMask, Register on Blockchain, and Verify Integrity. Connect switches to Base Sepolia (84532), subject to wallet approval. Registration asks MetaMask to approve a transaction with zero transfer value, addressed to the fixed sink `0x000000000000000000000000000000000000dEaD`, with the current connected account as sender. Gas uses Base Sepolia test ETH. No private keys, paid API, deployment, or contract are required.

The authenticated `/wt-api/api/cases/{case_id}/versions/{version_id}/integrity` GET and POST routes use the existing Revelio session and allowlisted gateway. WitnessTrace itself remains a loopback-only service; do not expose its port publicly. Cases retain the existing shared local collection permissions.

The backend hashes the saved original file bytes with SHA-256 on every check. The immutable revision digest remains the baseline, including for imported JPEG/WebP originals; browser previews and exported PNG conversions are never substituted. Path validation and case/revision association apply before reading files.

Transaction input is UTF-8 `revelio:image:v1:sha256:` followed by the hex SHA-256 of UTF-8 `revelio:witnesstrace:image:v1:<revision_id>:<original_image_sha256>`. Revision binding prevents a transaction for one revision from verifying another. The public transaction contains only this versioned commitment. It contains no image bytes, testimony, filenames, or case IDs. Wallet address, transaction time, and commitment are public permanently.

SQLite's additive `blockchain_integrity` table associates one transaction with one revision. The pending reference is persisted immediately after broadcast to support reload recovery; `confirmed_at` is recorded only after independent backend verification. An existing reference cannot be silently overwritten. Hashes supplied by browsers are never trusted as proof. New registrations require the wallet sender, which is saved atomically with the transaction hash and cannot be changed on retries. Sender and recipient are independently checked against the public RPC transaction and receipt.

Verification does not need MetaMask: the backend reads fixed public Base Sepolia RPCs (`https://sepolia.base.org`, PublicNode, and dRPC) and checks network, transaction hash, zero value, fixed sink recipient, persisted wallet sender, matching receipt sender/recipient, exact versioned commitment, successful receipt, matching transaction/receipt block, and canonical block hash. It also recomputes the current saved image digest. RPC failures display ERROR rather than VERIFIED. No explorer API is used.

Statuses:

- NOT REGISTERED: no transaction reference and saved bytes match the original.
- PENDING: loading, transaction/receipt not yet visible, or canonical block confirmation unavailable.
- VERIFIED: current bytes, commitment, transaction and successful canonical receipt match.
- TAMPERED: saved bytes or transaction commitment/shape differ.
- ERROR: wallet rejection, failed receipt, RPC failure, wrong network, or another operational error.

An idempotent additive migration marks only registrations with an existing `confirmed_at` as legacy eligible. A legacy self-transaction still requires a successful canonical receipt and exact revision commitment; its on-chain sender is pinned on the first successful post-migration verification. New self-transactions and unconfirmed legacy self-transactions are rejected. Existing transaction associations cannot be overwritten.

One canonical receipt is sufficient for this MVP. Verification is a point-in-time check, not a finality guarantee or proof that witness testimony is true. Verify again for a fresh check. Dropped/replaced transactions retain their original reference for investigation through BaseScan; the MVP does not replace registrations automatically.

Validation commands (from repository root):

```sh
npm run lint
npm run build
npm run test:adapter
node --test scripts/tests/integrity-wallet.test.mjs
witness-backend/.venv/bin/python -m pytest witness-backend/tests -q
witness-backend/.venv/bin/python -m pytest backend/tests -q
witness-backend/.venv/bin/python scripts/tests/verify_integrity.py
```

The browser E2E uses an isolated temporary database, synthetic image, simulated injected MetaMask provider, real ethers v6 BrowserProvider/signer, authenticated React/FastAPI gateway, and deterministic backend RPC responses. It tests wallet network switching, explicit rejection, zero-value submission, pending persistence, reload, successful verification, tampering, and BaseScan links. It does not sign or broadcast a live testnet transaction. A live smoke test requires the operator to click Approve in their own MetaMask extension and then observe VERIFIED with a BaseScan transaction.

Reference documentation: [ethers v6 providers](https://docs.ethers.org/v6/api/providers/) and [Base network details](https://docs.base.org/get-started/connect-to-base).

## Submit one live testnet transaction

1. Open `http://127.0.0.1:5182/app#/new` in the browser where MetaMask is installed, sign in, and select the case and saved image revision you want to register. Select an unregistered revision; a wallet rejection before broadcast does not create a database registration.
2. In Blockchain Integrity, click **Connect MetaMask**, choose your funded test account, and approve switching to **Base Sepolia** if prompted. Confirm chain ID **84532**.
3. Check that the panel says **NOT REGISTERED**, then click **Register on Blockchain** once.
4. In MetaMask, check the network is **Base Sepolia**, sender is your selected account, recipient is **0x000000000000000000000000000000000000dEaD**, amount is **0 ETH**, and only the network gas fee uses test ETH. The transaction data is the versioned SHA-256 commitment. Approve the transaction in MetaMask.
5. Wait for confirmation. The panel should change from **PENDING** to **VERIFIED**. If it remains pending, click **Verify Integrity** to query the independent backend RPC. A public RPC visibility delay may require a later retry.
6. Click **View transaction on BaseScan** and confirm a successful transaction, the fixed sink recipient, and zero value. Click **Verify Integrity** again for a fresh image-byte and chain check.

No live transaction is submitted by the automated tests or by restarting the application.

## Live verification diagnostics and wallet delegation

The reported transaction `0x5cd053f2f3bd9fb65625ee5c2ad0611adb62e19f5acd6a4542a9a345ab762091` succeeded in Base Sepolia block **51516198**. Two independent public RPCs returned matching transaction, receipt and execution trace data. The original backend HTTP client was blocked with HTTP 403 / edge error 1010 when using Python urllib's default User-Agent. The same request with `User-Agent: revelio-integrity/1.0` succeeds. RPC requests now set this header, use fixed public fallback endpoints, and share a bounded verification deadline.

A second incompatibility was hidden by that transport error: this wallet produced a type-4 MetaMask delegation transaction. Its outer recipient is MetaMask's DelegationManager, `0xdb9b1e94b5b69df7e401ddbede43491141047db3`, and the actual sink call is executed internally. A direct-recipient-only check would reject it even after repairing HTTP access.

The verifier now supports this narrowly identified wrapper while retaining direct and previously confirmed legacy paths. It still validates the original image bytes and revision-specific commitment, registered outer sender, chain, zero outer value, successful receipt, receipt identities and canonical block. For a type-4 call to this exact manager with the observed method selector, it additionally obtains `trace_transaction` from a public trace-capable endpoint. It requires the trace root to match the outer transaction, all trace records to bind to the same transaction and canonical block, and a successful CALL to the exact sink with zero value and exact commitment data. Every ancestor must exist, succeed, and have a linked caller/callee address. Reverted calls, static calls, calldata substrings and events alone cannot establish verification. The returned verification mode distinguishes `wallet_delegation_trace` from a direct transaction; `execution_sender` is the internal account, while `expected_sender` remains the persisted connected wallet. No new contract is deployed or transaction submitted for this support.

Every integrity result includes a safe `code` and `retryable` flag. RPC access denial, rate limits, timeout, missing methods and malformed responses are operational ERROR states, separate from TAMPERED fingerprint/sender/recipient mismatches and `TRANSACTION_REVERTED`. A JSON-RPC null transaction or receipt is PENDING, never evidence of tampering. The existing transaction reference and sender survive every retry. Click **Verify Integrity** or reload to recover using the saved hash; no wallet approval or new transaction is needed for verification.

Regression data in `witness-backend/tests/fixtures/base_sepolia_wrapped.json` is public RPC transaction/receipt/trace data only, with no local image bytes, testimony or case identifiers. Tests replay this actual wallet envelope against synthetic revisions and inject HTTP 403, HTTP/JSON-RPC rate limits, unavailable traces, malformed receipts and failed execution paths.
