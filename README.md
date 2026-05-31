# Decentralized SSI Selective Disclosure Demo

This workspace contains four independent Django projects that simulate a decoupled SSI ecosystem with holder proof-of-possession:

- Issuer Server Core: `http://127.0.0.1:8001`
- Holder Device Wallet: `http://127.0.0.1:8002`
- Verifier Audit Node: `http://127.0.0.1:8003`
- Trusted Registry: `http://127.0.0.1:8004`

This repository is a local demo of a decentralized Self-Sovereign Identity (SSI) system built with four independent Django services (Issuer, Holder wallet, Verifier, Trusted Registry). It includes selective disclosure, holder proof-of-possession, and a revocation registry.

## Setup

Install the shared Python dependencies once:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Initialize the stateful databases:

```powershell
cd issuer_core
python manage.py migrate
cd ..\holder_wallet
python manage.py migrate
cd ..\verifier_node
python manage.py migrate
cd ..\trusted_registry
python manage.py migrate
cd ..
```

## Run
Easiest way: use the provided orchestrator to start all services in development.

Start all services (PowerShell):

```powershell
.\run_all_services.ps1
```

Or start services individually in separate terminals:

```powershell
cd trusted_registry
python manage.py runserver 127.0.0.1:8004
```

```powershell
cd issuer_core
python manage.py runserver 127.0.0.1:8001
```

```powershell
cd holder_wallet
python manage.py runserver 127.0.0.1:8002
```

```powershell
cd verifier_node
python manage.py runserver 127.0.0.1:8003
```

## Flow

1. Visit `http://127.0.0.1:8001/admin/dashboard/`.
2. Select a student wallet, enter claims, and select `Sign & Export`.
3. The holder service registers student holder public keys with the trusted registry.
4. The issuer registers its public key, resolves the selected holder key from the registry, binds the credential to that holder fingerprint, signs the deterministic payload, and pushes the VC to `http://127.0.0.1:8002/api/v1/wallet/receive/`.
5. Visit `http://127.0.0.1:8002/wallet/ui/`.
6. Select the same student wallet, choose which claim values to disclose, then select `Compile Presentation & Submit`.
7. The holder removes hidden claim `value` and `salt` fields, keeps their hashes, signs the presentation with the holder private key, and submits the VP to `http://127.0.0.1:8003/api/v1/verify/`.
8. The verifier resolves issuer and holder public keys from `http://127.0.0.1:8004/`, verifies the issuer credential signature, verifies the holder presentation signature, and returns the result.

## What's New / Notes

- Revocation registry implemented and integrated: issued credentials can be revoked and the verifier checks revocation before accepting presentations.
- Holder creation API and UI: holders (student wallets) can be created via the wallet UI and the holder service registers holder public keys with the trusted registry.
- Issuer UI improvements: selecting a holder now auto-fills `student_name` and `student_id` and clears unrelated fields; this prevents accidental reuse of stale values.
- Wallet disclosure defaults: `name`, `degree title`, and `university name` disclosure toggles default to OFF for privacy by default.

## APIs (quick reference)

- Holder Wallet: `GET /api/v1/wallet/holders/` (list holders). Use the wallet UI to create a new holder; the service also exposes a create endpoint to register holder keys.
- Issuer: issue and revoke credential endpoints under the issuer service (see `issuer_core/issuer_app/views.py`).
- Trusted Registry: key registration, key resolution, and revocation/check endpoints live under the trusted registry service (see `trusted_registry/registry_app/views.py`).
- Verifier: presentation verification endpoint under the verifier service (see `verifier_node/verifier_app/views.py`).

For full API examples, sequence diagrams, code locations, and security recommendations see `report-final.md` in the repository root.

## Databases

Each service uses a local SQLite database file for development (e.g. `issuer_core/db.sqlite3`, `holder_wallet/db.sqlite3`).

## Next Steps

- Run `.\run_all_services.ps1` and open the services at the ports listed above.
- See `report-final.md` for detailed architecture, threat model, and API examples.

## CORS Boundaries

- `holder_wallet` only permits browser-origin requests from `http://127.0.0.1:8001`.
- `verifier_node` only permits browser-origin requests from `http://127.0.0.1:8002`.
- `trusted_registry` permits browser-origin requests from `http://127.0.0.1:8001`, `http://127.0.0.1:8002`, and `http://127.0.0.1:8003`.
- `issuer_core` exposes no cross-origin browser origins by default; key registration and lookup are server-side.
