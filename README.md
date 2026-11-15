# KaKoRide

WhatsApp and SMS for passengers. A private, aggregated demand dashboard for drivers.

## Run locally

Requires Node.js 22+ and Python 3.12+.

```powershell
python -m pip install -r kakoride/api/requirements-dev.txt
npm --prefix kakoride ci
npm run dev
```

Open **http://127.0.0.1:5173** and choose **Open demo dashboard**. The command starts the React site, FastAPI on port 8080, and a persistent local reminder worker. Local development uses a separate SQLite database under ignored `kakoride/api/.data/`; it requires no cloud account. Production uses Firestore and refuses SQLite.

Open the **Messaging simulator**. Use WhatsApp guided messages (Hi, boarding stop, destination, fare) or SMS `RIDE KAMWALA TOWN 20 [count]`. Request demand updates the driver totals; duplicate requests from the same synthetic sender across channels count once. Advance five minutes to generate a reminder, choose boarded/still waiting, and advance again to demonstrate expiry. Simulation is explicitly labelled and does not send real messages. Browser reloads preserve backend state.

Choose the local unsubscribed-driver account to test the access gate, or local admin tools to grant/revoke demo route access. No live subscription payments are processed.

## Implemented

- React/TypeScript driver dashboard: route and current-station controls, grouped destination demand, passenger counts, proposed fares, stale/expiry handling and responsive layout.
- Python FastAPI demand engine: verified messaging adapters, deterministic conversations, server-time lifecycle, transactional deduplication across matching phone numbers, consent/STOP, cancellation and versioned replies.
- Meta WhatsApp handshake/HMAC webhook and outbound text/buttons; modular Telerivet SMS form webhook/REST sender.
- Persistent jobs, leased retrying outbox, local worker, authenticated Cloud Scheduler sweep and optional Cloud Tasks reconciliation.
- Firebase driver authentication, server-enforced approval/route entitlements, manual admin grants and browser-denied Firestore data.
- Local simulator using the same engine as provider traffic, with isolated synthetic identities and test clock. Simulator endpoints/demo logins are absent in production.

No passenger app/account, GPS/maps, bookings, driver acceptance, PINs, commissions or live payments are part of the new product. Routes are illustrative until reviewed with an operator. Proposed fare totals are not guaranteed income.

## Tests and build

```powershell
npm test
npm run build
```

Backend tests use project-local temporary databases; an optional real Firestore-emulator test needs Java 21. Frontend tests cover aggregate presentation and freshness. The browser rehearsal covers both simulated channels, duplicate suppression, boarding, renewal, expiry, access denial and 390px layout. See [API documentation](kakoride/api/README.md) for exact commands.

## Connect real channels / deploy

See [deployment and provider setup](kakoride/api/DEPLOYMENT.md). Real messaging needs your Meta/Telerivet credentials and provisioned phone/gateway; cloud deployment needs your Google project/IAM/billing. These have not been created by this implementation. Firebase Hosting serves the built React app; Cloud Run hosts FastAPI with Firestore and durable scheduled jobs. Before the production build, set the actual HTTPS `VITE_API_BASE_URL` and Firebase web config. Never expose provider or Google service-account secrets in VITE variables.

The Firestore repository is deliberately bounded and serialized for a one-route pilot, not a high-volume production deployment. Review its documented capacity/cost/retention limits and verify real providers, IAM and scheduling in staging before a public launch.

## Workspace cleanup

Legacy OneRide/Supabase source, obsolete Next.js source configuration and the old passenger-browser flow were removed. Root commands/manifests now run KaKoRide only. Automatic cleanup review blocked deletion of old credentials, local database and generated/dependency artifacts; those files remain inactive and are not loaded by KaKoRide. They need separate explicit approval before permanent deletion. The filesystem workspace folder name itself has not been changed.

Active specifications: [.kiro/specs/kakoride/](.kiro/specs/kakoride/). The user's instruction to implement on 2026-11-14 supersedes the earlier specification-review gate.