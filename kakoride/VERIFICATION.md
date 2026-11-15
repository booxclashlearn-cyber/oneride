# KaKoRide verification — 2026-11-14

## Passed

- **25 backend tests**, including actual Firestore-emulator transactions, persistence/reopening, concurrent duplicate intake and REST browser-read denial under the checked-in rules.
- Backend cases include grouping/direction/current station, fare/count limits, shared-phone cross-channel duplicates, guided conversation, five-minute jobs/ten-minute read-time expiry, version/code guards, STOP consent, reordered messages, failed-send recovery, acceptance vs delivery, admin grants, route expiry/denial, signed Meta/verified Telerivet fixtures, phone-less WhatsApp IDs, production-disabled simulator, request bounds, OIDC job authorization and task retry generations.
- **7 frontend tests**: aggregate presentation, fare formatting and stale/expiry/subscription-time filtering.
- **Production build/type-check passed**. Initial application JavaScript ~251 kB minified (~79 kB gzip), with Firebase authentication loaded separately; the former ~795 kB single-bundle warning is gone.
- **Chrome rehearsal passed** against a separate API/database: simulated SMS, shared-number WhatsApp duplicate, grouped counts/fares, five-minute prompts, WhatsApp boarding, SMS renewal, silent expiry, denied subscription, 390px no horizontal overflow and no browser errors.
- Desktop/mobile screenshots inspected; artifacts contain only synthetic identities under ignored `.browser-artifacts/`.
- Actual Google Cloud Tasks SDK accepted the constructed POST/OIDC payload locally. Validation created no cloud tasks.

A repeated Firestore concurrency run exposed an intermittent emulator transaction lock timeout. The bounded pilot store now coordinates same-process contention and retries transient conflicts. The full emulator suite passed after that change. This does not replace deployed multi-instance/load testing.

## Isolation

SQLite tests use project-local temporary files. Firestore tests require localhost FIRESTORE_EMULATOR_HOST and a fresh namespace in project demo-kakoride; tests refuse a remote hostname. The browser rehearsal starts/stops an API on 8091 with a unique SQLite file. It sends no real SMS/WhatsApp and reads no legacy credentials/database. The normal app uses 5173/8080 and its own persistent local database. Temporary emulator services were stopped after verification.

## Remaining gates

- Owner-provisioned Meta business number/token and Telerivet account/SIM/gateway, then actual phone request/boarding-reply validation.
- Google project/IAM/Firestore/Auth, Firebase Hosting/Cloud Run deployment, container execution and managed Scheduler/Cloud Tasks staging checks.
- Live operator review of illustrative routes, broader accessibility/offline/load QA, scaled indexed Firestore repositories and production retention/abuse controls.
- Legacy credential/data/generated artifact deletion: automatic approval review blocked broad cleanup; exact inactive paths are in `.kiro/specs/kakoride/cleanup-pending.md`.

No live provider delivery or deployed URL is claimed. Outbox `sent` means provider acceptance; delivery receipts are separate.
