# Self-Sovereign Identity With Selective Disclosure

## Abstract

This report presents a prototype implementation of a decentralized Self-Sovereign Identity (SSI) ecosystem using four independent Django services: an Issuer, a Holder, a Verifier, and a Trusted Registry. The system demonstrates how a user can receive a signed Verifiable Credential (VC), store it in a wallet, selectively disclose only chosen claims, and submit a Verifiable Presentation (VP) for verification without revealing hidden attributes. The holder wallet also signs presentations with a holder private key to demonstrate proof of possession.

The prototype uses RSA asymmetric cryptography, salted SHA-256 commitments, deterministic sorting, and RSA-PSS signatures. Each identity claim is combined with a unique salt before hashing. The issuer signs only the deterministic serialized list of hashes, not the raw claims. During presentation, the holder may remove the raw `value` and `salt` for hidden claims while preserving their hashes. The verifier can still reconstruct the signed payload by recomputing disclosed claim hashes and reusing hidden claim hashes.

The project successfully demonstrates selective disclosure and tamper detection in a simple issuer-holder-verifier trust triangle. It does not claim full unlinkability or production-grade anonymity, but it provides a clear technical foundation for understanding privacy-preserving credentials.

## Table of Contents

1. Introduction
2. Concept Clarification
3. Problem Definition
4. System Requirements
5. System Architecture
6. Cryptographic Design
7. Prototype Implementation
8. Verification Flow
9. Evaluation
10. Limitations
11. Future Work
12. Conclusion

## 1. Introduction

Digital identity systems increasingly need to balance trust, usability, and privacy. Traditional identity checks often reveal more personal data than necessary. For example, a verifier may only need to know that a person has a valid status or is above a certain age, yet a conventional identity document may expose name, address, birth date, and other unrelated information.

Self-Sovereign Identity attempts to improve this model by giving the holder control over how credentials are stored and presented. In an SSI ecosystem, credentials are issued by trusted issuers, stored by holders, and verified by relying parties or verifiers. The holder decides which information to disclose during a transaction.

This project implements a local simulation of that model using three separate Django projects:

- Issuer Server Core: `http://127.0.0.1:8001`
- Holder Device Wallet: `http://127.0.0.1:8002`
- Verifier Audit Node: `http://127.0.0.1:8003`
- Trusted Registry: `http://127.0.0.1:8004`

The purpose is to show how selective disclosure can be achieved with salted hashes and digital signatures while keeping the three SSI roles decoupled.

## 2. Concept Clarification

**Claim**  
A claim is a statement about a subject, such as a name, age, role, or status.

**Verifiable Credential (VC)**  
A VC is a credential document issued by an authority. It contains claims and cryptographic proof that the issuer signed the credential.

**Verifiable Presentation (VP)**  
A VP is created by the holder from one or more credentials. It contains the information the holder chooses to present to a verifier.

**Issuer**  
The issuer creates credentials and signs them. In this project, the issuer signs salted claim hashes using RSA-PSS.

**Holder**  
The holder receives and stores credentials. The holder decides which claims are disclosed to the verifier.

**Verifier**  
The verifier checks whether a presentation is valid by reconstructing the signed payload and verifying the issuer signature.

**Selective Disclosure**  
Selective disclosure allows the holder to reveal only chosen attributes while hiding the remaining attributes.

**Salt**  
A salt is a random value added to a claim before hashing. It prevents simple dictionary attacks against predictable values.

**Commitment**  
A commitment is a cryptographic representation of data. In this system, each claim commitment is `SHA256(value + salt)`.

## 3. Problem Definition

The project addresses the following problem:

How can a holder prove that a credential was issued by a trusted issuer while revealing only selected identity attributes?

The implementation must satisfy three core properties:

1. The verifier must be able to detect tampering.
2. The holder must be able to hide selected claim values.
3. The issuer, holder, and verifier must operate as separate services.

## 4. System Requirements

### 4.1 Functional Requirements

- The issuer must accept claims and issue a signed credential.
- Each claim must receive a unique cryptographic salt.
- Each claim must be hashed using `SHA256(value + salt)`.
- Claim hashes must be sorted deterministically before signing.
- The issuer must sign the serialized payload using RSA-PSS.
- The holder must store received credentials.
- The holder must generate selective presentations.
- Hidden claims must retain only their hash.
- The verifier must fetch the issuer public key.
- The verifier must validate the RSA-PSS signature.
- The verifier must return a clear valid or invalid result.

### 4.2 Security Requirements

- Raw hidden values must not be sent to the verifier.
- Salts for hidden values must not be sent to the verifier.
- Signatures must be verified with the issuer public key.
- Verification failures must be handled safely.
- Cross-origin communication must be restricted by service role.

### 4.3 Deployment Requirements

The system runs as four independent Django services:

| Role | Port | Main Interface |
| --- | --- | --- |
| Issuer | `8001` | `/admin/dashboard/` |
| Holder | `8002` | `/wallet/ui/` |
| Verifier | `8003` | `/api/v1/verify/` |
| Trusted Registry | `8004` | `/` |

## 5. System Architecture

The architecture follows the classic SSI trust triangle.

```text
Issuer
  |
  | issues signed Verifiable Credential
  v
Holder
  |
  | creates selective Verifiable Presentation
  v
Verifier
  |
  | fetches public key
  v
Issuer
```

The issuer and verifier do not directly exchange user data. The holder acts as the privacy boundary and controls which attributes are disclosed.

### 5.1 Issuer Server Core

The issuer is responsible for:

- Receiving identity claims.
- Generating claim salts.
- Computing salted hashes.
- Sorting hashes deterministically.
- Signing the serialized hash payload.
- Returning a Verifiable Credential.
- Publishing the issuer public key.

### 5.2 Holder Device Wallet

The holder is responsible for:

- Receiving credentials from the issuer.
- Persisting credentials in SQLite.
- Showing credential claims in a wallet UI.
- Allowing the user to choose disclosed claims.
- Removing hidden claim values and salts.
- Sending the resulting presentation to the verifier.

### 5.3 Verifier Audit Node

The verifier is responsible for:

- Receiving a Verifiable Presentation.
- Fetching the issuer public key.
- Recomputing hashes for disclosed claims.
- Reusing hashes for hidden claims.
- Reconstructing the deterministic payload.
- Verifying the RSA-PSS signature.
- Recording recent verification attempts.

## 6. Cryptographic Design

The issuer follows this pipeline:

```text
Claims
   |
   v
Salt Generation
   |
   v
SHA256(value + salt)
   |
   v
Deterministic Sorting
   |
   v
Payload Serialization
   |
   v
RSA-PSS Signature
   |
   v
Verifiable Credential
```

### 6.1 Salt Generation

Each claim receives an independent salt:

```text
salt = secrets.token_hex(16)
```

This produces a 16-byte random salt encoded as hexadecimal.

### 6.2 Claim Hashing

Each claim is transformed into a commitment:

```text
hash = SHA256(value + salt)
```

The salt ensures that equal values do not produce equal hashes unless the same salt is reused.

### 6.3 Deterministic Sorting

All claim hashes are sorted alphabetically before signing. This ensures that issuer and verifier derive the same payload even if dictionary key order changes during JSON transport.

### 6.4 Payload Serialization

The sorted hashes are serialized into one string using a null-byte delimiter:

```text
payload = hash_1 + "\x00" + hash_2 + "\x00" + hash_3
```

The delimiter prevents ambiguous concatenation.

### 6.5 RSA-PSS Signature

The issuer signs the serialized payload using:

- RSA key size: 2048 bits
- Public exponent: 65537
- Padding: PSS
- MGF: MGF1 with SHA-256
- PSS salt length: maximum
- Signature transport format: hexadecimal

The signature binds the complete set of claim commitments to the issuer.

## 7. Prototype Implementation

### 7.1 Issuer Implementation

The issuer project contains:

- `CredentialType`
- `IssuerKeyPair`
- Credential issuing endpoint
- Public key endpoint
- Issuer dashboard

The main endpoint is:

```text
POST /api/v1/issue/
```

Example input:

```json
{
  "claims": {
    "student_name": "Nischal Ghimire",
    "student_id": "TU20250001",
    "degree_title": "Bachelor of Computer Science",
    "university_name": "Tribhuvan University",
    "graduation_year": "2026",
    "department": "Computer Science",
    "grade_summary": "First Division"
  }
}
```

Example claim block inside the issued credential:

```json
{
  "value": "27",
  "salt": "random_hex_salt",
  "hash": "sha256_digest"
}
```

The issuer dashboard allows the user to enter claims and click **Sign & Export**. The generated credential is automatically sent to the holder wallet.

### 7.2 Holder Implementation

The holder project contains:

- `WalletCredential`
- Credential receive endpoint
- Presentation generation endpoint
- Wallet dashboard

The receive endpoint is:

```text
POST /api/v1/wallet/receive/
```

The presentation generation endpoint is:

```text
POST /api/v1/wallet/presentation/generate/
```

The holder uses a destructive redaction process. If a claim is not selected for disclosure, its raw `value` and `salt` are removed:

```json
{
  "hash": "existing_claim_hash"
}
```

This allows the verifier to include the hidden claim in signature verification without learning the hidden value.

### 7.3 Verifier Implementation

The verifier project contains:

- Verification endpoint
- Public key fetch logic
- Hash reconstruction logic
- Signature verification logic
- Audit UI

The verification endpoint is:

```text
POST /api/v1/verify/
```

On browser visits, the same URL displays a simple verifier page with recent verification checks.

## 8. Verification Flow

When the verifier receives a presentation, it performs the following steps:

1. Parse the VP document.
2. Extract the embedded VC.
3. Read the issuer URL.
4. Fetch the issuer public key from:

```text
http://127.0.0.1:8001/api/v1/pki/public-key/
```

5. Iterate through credential claims.
6. For disclosed claims, recompute:

```text
SHA256(value + salt)
```

7. For hidden claims, use the provided hash.
8. Sort all evaluated hashes.
9. Serialize the payload using the same delimiter.
10. Decode the hex signature.
11. Verify the RSA-PSS signature.
12. Return a result.

Successful response:

```json
{
    "valid": true,
    "disclosed_claims": {
    "student_name": "Nischal Ghimire",
    "degree_title": "Bachelor of Computer Science",
    "university_name": "Tribhuvan University"
  }
}
```

Failed response:

```json
{
  "valid": false,
  "reason": "RSA-PSS signature verification failed."
}
```

## 9. Evaluation

### 9.1 Selective Disclosure

The prototype supports selective disclosure. The holder can decide which claims are visible to the verifier. Hidden claims are represented only by their hash.

This means the verifier can validate the integrity of the complete credential without seeing every raw claim.

### 9.2 Tamper Detection

The system detects tampering. If a disclosed value or salt is changed, the recomputed hash no longer matches the original signed hash. If a hidden hash is changed, the final serialized payload changes. In both cases, RSA-PSS verification fails.

### 9.3 Decoupled Trust Triangle

The issuer, holder, and verifier are implemented as separate Django projects and run on separate ports. This supports the intended SSI separation of roles.

### 9.4 User Control

The holder wallet gives the user direct control over which attributes are disclosed. This demonstrates the main privacy goal of selective disclosure.

### 9.5 Practicality

The system is practical as a local educational prototype. It uses common web technologies and standard cryptographic primitives available in Python.

## 10. Limitations

### 10.1 Not Full Anonymous Credentials

This project demonstrates selective disclosure, but it does not implement full anonymous credentials. More advanced systems may use BBS+, CL signatures, or zero-knowledge proofs to provide stronger unlinkability.

### 10.2 Hidden Claims Are Still Commitment-Revealed

The verifier sees hashes for hidden claims. While salts protect against simple guessing attacks, this is still not equivalent to a zero-knowledge proof.

### 10.3 Revocation Registry (Prototype)

This prototype includes a simple local revocation registry. The trusted registry service exposes endpoints to revoke credentials, check revocation status, and list revoked credentials (`/api/v1/registry/revocation/revoke/`, `/api/v1/registry/revocation/check/`, `/api/v1/registry/revocation/list/`). The issuer UI and server call the registry to record revocations, and the verifier queries the registry during verification to detect revoked credentials. See [trusted_registry/registry_app/views.py](trusted_registry/registry_app/views.py), [issuer_core/issuer_app/registry.py](issuer_core/issuer_app/registry.py), and [verifier_node/verifier_app/utils.py](verifier_node/verifier_app/utils.py) for the implementation details.

Example workflow (issue → revoke → check):

Start all services from the project root:

```powershell
.\run_all_services.ps1
```

Ensure holder keys are registered (this endpoint also creates default holders):

```bash
curl http://127.0.0.1:8002/api/v1/wallet/holders/
```

Issue a credential (example using `curl`):

```bash
curl -X POST http://127.0.0.1:8001/api/v1/issue/ \
  -H "Content-Type: application/json" \
  -d '{"claims":{"student_name":{"value":"Test Student"}},"holder":{"id":"student_001","url":"http://127.0.0.1:8002","key_id":"default"}}'
```

Sample successful response includes the issued credential `id`, e.g.:

```json
{"id":"urn:uuid:7e83cac1-cc04-4add-a8a2-6ce45a5007fd", ...}
```

Revoke the credential via the issuer API:

```bash
curl -X POST http://127.0.0.1:8001/api/v1/revoke/ \
  -H "Content-Type: application/json" \
  -d '{"credential_id":"urn:uuid:7e83cac1-cc04-4add-a8a2-6ce45a5007fd","reason":"Test revoke"}'
```

Check the registry revocation status:

```bash
curl "http://127.0.0.1:8004/api/v1/registry/revocation/check/?credential_id=urn:uuid:7e83cac1-cc04-4add-a8a2-6ce45a5007fd"
```

Sample registry response indicating the credential is revoked:

```json
{"revoked":true,"credential_id":"urn:uuid:7e83cac1-cc04-4add-a8a2-6ce45a5007fd","revocation_reason":"Test revoke",...}
```

### 10.4 Holder Binding (Implemented, with caveats)

The prototype includes a holder-binding mechanism: when the issuer issues a credential it embeds holder binding metadata in `credentialSubject.holder` (holder `id`, `url`, `keyId`, and a `publicKeyFingerprint`). The holder wallet generates an RSA keypair on first use, stores the keypair locally, and registers the public key with the trusted registry. When creating a Verifiable Presentation the wallet signs the presentation payload with the holder private key and includes a `holderProof` object containing the signature, `keyId`, and the holder public key fingerprint. The verifier fetches the holder public key from the trusted registry and verifies the `holderProof` before accepting the presentation.

This provides basic proof-of-possession and ties the credential to a holder key, but several practical limitations remain:

- Replay protection: presentations include a `created` timestamp but there is no interactive nonce or verifier-supplied challenge in the current protocol. An intercepted presentation could be replayed by an attacker. Mitigation: implement challenge-response (verifier nonce) or include a short-lived audience/nonce field in the signed payload.
- Key compromise and rotation: if a holder private key is stolen the attacker can present credentials. Mitigation: add holder key revocation/rotation (registry support already exists for revoking credentials and trusted keys; holder key lifecycle flows can be implemented on top of the registry).
- Privacy vs. binding tradeoff: stronger holder binding (e.g., long-term holder public keys) increases linkability across presentations. Consider ephemeral holder keys or anonymous-credential constructions (BBS+, CL signatures, ZK proofs) if unlinkability is required.

See `holder_wallet/holder_app/redaction.py` for presentation generation, `holder_wallet/holder_app/registry.py` for holder key registration, and `verifier_node/verifier_app/utils.py` for trusted key resolution and holder proof verification.

### 10.5 Local Trust Boundary

The system uses fixed local URLs and simplified trust assumptions. A production deployment would require TLS, authenticated registry endpoints, key rotation, and stronger origin controls. The prototype is intentionally constrained to a local trust boundary for educational clarity.

## 11. Future Work

The prototype demonstrates many SSI concepts but remains a local educational system. Priorities for future improvement include:

- Robust replay protection and interactive verification: add verifier nonces / challenge-response into the presentation flow so the holder signs a verifier-supplied nonce to prove liveness.
- Holder key lifecycle management: add explicit key rotation and revocation APIs and UI (holder-initiated rotation, registry-marked revocation, and issuer/verifier handling of rotated keys).
- Registry hardening: migrate from a local trusted registry to a production-ready service with TLS, authentication, audit logging, and possibly distributed consensus for trust anchoring.
- Privacy-enhancing credentials: investigate anonymous credential schemes (BBS+, CL) or selective disclosure techniques with unlinkability guarantees.
- Expiration and status semantics: add expiration fields to credentials and standardize status checks (revocation vs. suspension vs. expiration).
- Better UX and security: add user authentication for the wallet UI, explicit consent flows, and clearer error handling.
- Operational tooling: provide Docker compose or Kubernetes manifests, CI integration, and `manage.py` commands for administrative tasks (create-holder, rotate-key, import/export keys).
- Tests and automation: expand automated integration tests that exercise the full issue → hold → present → verify → revoke cycle.

Completed items since the initial prototype (already implemented): holder key registration, wallet add-holder UI, revocation registry and verification checks, issuer/holder/verifier separation, and an example end-to-end test harness used during development.

## 12. Conclusion

This project implements a working SSI selective disclosure prototype using four independent Django services. The issuer creates salted claim commitments, binds the credential to a holder public key fingerprint, and signs a deterministic payload using RSA-PSS. The holder stores credentials and generates redacted presentations signed with the holder private key. The verifier reconstructs the signed payload, resolves trusted public keys from the registry, verifies the issuer signature, and verifies the holder signature without requiring hidden claim values.

The prototype shows that salted commitments and digital signatures can support basic selective disclosure and tamper detection. However, the approach does not provide full unlinkability or complete anonymous credential functionality. It is best understood as a clear educational foundation for SSI concepts rather than a final privacy-preserving identity system.

## Appendix A: Running the Prototype

Start all services from the project root:

```powershell
.\run_all_services.ps1
```

Open the issuer dashboard:

```text
http://127.0.0.1:8001/admin/dashboard/
```

Open the holder wallet:

```text
http://127.0.0.1:8002/wallet/ui/
```

Open the verifier:

```text
http://127.0.0.1:8003/api/v1/verify/
```


## Appendix B: Main Source Files

Issuer:

- `issuer_core/issuer_app/crypto.py`
- `issuer_core/issuer_app/views.py`
- `issuer_core/issuer_app/models.py`

Holder:

- `holder_wallet/holder_app/redaction.py`
- `holder_wallet/holder_app/views.py`
- `holder_wallet/holder_app/models.py`

Verifier:

- `verifier_node/verifier_app/utils.py`
- `verifier_node/verifier_app/views.py`
- `verifier_node/verifier_app/models.py`

## Appendix D: Comprehensive Technical Summary

This appendix collects a complete, detailed reference of the implementation: service endpoints, data models, important functions, UI behaviors, file locations, and recommended checks. It is intended as a single-source technical summary for maintainers and reviewers.

1) Services and base commands
- Start all services (project root):

```powershell
.\run_all_services.ps1
```

- Individual Django service runners (from each project folder):

```powershell
# Registry
cd trusted_registry
python manage.py migrate
python manage.py runserver 127.0.0.1:8004

# Issuer
cd issuer_core
python manage.py migrate
python manage.py runserver 127.0.0.1:8001

# Holder wallet
cd holder_wallet
python manage.py migrate
python manage.py runserver 127.0.0.1:8002

# Verifier
cd verifier_node
python manage.py migrate
python manage.py runserver 127.0.0.1:8003
```

2) API Endpoints (by service)

- Trusted Registry (`127.0.0.1:8004`)
  - `GET  /api/v1/registry/keys/` — List trusted keys.
  - `POST /api/v1/registry/keys/register/` — Register or update a trusted key (issuer/holder/verifier).
  - `GET  /api/v1/registry/keys/resolve/?entity_url=...&entity_role=...&key_id=...` — Resolve the latest active trusted key for an entity.
  - `POST /api/v1/registry/revocation/revoke/` — Record a credential revocation (`credential_id`, `issuer_url`, `revocation_reason`, `revoked_by`).
  - `GET  /api/v1/registry/revocation/check/?credential_id=...` — Check if a credential is revoked.
  - `GET  /api/v1/registry/revocation/list/` — List revoked credentials (optionally filter by `issuer_url`).

- Issuer (`127.0.0.1:8001`)
  - `GET  /admin/dashboard/` — Issuer dashboard UI (issue/revoke forms).
  - `POST /api/v1/issue/` — Issue a Verifiable Credential. JSON body: `claims` (object), `holder` (object with `id`, `url`, `key_id`). Returns the VC JSON.
  - `GET  /api/v1/pki/public-key/` — Return current issuer public key and fingerprint.
  - `POST /api/v1/revoke/` — Revoke an issued credential (calls registry).

- Holder Wallet (`127.0.0.1:8002`)
  - `GET  /wallet/ui/` — Wallet UI.
  - `GET  /api/v1/wallet/holders/` — List all holders (created and defaults), returns `holder_id`, `display_name`, `holder_url`, `key_id`, `public_key_fingerprint`.
  - `POST /api/v1/wallet/holders/create/` — Create a new holder profile, generate keypair, and attempt to register the public key at the registry.
  - `GET  /api/v1/wallet/holders/<holder_id>/public-key/` — Return holder public key details.
  - `GET  /api/v1/wallet/credentials/` — List credentials stored in the wallet.
  - `POST /api/v1/wallet/receive/` — Receive an issued credential (issuer forwards VC here).
  - `POST /api/v1/wallet/presentation/generate/` — Build a selective presentation. Body: `wallet_id`, `disclosed_keys`.

- Verifier (`127.0.0.1:8003`)
  - `POST /api/v1/verify/` — Verify a presentation. Returns `valid` boolean and disclosed claims or a reason.
  - `GET  /api/v1/verify/audits/` — List recorded audit events (recent verification attempts).

3) Database models (summary)

- Trusted Registry (`registry_app/models.py`)
  - `TrustedKey`:
    - entity_name, entity_url, entity_role (issuer|holder|verifier), key_id, key_type, algorithm, public_key_pem, public_key_fingerprint, active, created_at, updated_at
    - Unique constraint on (entity_url, entity_role, key_id)
  - `RevokedCredential`:
    - credential_id (unique), issuer_url, revocation_reason, revoked_by, revoked_at

- Issuer (`issuer_app/models.py`)
  - `IssuerKeyPair`:
    - label, private_key_pem, public_key_pem, active, created_at
  - `CredentialType`:
    - name, context_uri, schema_version, allowed_fields

- Holder (`holder_app/models.py`)
  - `HolderProfile`: holder_id (unique), display_name, email, created_at
  - `HolderKeyPair`: holder (OneToOne), key_id, private_key_pem, public_key_pem, public_key_fingerprint, active, created_at
  - `WalletCredential`: holder FK, credential (JSONField), issuer URL, credential_id, created_at

- Verifier (`verifier_app/models.py`)
  - Audit events to record verification attempts (timestamp, input, result, etc.). See file for schema details.

4) Cryptography and payload formats

- Key generation: RSA-2048 key pairs generated with `cryptography` library (PEM encoded), using RSA-PSS signatures with MGF1-SHA256.
- Claim protection: for each claim the issuer generates a random salt (`secrets.token_hex(16)`) and computes `hash = SHA256(value + salt)`.
- Payload for signing: sort claim hashes deterministically and join with the null character (`\x00`). If a holder binding exists append `holder:{holder_url}|{key_id}|{fingerprint}` then re-sort and join. The final byte payload is signed with RSA-PSS.
- Verifiable Credential structure: includes `credentialSubject` with `holder` metadata and `claims` where each claim block contains `value`, `salt`, and `hash` (holder may later remove `value` and `salt` for hidden claims).
- Presentation: the holder builds a `VerifiablePresentation` JSON, removes `value`/`salt` where hidden, adds `holderProof` with holder signature hex, key id, fingerprint, and creation time.

5) Important code paths (functions)

- Issuer (`issuer_app/crypto.py`):
  - `salt_and_hash_claims(claims)` — produce salted claim blocks.
  - `compile_hash_payload(claim_blocks, holder_binding)` — build byte payload to sign.
  - `sign_payload(payload, private_key_pem)` — produce hex signature.

- Holder (`holder_app/redaction.py`):
  - `validate_credential_structure(credential)` — assert credential shape.
  - `build_selective_presentation(credential, disclosed_keys, holder)` — build presentation with selective disclosure and sign with holder private key.

- Registry (`registry_app/views.py`):
  - `register_key` — update_or_create `TrustedKey`.
  - `resolve_key` — return the latest active `TrustedKey` record.
  - `revoke_credential` — update_or_create `RevokedCredential`.
  - `check_revocation` — query `RevokedCredential` by credential_id.

- Verifier (`verifier_app/utils.py`):
  - `fetch_trusted_public_key(entity_url, entity_role, key_id, expected_fingerprint)` — query registry and validate fingerprint.
  - `check_credential_revocation(credential_id)` — query registry revocation endpoint and raise if revoked.
  - `verify_presentation_document(presentation)` — full verification pipeline: revocation check, holder binding validation, claim evaluation, issuer signature verification, holder signature verification.

6) UI behavior notes

- Issuer UI (`issuer_app/templates/issuer_app/dashboard.html`):
  - Loads holders from `http://127.0.0.1:8002/api/v1/wallet/holders/` into a dropdown. Each option contains `data-display-name` and `data-url` attributes.
  - On holder selection the UI now sets `student_name` to the holder `display_name` and `student_id` to the holder id, and clears other form fields to avoid accidental reuse of stale values.
  - Issuer posts `claims` and `holder` to `/api/v1/issue/`. On success the credential is forwarded to the holder wallet `/api/v1/wallet/receive/`.

- Holder UI (`holder_app/templates/holder_app/wallet.html`):
  - Displays holder selector, a refresh button, and credentials grid.
  - Added inline "Add Student" form which POSTs to `/api/v1/wallet/holders/create/` to create a new holder profile and keypair. On success the holders list is refreshed and the new entry is selectable.
  - Disclosure toggles: these are now conservative — `student_name`, `degree_title`, and `university_name` are OFF by default (user must actively toggle them on to disclose).

7) Tests and example automation

- During development a quick Python snippet (using `requests`) was used to run an end-to-end smoke test:
  - Wait for registry to be available.
  - Fetch holders and select a holder.
  - Issue a credential (`POST /api/v1/issue/`).
  - Revoke the credential via issuer `POST /api/v1/revoke/`.
  - Query registry revocation `GET /api/v1/registry/revocation/check/` to assert `revoked: true`.

8) Security assessment and recommendations

- What is implemented:
  - Issuer signing with RSA-PSS, salted claim commitments, holder proof-of-possession signed presentations, registry-based trusted key resolution, revocation registry for credential status.

- Gaps and risks:
  - No interactive verification nonce (replay risk).
  - No formal holder key lifecycle UI for rotation/revocation (registry supports revocations for credentials and trusted keys, but workflows are not complete).
  - Local-only trust assumptions (no TLS or authentication on registry endpoints in prototype).
  - Linkability tradeoffs when using long-lived holder keys.

- Recommendations:
  - Add verifier challenge nonce in the Verify API and require holder to sign the nonce inside the presentation.
  - Add `HolderKeyRevocation` or extend `TrustedKey` semantics and UI for holder key rotation and revocation.
  - Harden registry endpoints (TLS, authentication) and add audit logs and permissions.
  - Add comprehensive integration tests for issue → receive → present → verify → revoke cycles.

9) Where to look in the code for details
- Issuer: `issuer_core/issuer_app/` (views.py, crypto.py, registry.py, templates)
- Holder: `holder_wallet/holder_app/` (views.py, redaction.py, registry.py, templates)
- Verifier: `verifier_node/verifier_app/` (utils.py, views.py)
- Registry: `trusted_registry/registry_app/` (models.py, views.py, urls.py)

Appendix C (Change Log) contains a timeline of feature additions made during development.

If you'd like I can now:
- produce a finalized `report-final.md` replacing `report.md` with this consolidated version, or
- commit all changes and create a Git tag and CHANGELOG entry summarizing the final status.
Which would you prefer? 

## Appendix C: Recent Modifications — Detailed Change Log

This section documents code and UI changes made while developing the prototype (revocation, holder management, and UI improvements), the rationale for each change, how to exercise them, and where to find the implementation.

1) Revocation registry and workflow
- Purpose: provide a simple trusted revocation registry so issuers can mark credentials as revoked and verifiers can detect revoked credentials during verification.
- Key files:
  - `trusted_registry/registry_app/models.py` — added `RevokedCredential` model to store revocations.
  - `trusted_registry/registry_app/views.py` — implemented endpoints:
    - `POST /api/v1/registry/revocation/revoke/` — record or update revocation for a credential.
    - `GET  /api/v1/registry/revocation/check/?credential_id=...` — query revocation status.
    - `GET  /api/v1/registry/revocation/list/` — list recent revoked credentials (optional issuer filter).
  - `trusted_registry/trusted_registry/urls.py` — routed the revocation endpoints.

  - Issuer integration: `issuer_core/issuer_app/registry.py` provides `revoke_credential()` which POSTs to the registry; `issuer_core/issuer_app/views.py` exposes `POST /api/v1/revoke/` (`revoke_issued_credential`) that calls this function.
  - Verifier integration: `verifier_node/verifier_app/utils.py` implements `check_credential_revocation(credential_id)` which queries the registry during presentation verification and fails verification if a revocation is returned.

  - How to exercise (example):
    1. Issue a credential from the issuer UI or API.
    2. Revoke it via the issuer revoke API:

```bash
curl -X POST http://127.0.0.1:8001/api/v1/revoke/ \
  -H "Content-Type: application/json" \
  -d '{"credential_id":"<CREDENTIAL_ID>","reason":"<reason>"}'
```

    3. Check registry:

```bash
curl "http://127.0.0.1:8004/api/v1/registry/revocation/check/?credential_id=<CREDENTIAL_ID>"
```

  - Sample result from an automated test run used during development:

```
Issued credential id: urn:uuid:7e83cac1-cc04-4add-a8a2-6ce45a5007fd
Revoke response: {'credential_id': 'urn:uuid:7e83cac1-cc04-4add-a8a2-6ce45a5007fd', 'issuer_url': 'http://127.0.0.1:8001', 'revocation_reason': 'Test revoke', 'revoked_by': 'Issuer Admin', 'revoked_at': '2026-05-31T11:12:05.138968+00:00'}
Registry check: {'revoked': True, 'credential_id': 'urn:uuid:7e83cac1-cc04-4add-a8a2-6ce45a5007fd', 'issuer_url': 'http://127.0.0.1:8001', 'revocation_reason': 'Test revoke', 'revoked_by': 'Issuer Admin', 'revoked_at': '2026-05-31T11:12:05.138968+00:00'}
```

2) Holder (wallet) management — add student wallet API and UI
- Purpose: allow adding new student wallets from the Holder UI without needing to use Django admin or the shell.
- Key changes:
  - `holder_wallet/holder_app/views.py` — added `create_holder` view (POST) which:
    - accepts `holder_id`, `display_name`, and `email`.
    - creates a `HolderProfile` and a `HolderKeyPair` (RSA keypair) if the holder is new.
    - calls `holder_wallet/holder_app/registry.register_holder_key()` to publish the public key to the trusted registry.
  - `holder_wallet/holder_wallet/urls.py` — added route `POST /api/v1/wallet/holders/create/`.
  - `holder_wallet/holder_app/templates/holder_app/wallet.html` — added an inline form to create a new student and client-side JS to POST to the new endpoint and then refresh the UI.
  - `holder_wallet/holder_app/registry.py` — utility already used to register holder public keys with the registry.

  - Behaviour: after creating a holder via the UI form, the wallet list is refreshed and the new student appears in the dropdown. The public key is registered with the trusted registry (unless the registry is unavailable; registration errors are returned by the API).

3) Holder listing and wallet UI defaults
- Issue found and fix: newly created holders were not showing in the wallet dropdown because `list_holders` returned only default demo holders. Fix: `holder_wallet/holder_app/views.py` now returns all `HolderProfile` records (and still ensures default holders exist), so newly created profiles appear in the API and UI.
- Wallet UI change: The default disclosure toggles have been made conservative — `student_name`, `degree_title`, and `university_name` are now OFF by default. File: `holder_wallet/holder_app/templates/holder_app/wallet.html` (changed `defaultDisclosures`).

4) Issuer UI behavior improvements
- Purpose: make it easier to issue credentials for a selected wallet and avoid accidentally sending stale values.
- Changes:
  - `issuer_core/issuer_app/templates/issuer_app/dashboard.html`:
    - the holder `<option>` now includes `data-display-name` so the UI can populate the `student_name` field automatically from the selected holder.
    - added a `change` handler on the holder dropdown that sets `student_name` to the holder display name and `student_id` to the selected holder id, and clears the other fields (`degree_title`, `university_name`, `graduation_year`, `department`, `grade_summary`) so the issuer always starts from a blank form when switching wallets.
    - Note: an earlier temporary change that populated degree/university defaults was reverted to preserve a blank form.

5) Testing, automation, and run scripts
- Services: `run_all_services.ps1` starts the four Django services (registry:8004, issuer:8001, holder:8002, verifier:8003), runs migrations, and runs servers in background jobs for developer convenience.
- Automated test performed during development: a small Python snippet (using `requests`) waited for services, issued a credential, revoked it, and queried the registry — the outputs are shown above.

6) Report updates
- `report.md` (this file) was updated to describe the revocation implementation and to include an example issue→revoke→check workflow with sample commands and responses.

7) Files changed (quick map)
- trusted_registry/registry_app/models.py — added `RevokedCredential`
- trusted_registry/registry_app/views.py — added revocation endpoints
- trusted_registry/trusted_registry/urls.py — added revocation routes
- issuer_core/issuer_app/registry.py — added `revoke_credential()` client
- issuer_core/issuer_app/views.py — added `revoke_issued_credential` view; updated issuer UI template (auto-fill/clear behavior)
- issuer_core/issuer_app/templates/issuer_app/dashboard.html — UI changes
- holder_wallet/holder_app/views.py — added `create_holder`; updated `list_holders` to return all records
- holder_wallet/holder_wallet/urls.py — added `holders/create/` route
- holder_wallet/holder_app/templates/holder_app/wallet.html — added add-holder form and JS; toggles default updated
- verifier_node/verifier_app/utils.py — checks revocation during verification
- report.md — updated with revocation note, workflow example, and this change log

8) How to manually verify the end-to-end flow
- Start services:

```powershell
.\run_all_services.ps1
```

- Create a holder from the wallet UI:
  - Open `http://127.0.0.1:8002/wallet/ui/`, fill `student_id`, `Display name`, optional email and click `Add Student`, then click `Refresh Wallet` (the UI automatically refreshes after creation).

- Issue a credential from the Issuer UI:
  - Open `http://127.0.0.1:8001/admin/dashboard/`, select the student in `Student Wallet` (form will clear and populate name/id), fill degree details and `Sign & Export`.

- The issuer will POST the signed credential to the holder wallet receive endpoint; check the holder admin or API `GET /api/v1/wallet/credentials/` to see the stored credential.

- Revoke the credential via the issuer revoke endpoint (see commands above) and verify the registry reports `revoked: true`.

If you want, I can also:
- add a short `manage.py` command to create holders from the command line, or
- persist default degree/university values in the holder profile and surface them in the issuer UI when selected.

If you'd like, I can now append this change log into the Git commit history and run a small test script that demonstrates creating a holder via the new form and issuing a credential programmatically — shall I proceed?
