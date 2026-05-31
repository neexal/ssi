# Decentralized SSI Selective Disclosure Demo

This workspace contains four independent Django projects that simulate a decoupled SSI ecosystem with holder proof-of-possession:

- Issuer Server Core: `http://127.0.0.1:8001`
- Holder Device Wallet: `http://127.0.0.1:8002`
- Verifier Audit Node: `http://127.0.0.1:8003`
- Trusted Registry: `http://127.0.0.1:8004`

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

Open four terminals:

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

## CORS Boundaries

- `holder_wallet` only permits browser-origin requests from `http://127.0.0.1:8001`.
- `verifier_node` only permits browser-origin requests from `http://127.0.0.1:8002`.
- `trusted_registry` permits browser-origin requests from `http://127.0.0.1:8001`, `http://127.0.0.1:8002`, and `http://127.0.0.1:8003`.
- `issuer_core` exposes no cross-origin browser origins by default; key registration and lookup are server-side.
