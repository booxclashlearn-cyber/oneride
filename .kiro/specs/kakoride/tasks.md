# KaKoRide tasks — v3 messaging-first

Date: 2026-11-14. Status: **implementation authorized by the user on 2026-11-14; local pilot implemented**.

The user subsequently instructed removal of legacy files and implementation. That instruction satisfies the earlier specification-review gate. Checked implementation items mean code/local verification, not live provider provisioning or cloud deployment. Previous checklist is preserved in `archive/tasks-v2-demand-intelligence.md`.

## Review completed

- [x] Inspect actual root OneRide and nested KaKoRide source and read the supplied proposal.
- [x] Preserve v2 requirements/design/tasks/testing documents in archive.
- [x] Draft messaging-first requirements, design, implementation phases and testing plan.
- [x] Record reuse, missing features, security/lifecycle gaps and validation in assessment-v3.md.
- [x] Run existing KaKoRide validation: 23 tests passed; type-check/Vite production build passed, with large-bundle warning.
- [x] User accepted progression by explicitly asking to remove legacy files and implement.

## Phase 1 — driver dashboard and shared engine, one route

- [x] Add FastAPI/config/health/readiness and Firestore emulator setup; preserve legacy data.
- [ ] Review route/stop order and aliases; create labelled synthetic test fixtures and explicit fare-unit conversion.
- [x] Implement authoritative matching, validation, transactional contact-level duplicate guard, idempotent intake, versioned lifecycle and injected clock.
- [x] Add aggregate-only driver API with Firebase token verification, approved role and route entitlement checks.
- [x] Reuse React primitives for driver login, entitled route/current-station controls, grouped counts/fares and last-update/stale state.
- [x] Add three-second refresh and server-time expiry filtering from the first slice.
- [x] Add development-only messaging simulator using the actual shared engine; no public passenger web form.
- [x] Test route direction, duplicate/concurrent events, count/fare totals, current/passed stops, exact expiry, privacy and entitlement denial.

## Phase 2 — WhatsApp

- [ ] Owner provisions Meta app/business number and confirms permitted messaging/billing.
- [x] Implement verified handshake/signature, normalized intake and delivery-receipt separation.
- [x] Add boarding/destination/fare/count conversation, receipt, HELP/STATUS/CANCEL/STOP.
- [x] Persist deduplicated outbox and record send/retry/delivery failures without false success.
- [x] Test real provider fixtures and forged/retried/malformed events without requiring live secrets in tests.
- [ ] Prove a real WhatsApp request appears in an independent authenticated driver browser.

## Phase 3 — SMS

- [ ] Provision/test Telerivet Android gateway or another two-way option; validate exact authenticated webhook/send contract.
- [x] Implement RIDE command, optional count, stop alias resolution and clarification replies.
- [x] Normalize numbers across channels and prove one active demand record per matching number.
- [x] Test delayed/ambiguous SMS responses, short request-code context, retries and sender throttling.
- [ ] Perform real basic-phone test when provisioned; label simulator coverage otherwise.

## Phase 4 — durable reminder delivery

- [x] Persist reminder jobs/generations, outbox and ten-minute deadline from initial request.
- [x] Add Cloud Tasks callbacks, authenticated Scheduler reconciliation and local worker command.
- [x] Implement five-minute prompt, YES removal, STILL WAITING renewal and silent expiry.
- [x] Recover crashes between commit/scheduling/send; retries/old callbacks cannot inflate demand or revive old requests.
- [x] Test provider outage, no-browser expiry, STOP and restart recovery with injected time.

## Phase 5 — access, deployment and demonstration

- [x] Add admin-granted/demo entitlements, expiry/revocation and explicitly simulated trials; no public self-grants/live payments.
- [x] Deny browser access to private Firestore data; test rules separately from backend IAM/authorization.
- [x] Document contact retention, consent/opt-out, redacted logs and secrets.
- [ ] Deploy React to Firebase Hosting and FastAPI to Cloud Run; record URLs only after verification.
- [ ] Show one real WhatsApp or SMS request and boarding reply changing driver totals; simulator-only is insufficient.
- [ ] Rehearse narrow-screen/offline/demo flow; record video and truthful README; run backend/UI/integration tests and production build.

## Scope guard

One route, deterministic conversations, one SMS adapter, aggregated snapshots and manual/demo subscriptions. No passenger native app, maps/GPS, bookings/PINs, commission, AI prediction or live payments. Approximately 4,000 credits is a scope target, not a verified estimate. Implement one tested phase at a time and make scope changes explicit if provisioning/integrations exceed the target.

## Current verification and limits

- [x] Final root test command: 25 backend tests (including real Firestore emulator and rules) plus 7 frontend tests passed. Production build/type-check and isolated Chrome rehearsal passed. See `kakoride/VERIFICATION.md`.

- [x] Real Chrome rehearsal: both simulated channels, cross-channel duplicate, aggregated totals, prompt/boarding/renewal/expiry, subscription gate and 390px layout; no browser errors.
- [x] Firestore emulator: atomic records/restart/duplicate intake and direct browser read denial. An intermittent emulator transaction lock timeout led to per-store contention coordination and bounded transient retries.
- [x] Frontend type-check and production build; lazy Firebase auth keeps initial application code below the former bundle warning.
- [ ] Actual Meta/Telerivet credentials, real message/boarding-reply demonstration, deployment/IAM and managed Scheduler/Tasks staging verification.
- [ ] Live operator review of illustrative route order, scaled Firestore repository/cost testing and production retention/abuse controls.
- [ ] Final legacy sensitive-data/generated-file deletion: automatic review blocked broad cleanup; preserved inactive files need explicit approval.
