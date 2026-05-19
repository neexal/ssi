# Decentralized SSI Selective Disclosure Demo

This workspace contains three independent Django projects that simulate the decoupled SSI trust triangle:

- Issuer Server Core: `http://127.0.0.1:8001`
- Holder Device Wallet: `http://127.0.0.1:8002`
- Verifier Audit Node: `http://127.0.0.1:8003`

## Setup

Install the shared Python dependencies once:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Initialize the two stateful databases:

```powershell
cd issuer_core
python manage.py migrate
cd ..\holder_wallet
python manage.py migrate
cd ..
```

The verifier is stateless, but running migrations there is harmless if you want the Django admin tables:

```powershell
cd verifier_node
python manage.py migrate
cd ..
```

## Run

Open three terminals:

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
2. Enter claims and select `Sign & Export`.
3. The issuer signs the deterministically sorted salted claim hashes and pushes the full VC to `http://127.0.0.1:8002/api/v1/wallet/receive/`.
4. Visit `http://127.0.0.1:8002/wallet/ui/`.
5. Choose which claim values to disclose, then select `Compile Presentation & Submit`.
6. The holder removes hidden claim `value` and `salt` fields, keeps their hashes, and submits the VP to `http://127.0.0.1:8003/api/v1/verify/`.
7. The verifier fetches the issuer public key from `http://127.0.0.1:8001/api/v1/pki/public-key/`, recomputes disclosed hashes, preserves hidden hashes, rebuilds the sorted payload, and verifies the RSA-PSS signature.

## CORS Boundaries

- `holder_wallet` only permits browser-origin requests from `http://127.0.0.1:8001`.
- `verifier_node` only permits browser-origin requests from `http://127.0.0.1:8002`.
- `issuer_core` exposes no cross-origin browser origins by default; verifier public-key retrieval is server-side.
