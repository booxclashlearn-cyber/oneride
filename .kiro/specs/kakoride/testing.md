<!-- Implementation authorized by the user on 2026-11-14. See tasks.md and API/DEPLOYMENT.md for implemented scope and remaining live-service gates. -->
# KaKoRide testing — v3 messaging-first

Date: 2026-11-14. Draft alongside requirements/design; these are planned checks, not claims of implemented integrations. V2 strategy is archived.

| Layer | Required evidence |
|---|---|
| Existing React prototype | 23 existing Vitest tests and build/type-check; not proof of messaging, subscriptions or Firestore authorization |
| Backend logic | Injected-clock direction/alias/validation/aggregate tests; strict expiry; current/passed stop filtering |
| Firestore transactions | Concurrent cross-channel requests, contact active pointer, duplicate consumption and atomic outbox/jobs/generation tests |
| Provider adapters | Verified webhook fixtures, bad signatures, retries, unsupported payloads, delivery-status separation and failed sends |
| Driver API | Token/role/route entitlement denial; revoked/expired access; aggregate-only payloads and no contact/request identifiers |
| Durable workers | Restart/reconciliation, duplicate callback, stale generation, send failure, no-browser expiry and TTL-independent correctness |
| React driver UI | Route/station selection, grouped totals, server time/expiry, stale/offline and return refresh, access errors and no hidden PII |
| Real-channel demo | Actual WhatsApp or SMS request and boarding reply update another authenticated driver's browser |

Mandatory scenarios:

1. Repeated events and same-number WhatsApp/SMS requests count once; different numbers are not asserted to be the same human.
2. K20 × two people plus K25 × one produces three passengers and K65 proposed fares, not K65 earnings.
3. B→D matches A-B-C-D; D→B fails. Driver at B sees C's waiting passengers, not A's or B's.
4. Five-minute prompt is scheduled once logically; YES completes, STILL WAITING renews once for that reply/version.
5. Silence excludes demand at ten minutes even with all browsers closed and cleanup unavailable.
6. Delayed replies/jobs cannot change a replacement request; ambiguous SMS requires context.
7. STOP closes demand and suppresses automated sends until re-opt-in.
8. Network responses/browser storage contain no phone, contact key, message body, request ID or individual demand rows.
9. Forged webhooks/private Firestore access fail; subscription expiry is checked on every driver aggregate read.
10. Crash/provider failure preserves committed demand and pending jobs without false delivery claims.

Use isolated emulator data and synthetic contacts. Test Firestore Rules and backend authorization independently. Live credentials are unnecessary for unit tests; actual provider delivery remains a separately provisioned acceptance gate. Do not copy real contacts or silently migrate legacy PostgreSQL bookings into these fixtures.
