# KaKoRide: Implementation Tasks (v2)
Status: **awaiting approval**. Ordered, small, each ends with passing tests. Budget guard: stop and ask if a phase looks like it needs more than planned.

## Phase 0 (prep, before code)
- [ ] 0.1 You create a free Firebase project (Spark), enable Anonymous and Email/Password auth, create Firestore (production mode), add a web app and send me the config values (not secrets). Optional: install Java 11+ for the emulator.
- [ ] 0.2 New public GitHub repo containing `kakoride/` + `.kiro/` only.
- [ ] 0.3 Add `.kiro/steering/kakoride.md` (product rules: not Uber, no PII, no GPS, mobile-first, tests required) so every Kiro session follows them.

## Phase 1: Passenger UI and request lifecycle (code complete; live Firebase check pending)
- [x] 1.1 Remove operator/booking/PIN/ledger code and the Zustand store; keep UI primitives.
- [x] 1.2 Add Firebase SDK, config via `VITE_*` env, anonymous sign-in hook.
- [x] 1.3 Passenger home: dropdowns, fare per passenger, count, big button. Active-request card with Cancel.
- [x] 1.4 Request lifecycle service: create, cancel, complete, still-waiting (renew), reactivate (single batch writes).
- [x] Tests: lifecycle, route direction, validation, duplicate blocking (17 unit) + form and active card (6 UI). 23 pass.
- [ ] 1.5 Live check against Firebase: needs Authentication enabled (Anonymous) and `firestore.rules` published. Not yet verified.
- Notes: first route data and pure matching functions were pulled forward from Phase 2. Phase 1 rules in `firestore.rules` have a TEMPORARY open read on route entries until Phase 5. Bundle is ~795 kB (Firebase); consider code-splitting the driver area in Phase 3/6.

## Phase 2: Route data and demand matching
- [ ] 2.1 Seed script/data: stops, two routes (Lusaka to Kafue + overlapping route), plans.
- [ ] 2.2 Pure functions `destinationsAhead`, `routesFor`, `aggregateDemand`.
- [ ] Tests: B to D ok, D to B rejected, multi-route, no double counting, passed stops hidden, expired ignored, totals (fare x count).

## Phase 3: Driver dashboard (real-time)
- [ ] 3.1 Driver sign-in, route picker, manual current-station selector.
- [ ] 3.2 Live listener on `routeDemand/{route}/entries`; stop cards with destination breakdown, totals and demand bars; aria-live.
- [ ] 3.3 1-second tick to drop expired entries locally.

## Phase 4: Reminder and expiry
- [ ] 4.1 Reminder modal at `nextReminderAt` (works after reload).
- [ ] 4.2 YES / NOT YET flows with extended expiry; expired screen + one-tap reactivate.
- [ ] 4.3 Dev-only "Simulate 5 minutes passing" (stripped from production build).
- [ ] Tests: reminder due logic, still-waiting extends window, expiry removes from demand, reactivation.

## Phase 5: Demo subscriptions and access control
- [ ] 5.1 Plans config, upgrade screen, simulated activation guarded by `config/demo`.
- [ ] 5.2 Firestore rules + `firestore.indexes.json` (if needed); driver route gating.
- [ ] 5.3 Rules tests on the emulator: unsubscribed driver denied, wrong route denied, expired subscription denied, passenger cannot read others' requests, bad stop order rejected, fare/count bounds, expiry window bounds.

## Phase 6: Testing, deployment, demo preparation
- [ ] 6.1 "Seed demo demand" dev button with fictional data; reset button.
- [ ] 6.2 UI test of the full flow against fake/emulated Firestore; production build and type-check.
- [ ] 6.3 Deploy to Firebase Hosting; two-session rehearsal (two browsers + phone) against the hosted project.
- [ ] 6.4 README: run, demo script, architecture, Kiro usage (specs, steering, tests), limitations.
- [ ] 6.5 Record a short demo video.

## Definition of done
`npm run build`, `npm test` and rules tests pass; the 10-step demo works across two independent sessions; no identity visible to drivers; README documents how Kiro specs/steering/testing were used.
