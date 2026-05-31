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

### 10.3 No Revocation Registry

The prototype does not include credential revocation. A production SSI system should support revocation lists, status lists, or another trusted registry.

### 10.4 No Holder Binding

The prototype does not prove that the presenter is the legitimate holder of the credential. A stronger implementation would bind the credential to a holder key and require proof of possession.

### 10.5 Local Trust Boundary

The system uses fixed local URLs and simplified trust assumptions. A production deployment would require TLS, key rotation, issuer registries, and stronger origin controls.

## 11. Future Work

Future improvements could include:

- Holder key binding.
- Credential revocation.
- Expiration handling.
- Issuer trust registry.
- Merkle proof paths instead of a sorted hash list.
- Zero-knowledge proof support.
- Stronger audit logging.
- User authentication for the wallet.
- Docker-based orchestration.
- Automated integration tests.

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
