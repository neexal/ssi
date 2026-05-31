# Self-Sovereign Identity With Selective Disclosure — Final Technical Report

## Abstract

This document is a consolidated, detailed final report for the SSI selective-disclosure prototype implemented across four Django services: Issuer, Holder (wallet), Verifier, and Trusted Registry. It documents architecture, cryptographic design, data models, API reference with examples, UI behavior, implementation notes, tests performed, security considerations, and recommended next steps.

---

## 1. Overview

Services (local dev addresses):

- Issuer Server Core: http://127.0.0.1:8001
- Holder Device Wallet: http://127.0.0.1:8002
- Verifier Audit Node: http://127.0.0.1:8003
- Trusted Registry: http://127.0.0.1:8004

The system demonstrates salted commitments, deterministic payload signing, selective disclosure, holder proof-of-possession, and a revocation registry.

---

## 2. High-level Flow

```mermaid
flowchart LR
  Issuer[Issuer (8001)] -->|issue VC| Holder[Holder Wallet (8002)]
  Holder -->|present VP| Verifier[Verifier (8003)]
  Verifier -->|resolve / check| Registry[Trusted Registry (8004)]
  Issuer -->|register key| Registry
  Holder -->|register key| Registry
  Issuer -->|revoke| Registry
  Verifier -->|check revocation| Registry
```

---

## 3. Detailed Architecture & Files

- Issuer: `issuer_core/issuer_app/` — key files: `views.py`, `crypto.py`, `registry.py`, `templates/issuer_app/dashboard.html`.
- Holder wallet: `holder_wallet/holder_app/` — key files: `views.py`, `redaction.py`, `crypto.py`, `registry.py`, `templates/holder_app/wallet.html`.
- Verifier: `verifier_node/verifier_app/` — key files: `utils.py`, `views.py`.
- Trusted Registry: `trusted_registry/registry_app/` — key files: `models.py`, `views.py`, `urls.py`.
- Scripts: `run_all_services.ps1` runs all services locally and applies migrations.

---

## 4. Data Models (summary)

- TrustedKey (registry): entity_name, entity_url, entity_role, key_id, public_key_pem, public_key_fingerprint, active
- RevokedCredential (registry): credential_id, issuer_url, revocation_reason, revoked_by, revoked_at
- IssuerKeyPair: label, private_key_pem, public_key_pem, active
- CredentialType: name, context_uri, allowed_fields, schema_version
- HolderProfile: holder_id, display_name, email
- HolderKeyPair: holder FK (OneToOne), key_id, private_key_pem, public_key_pem, public_key_fingerprint
- WalletCredential: holder FK, credential JSON, issuer, credential_id
- Verifier audit: stores verification attempts and results

---

## 5. Cryptography & Payloads

- Keys: RSA-2048 PEM (private/public) using Python `cryptography`.
- Signature: RSA-PSS (MGF1-SHA256) signing of a deterministic byte payload.
- Claim protection: For each claim:
  - `salt = secrets.token_hex(16)`
  - `hash = SHA256(value + salt)`
- Signing payload: collect all claim hashes, sort deterministically, optionally append a holder binding string `holder:{holder_url}|{key_id}|{fingerprint}`, sort again, join with the null char `\x00`, sign that byte payload.
- VC structure: standard JSON with `credentialSubject` including `holder` metadata (`id`, `url`, `keyId`, `publicKeyFingerprint`) and `claims` where each claim is `{ value, salt, hash }`.
- VP structure: `VerifiablePresentation` that contains `verifiableCredential` with hidden claims (value/salt removed for hidden claims), plus `holderProof` containing the holder signature and metadata.

---

## 6. API Reference with Examples

This section lists the main endpoints and provides concrete `curl` examples and expected responses.

A. Registry: Trusted key management & revocation

1) Register or update a trusted key
- POST `/api/v1/registry/keys/register/`
- Body (JSON):

```json
{
  "entity_name": "Holder A",
  "entity_url": "http://127.0.0.1:8002/wallet/holders/student_001",
  "entity_role": "holder",
  "key_id": "default",
  "key_type": "RSA",
  "algorithm": "PSS-MGF1-SHA256",
  "public_key_pem": "-----BEGIN PUBLIC KEY-----\n...\n-----END PUBLIC KEY-----\n",
  "public_key_fingerprint": "<sha256-fingerprint>",
  "active": true
}
```

- Example `curl`:

```bash
curl -X POST http://127.0.0.1:8004/api/v1/registry/keys/register/ \
  -H "Content-Type: application/json" \
  -d @register.json
```

- Response: `201` with JSON payload describing `registered: true` and the saved key record.

2) Resolve a key (verification use)
- GET `/api/v1/registry/keys/resolve/?entity_url=...&entity_role=...&key_id=...`
- Example:

```bash
curl "http://127.0.0.1:8004/api/v1/registry/keys/resolve/?entity_url=http://127.0.0.1:8002/wallet/holders/student_001&entity_role=holder&key_id=default"
```

- Response: JSON with `trusted: true` and the public key PEM plus fingerprint.

3) Revoke a credential
- POST `/api/v1/registry/revocation/revoke/`
- Body:

```json
{
  "credential_id": "urn:uuid:...",
  "issuer_url": "http://127.0.0.1:8001",
  "revocation_reason": "Compromised",
  "revoked_by": "Issuer Admin"
}
```

- Example `curl`:

```bash
curl -X POST http://127.0.0.1:8004/api/v1/registry/revocation/revoke/ \
  -H "Content-Type: application/json" \
  -d '{"credential_id":"urn:uuid:...","issuer_url":"http://127.0.0.1:8001","revocation_reason":"Test revoke","revoked_by":"Issuer Admin"}'
```

- Response: `201` with revocation payload including `revoked_at` timestamp.

4) Check revocation status
- GET `/api/v1/registry/revocation/check/?credential_id=...`
- Example:

```bash
curl "http://127.0.0.1:8004/api/v1/registry/revocation/check/?credential_id=urn:uuid:..."
```

- Response when revoked:

```json
{
  "revoked": true,
  "credential_id": "urn:uuid:...",
  "issuer_url": "http://127.0.0.1:8001",
  "revocation_reason": "Test revoke",
  "revoked_by": "Issuer Admin",
  "revoked_at": "2026-05-31T..."
}
```

B. Issuer

1) Issue a credential
- POST `/api/v1/issue/`
- Body:

```json
{
  "claims": {
    "student_name": "Alice Example",
    "student_id": "S123",
    "degree_title": "BSc Computer Science",
    "university_name": "Example University",
    "graduation_year": "2026"
  },
  "holder": { "id": "student_001", "url": "http://127.0.0.1:8002", "key_id": "default" }
}
```

- `curl`:

```bash
curl -X POST http://127.0.0.1:8001/api/v1/issue/ \
  -H "Content-Type: application/json" \
  -d @issue.json
```

- Response: `201` with the full Verifiable Credential JSON. Important fields include `id` (URN), `credentialSubject` with `holder` metadata and `claims` blocks containing `value`, `salt`, and `hash`, and `proof` containing issuer signature.

2) Revoke issued credential (issuer-forwarding convenience)
- POST `/api/v1/revoke/` — calls registry `revoke_credential()` internally; body requires `credential_id` (and optional `reason`).

C. Holder Wallet

1) List holders
- GET `/api/v1/wallet/holders/`
- Response: array of existing holders including newly created ones.

2) Create holder (UI or API)
- POST `/api/v1/wallet/holders/create/`
- Body:

```json
{ "holder_id": "student_042", "display_name": "New Student", "email": "new@example.local" }
```

- Behavior: creates `HolderProfile`, generates an RSA keypair, persists a `HolderKeyPair`, attempts to register the public key with the registry, and returns the created holder data and registration result.

3) Receive credential
- POST `/api/v1/wallet/receive/` — call made by the issuer after issuing a credential. The wallet validates structure and persists the credential in `WalletCredential`.

4) Build presentation
- POST `/api/v1/wallet/presentation/generate/` with body `{ "wallet_id": <int>, "disclosed_keys": ["student_name","degree_title"] }`.
- Response: a `VerifiablePresentation` JSON including `holderProof`.

D. Verifier

1) Verify presentation
- POST `/api/v1/verify/` — the verifier performs:
  - optional revocation check on credential `id` via registry
  - holder binding validation (fetch holder public key via registry resolve URL)
  - recomputation of claim hashes for disclosed claims and reuse of hidden claim hashes
  - reconstruction of issuer signing payload and verification of issuer signature
  - verification of `holderProof` signature using holder public key
- Example `curl`:

```bash
curl -X POST http://127.0.0.1:8003/api/v1/verify/ \
  -H "Content-Type: application/json" \
  -d @presentation.json
```

- Response: JSON like `{ "valid": true, "holder": "http://127.0.0.1:8002/wallet/holders/student_001", "disclosed_claims": { ... } }` or `{ "valid": false, "reason": "..." }`.

---

## 7. UI Changes & UX Notes

A. Holder wallet UI (`wallet.html`)
- New "Add Student" inline form in the header to create new holders without using Django admin.
- Form POSTs to `/api/v1/wallet/holders/create/` and upon success refreshes the holder dropdown.
- Disclosure toggles default to off for sensitive fields: `student_name`, `degree_title`, `university_name` are intentionally OFF by default.

B. Issuer dashboard (`dashboard.html`)
- Holder selector now reads from holder wallet API and attaches `data-display-name` to options.
- On selection: `student_name` and `student_id` are auto-filled from the selected holder; other credential fields are cleared to avoid accidental reuse.

---

## 8. Tests Performed

- Service start: executed `run_all_services.ps1` to run all four services and applied migrations.
- End-to-end smoke test (scripted): waited for registry readiness, issued a VC, revoked it, and checked registry status programmatically. Output from the run demonstrates issue→revoke→check succeeded.
- Manual UI test: created a new holder via wallet UI form, verified it appears in holder dropdown, issued a credential to that holder, and created/verifed a presentation (basic flow).

---

## 9. Security Assessment

- Strengths:
  - Uses RSA-PSS signatures and salted claim hashes.
  - Holder proof-of-possession included and verified.
  - Registry-backed key discovery enables centralized trust decisions.
  - Revocation registry implemented and used in verification.

- Weaknesses and mitigations:
  - Replay risk: no verifier nonce — add challenge-response.
  - Key lifecycle: rotation and revocation UI for holder keys missing — extend registry semantics and add workflows.
  - Local deployment: registry endpoints are HTTP-only in this prototype; production must use TLS and authentication.
  - Linkability: long-lived holder keys allow correlating presentations — consider ephemeral keys or anonymous-credential schemes.

---

## 10. Recommended Next Steps

1. Add verifier nonce challenge to prevent replay attacks.
2. Implement holder key rotation and revocation workflows and UI.
3. Harden registry (TLS, auth, audit) and consider a distributed trust model.
4. Add integration tests for the full lifecycle and edge cases.
5. Consider privacy-preserving credential schemes if unlinkability is a project requirement.

---

## 11. Appendix: Useful Commands

Start all services:

```powershell
.\run_all_services.ps1
```

Create holder (CLI call example replacing with proper JSON file):

```bash
curl -X POST http://127.0.0.1:8002/api/v1/wallet/holders/create/ \
  -H "Content-Type: application/json" \
  -d '{"holder_id":"student_042","display_name":"New Student","email":"new@example.local"}'
```

Issue a credential (example):

```bash
curl -X POST http://127.0.0.1:8001/api/v1/issue/ \
  -H "Content-Type: application/json" \
  -d '{"claims":{"student_name":"Alice","student_id":"S42"},"holder":{"id":"student_042","url":"http://127.0.0.1:8002","key_id":"default"}}'
```

Revoke and check (example):

```bash
curl -X POST http://127.0.0.1:8001/api/v1/revoke/ -H "Content-Type: application/json" -d '{"credential_id":"urn:uuid:...","reason":"Test revoke"}'
curl "http://127.0.0.1:8004/api/v1/registry/revocation/check/?credential_id=urn:uuid:..."
```

---

## 12. Closing Notes

This `report-final.md` consolidates implementation details and up-to-date behavior discovered by reading the code. If you want, I can:

- Commit `report-final.md` and tag a release.
- Produce a shorter executive summary and slides.
- Generate sequence diagrams per endpoint or expand the API reference into an OpenAPI spec.

Tell me which follow-up action you prefer.
