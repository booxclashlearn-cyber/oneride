<!-- Implementation authorized by the user on 2026-11-14. See tasks.md and API/DEPLOYMENT.md for implemented scope and remaining live-service gates. -->
# KaKoRide design — v3 messaging-first

Date: 2026-11-14. Status: **implementation authorized on 2026-11-14; local pilot implemented**. Previous design is archived as `archive/design-v2-demand-intelligence.md`.

## Architecture and reuse

```text
WhatsApp ─ verified webhook ─┐
SMS ─ verified adapter ──────┼─ FastAPI / Cloud Run ─ Firestore
Dev simulator ─ dev auth ────┘          │
                                      ├─ conversation / shared demand engine
React driver web ─ Firebase token ─────┤  aggregate-only API / entitlement checks
Firebase Hosting                      └─ outbox / durable reminder jobs
```

Use `kakoride/` as the frontend base, with proposed `kakoride/api/` Python package after review. Reuse UI primitives, styles, route types, direction helpers and lifecycle test scenarios. Port authoritative logic to Python using shared fixture cases. Stop selection replaces GPS; messaging sender continuity replaces browser anonymous UID. Root OneRide Next.js/Node/PostgreSQL and its specs remain legacy references. No dual-write between old bookings and new Firestore demand.

Implementation update: `kakoride/api/` and the driver React UI now exist. Legacy OneRide/Supabase source and old Next.js configuration were removed at the user's request; only blocked inactive credentials/data/generated artifacts remain (see cleanup-pending.md). Local development uses an independent SQLite adapter; Cloud Run refuses local storage and uses private Firestore records. The bounded one-route Firestore repository serializes per-process contention, uses a revision transaction across records and retries transient conflicts. It is not a scaled indexed-demand repository; limits and remaining staging gates are documented in `kakoride/api/DEPLOYMENT.md`. The catalog currently demonstrates both directions of one illustrative corridor; live operator validation remains outstanding.

FastAPI verifies driver Firebase ID tokens, approved role and route entitlement. The server service account accesses Firestore through least-privilege IAM. Deny browser reads/writes to all new private demand/contact/entitlement collections; Admin SDK bypasses security rules, so backend authorization needs its own tests. React receives only catalog, own access state and aggregated demand.

## Proposed Firestore data model

| Collection | Contents | Access |
|---|---|---|
| routes / stops | Reviewed direction, ordered stop IDs, aliases, active flags | Sanitized API catalog |
| contacts/{contactKey} | Keyed HMAC of E.164 number, protected delivery address, consent/STOP state, active request pointer | Backend only |
| conversations/{contact_channel} | Collection step, draft, pending request/version, bounded lifetime | Backend only |
| demands/{randomId} | Contact key, stops, compatible routes, fareMinor, count, status, confirmationVersion, timestamps, expiresAt | Backend only |
| inboundEvents/{provider_id} | Message identity, accepted time, processing state, minimal retained data | Backend only |
| outbox/{logicalSendId} | Private recipient reference, message data, attempts/delivery state, generation/due time | Backend only |
| jobs/{request_version_kind} | Due time, current request/version, dispatch/lease state | Backend only |
| drivers/{authUid} | Approved role/status | Backend only |
| routeEntitlements/{driver_route} | Route, status, startsAt/expiresAt, manual/demo grant source | Backend only; sanitized own-access API |

Use backend timestamps and integer ngwee; whole-K input converts explicitly. Existing prototype fares are whole K and cannot be reinterpreted as ngwee silently. Define retention for contacts, completed demand and event bodies before production. No contact fields belong in aggregate documents/logs. Provider secrets and HMAC keys live in Secret Manager, never VITE_* variables. Firebase web config is not a server credential.

## Verified ingestion and idempotent effects

1. Verify each provider's handshake/signature/secret using raw bytes when required; bound payloads. Delivery receipts are not passenger requests.
2. Persist intake before acknowledging it. Retryable persistence failure must not acknowledge and lose a message.
3. Normalize verified sender, text/button reply, provider event ID/time/context into a shared event. Reject unknown types safely.
4. Transactionally consume the event, resolve contact's active pointer, mutate demand and create deterministic outbox/jobs. Firestore transaction callbacks must not send external messages because callbacks can retry.
5. Claim outbox work, send through adapters and record delivery/failure. Demand effects are idempotent; external exactly-once delivery cannot be promised after an ambiguous timeout.
6. Bind replies/jobs to the request generation. WhatsApp buttons encode context. Ambiguous/delayed SMS responses ask for a code. Same-number contact identity spans channels; different numbers and simulator identities are not proof of the same person.

Repeated RIDE returns existing active demand rather than inflating it. YES transitions active→completed; CANCEL/STOP transitions active→cancelled; expiry is authoritative at deadline. STILL WAITING increments the version and resets its timing window once per accepted event. Explicit restart after expiry creates a fresh request.

## Aggregation and timing

Query compatible active demand by route; enforce expiresAt > serverNow on the backend. Validate current station against the route and include only boarding positions strictly after it. Group by boarding/destination and sum passenger count and fareMinor × count. Each request counts once per route. Return names/IDs of stops, group totals, serverNow, generatedAt and nextExpiryAt only, never serialized private requests. Fully scan the bounded demo dataset or fail explicitly if a configured scan limit is exceeded; silent partial totals are unacceptable. Validate required indexes in emulator/staging.

React polls every three seconds while visible, refreshes on return/selection change and uses server time/nextExpiryAt to stop representing expired results as current between polls. Failed or delayed refreshes show a stale/disconnected state. Fare totals are offers, not guaranteed revenue.

## Durable jobs and reminders

Use deterministic Cloud Tasks jobs plus an authenticated Cloud Scheduler reconciliation sweep of persisted due jobs/outbox records. Local development uses an explicit worker with injected clock. Do not use browser timers or an in-process five-minute sleep as the production scheduler. Verify service-account token audience/issuer and authorization on internal callbacks; provider webhooks and driver tokens cannot authorize jobs.

Callbacks recheck request/version/status/expiry. Retries cannot repeat state transitions or revive old requests. Recover a crash after database commit but before external task creation through reconciliation. Bound retries/backoff and expose failures to admins. Target reminder dispatch within one minute of due time, plus provider delay; delayed sends do not extend demand automatically.

Firestore TTL is cleanup only, not the expiry mechanism: deletion is typically within 24 hours. Correct ten-minute exclusion must work even if cleanup/jobs are down. [Official TTL behavior](https://firebase.google.com/docs/firestore/ttl).

## Proposed endpoints

| Route | Authentication | Purpose |
|---|---|---|
| GET/POST /webhooks/whatsapp | Meta verification/signature | Handshake / verified intake |
| POST /webhooks/sms/{adapter} | Verified provider-specific secret/signature | SMS intake |
| GET /api/driver/routes | Firebase token + approved driver | Entitled catalog |
| GET /api/driver/demand?routeId=&currentStopId= | Driver + live route entitlement | Aggregated snapshot |
| GET /api/driver/access | Driver | Sanitized access state |
| POST /api/admin/entitlements | Admin | Manual/demo grants |
| POST /internal/jobs/... | Authorized service identity | Dispatch/reconcile jobs |
| /dev/messages and /dev/clock | Development mode + auth | Shared-engine simulator; absent in production |

CORS allows approved frontend origins; it is not authentication. Set payload limits, redacted errors and explicit retry behavior. No provider secret, private contact or driver token is returned in catalog/demand responses.

## Provider and hosting decisions

Meta Cloud API is the WhatsApp target. Verify current webhook contracts and permitted customer-service-window/template behavior against account configuration. A retry after an outage may be outside the allowed send window; record/suppress an unpermitted send rather than claim delivery. No pricing/free-tier promise is built into scope: the primary Meta pricing page required login during this review. [Meta pricing](https://developers.facebook.com/documentation/business-messaging/whatsapp/pricing).

Telerivet is the initial SMS candidate: its Zambia page supports an Android gateway with local SIM, internet and airtime. Its exact authenticated inbound/outbound contract still needs validation. Africa's Talking can be a later provisioned adapter; a sender ID alone is not a two-way number. [Telerivet Zambia](https://www.telerivet.com/product/messaging/country/zm). Twilio's Zambia guidance currently says two-way SMS is unsupported, so it is not the inbound SMS choice. [Twilio Zambia](https://www.twilio.com/en-us/guidelines/zm/sms).

Firebase Hosting serves React; Cloud Run hosts FastAPI and uses Firestore. Cloud Tasks/Scheduler/billing/provisioning are owner setup gates, superseding the prior Spark-only/no-custom-server assumption. Simulator proves internal behavior; acceptance needs a real incoming WhatsApp or SMS request and boarding reply reflected in the driver's browser.
