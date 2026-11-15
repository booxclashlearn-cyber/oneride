# KaKoRide API

Run from the repository root after `python -m pip install -r kakoride/api/requirements-dev.txt`:

```powershell
python -m uvicorn kakoride.api.app:app --host 127.0.0.1 --port 8080
# Separate terminal, for durable local reminder/outbox work:
python -m kakoride.api.worker
```

`npm run dev` starts both plus the React site. Defaults are development-only SQLite at `kakoride/api/.data/development.sqlite`. Data and clock offset survive restarts. The old root `.env.local` is never loaded. `scripts/dev-kakoride.mjs` reads only nonempty `KAKORIDE_*` settings from `kakoride/api/.env`; copy `.env.example` there if needed. Direct Python invocations use process environment variables, not an implicit dotenv loader.

```powershell
python -m pytest kakoride/api/tests -q
```

The tests use dedicated project-local temporary databases. `test_firestore.py` runs only when `FIRESTORE_EMULATOR_HOST` points to localhost. The official Firestore emulator now requires Java 21; set up the Firebase emulator and run with project `demo-kakoride`, port 8189, and `kakoride/firestore.rules`, then:

```powershell
$env:FIRESTORE_EMULATOR_HOST='127.0.0.1:8189'
python -m pytest kakoride/api/tests/test_firestore.py -q
```

The optional browser script `tests/e2e_browser.py` requires Playwright and installed Chrome, plus Vite running on 5173. It launches its own isolated API on 8091, uses synthetic messages, saves screenshots under ignored `.browser-artifacts/` and stops its API afterward. It does not send actual SMS/WhatsApp messages.

Production Firestore, account provisioning, provider webhooks, durable scheduling and hosting instructions are in [DEPLOYMENT.md](DEPLOYMENT.md).

For actual phone tests before cloud deployment, follow [PHONE-TESTING.md](PHONE-TESTING.md). `npm run dev` also starts a webhook-only listener at 8081; tunnel that port, never the development API at 8080.
