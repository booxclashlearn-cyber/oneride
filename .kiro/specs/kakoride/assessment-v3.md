# KaKoRide direction review — 2026-11-14

## Decision proposed for review

Use the nested `kakoride/` React/Firestore prototype as the base for a messaging-first demand product. Passengers use WhatsApp/SMS without registration; subscribed drivers use a web dashboard. Add FastAPI on Cloud Run as the shared, authoritative intake/conversation/lifecycle/aggregate engine. Preserve root OneRide separately as legacy work. Review v3 requirements/design/tasks before implementation, as the supplied proposal requires.

## What is actually present

| Area | Evidence in the current workspace | Fit for the new direction |
|---|---|---|
| Root OneRide | Next.js admin website, Node HTTP API, PostgreSQL/PGlite schema, phone/password sessions, verification, GPS requests, counteroffers, PIN bookings, commission and ratings | Historical reference; ride-booking workflow and PostgreSQL store are outside the proposed demand MVP |
| Android | Root README/specs describe it, but no `android-app/` directory or `public/downloads/` APK was found during this audit | Earlier Android claims cannot be verified from current files; native passenger apps are superseded by the new brief |
| `kakoride/` frontend | Vite/React/TypeScript, reusable Button/Card/Badge, passenger request form and active/cancel view | Reuse UI foundation; replace passenger web entry with driver dashboard and development messaging simulator |
| Firestore | Firebase initialization, anonymous browser sessions, request listener, atomic browser batches, private request per UID and per-route demand copies | Existing integration code, not proof of deployed access/rules. New server-side messaging model changes ownership and write paths |
| Stops/routes | Ordered-stop helpers, forward destinations, two illustrative overlapping routes | Reuse concepts/test cases; review real stop order and introduce SMS aliases |
| Request lifecycle | Create/close/renew service functions; five-minute reminder/ten-minute expiry helpers | Reuse policy/test scenarios, not browser execution as scheduler |
| Duplicate guard | `requests/{anonymousUid}` plus browser `canSubmit` check | Per-session only; cannot prevent same-phone duplicates across channels/new sessions |
| Driver product | No driver screen, login, aggregate service or subscription implementation in current nested source | Build |
| Messaging/backend | No FastAPI, WhatsApp/SMS adapters, webhooks, outbound sender, durable jobs or channel simulator found | Build |

## Material gaps in the current prototype

1. `kakoride/README.md` described old tabs, PINs and Zustand despite the actual App rendering only PassengerHome. Documentation needed correction.
2. `ActiveRequest.tsx` says drivers can see demand, but there is no implemented driver dashboard in this prototype. That statement is not evidence of a connected driver experience.
3. Reminder helpers exist, but no reminder UI or outbound message dispatch/worker is wired up. Ten-minute filtering in browser logic is not a durable messaging lifecycle.
4. `firestore.rules` explicitly allows any signed-in user to read raw route-demand entries. Subscription gating and aggregate-only privacy are not implemented.
5. Route entries are client-written; the current rules do not enforce exact field whitelists, equality with a canonical active request, route/stop compatibility or the full lifecycle transitions described in v2. They must not be treated as completed production security.
6. A browser UID is not a stable WhatsApp/SMS contact identifier. Client-clock-derived deadlines and a client-side duplicate check need backend-authoritative replacement.
7. The existing ~795 kB minified JavaScript bundle triggers a Vite chunk-size warning. This is a performance issue to address when restructuring the driver UI, not a failed build.
8. Existing illustrative route data is not confirmed operating coverage; no real provider delivery or deployed Firebase/Cloud Run setup was verified in this review.

## Validation run during this audit

- Nested KaKoRide: `npm test` — **23 tests passed**, two files. Covers route/lifecycle/input logic and passenger form/active-card rendering; Firestore/provider integration is not exercised.
- Nested KaKoRide: `npm run build` — type-check and production build passed, with the bundle-size warning noted above.
- Root OneRide: **36 backend regression tests passed**. They validate legacy SQL behavior, not the new demand architecture.
- No cloud infrastructure, external messages, account changes, live data migration or application feature changes were performed. Tests use their existing synthetic fixtures.

## Reuse and implementation order

Reuse nested React styles/components, ordered-stop matching concepts and lifecycle test cases. Keep its Firestore project concept, but make new private demand writes server-only. Do not port acceptance/PIN/capacity/commission features into the new product.

After specification review:

1. One-route authenticated driver dashboard + aggregate API + shared-engine message simulator, with expiry/privacy/entitlement enforcement from the start.
2. Real WhatsApp conversation and verified webhook/outbound integration.
3. Modular two-way SMS gateway adapter with cross-channel deduplication.
4. Durable five-minute prompts, renewed windows, silent ten-minute expiry and restart recovery.
5. Provisioned real-channel demonstration, then deployment and production hardening.

Manual/demo entitlements prove subscription access without adding payments. Illustrative plan prices are not approved pricing. The 4,000-credit figure is a scope constraint, not a validated delivery guarantee.

## Provider and architecture checks

- Telerivet explicitly documents two-way Zambia SMS using an Android gateway/local SIM, internet and airtime. Provisioning and a real send/reply test are still required. [Telerivet Zambia](https://www.telerivet.com/product/messaging/country/zm).
- Twilio currently marks two-way SMS in Zambia unsupported. [Twilio Zambia guidance](https://www.twilio.com/en-us/guidelines/zm/sms).
- Meta's main pricing page required login in this audit; do not treat the pasted free-tier statement as a budget guarantee without checking the applicable account/rate card. [Meta pricing](https://developers.facebook.com/documentation/business-messaging/whatsapp/pricing).
- Firestore TTL can delete documents much later than their deadline. Use backend expiry filtering and durable messaging jobs; TTL only cleans storage. [Official TTL documentation](https://firebase.google.com/docs/firestore/ttl).

## Review gate

The supplied proposal says: “First update the requirements, architecture and task specifications. Do not write implementation code until the new specifications are reviewed.” The three canonical v3 files and testing plan are now the concrete review package. The current prototype remains unchanged pending that review.
