<!-- Implementation authorized by the user on 2026-11-14. See tasks.md and API/DEPLOYMENT.md for implemented scope and remaining live-service gates. -->
# KaKoRide requirements — v3 messaging-first

Date: 2026-11-14. Status: **user authorized implementation on 2026-11-14; local pilot implemented**.

Adopts the user's supplied WhatsApp/SMS proposal. Supersedes v2, preserved in `archive/requirements-v2-demand-intelligence.md`. The user subsequently authorized implementation; see tasks.md and the API deployment guide for the locally verified pilot and remaining real-provider/cloud gates.

## Product and scope

Passengers signal demand for free through WhatsApp or SMS, with no app, passenger website, registration, maps or GPS. Drivers sign into a responsive website and view aggregated demand on subscribed routes. Demand is not a booking, seat reservation or pickup guarantee. No driver acceptance, counteroffers, passenger contact, PINs, commission, ratings or live payments belong in this flow.

Target: reuse `kakoride/` React/TypeScript; add Python FastAPI on Cloud Run; one Firestore demand database; Firebase Hosting for the static driver UI and Firebase Authentication for drivers/admins. This supersedes the previous browser-only/no-server design. Existing OneRide Node/PostgreSQL code remains a separate legacy system, not a second source of demand truth. One reviewed Zambia route initially; current route seeds are illustrative, not verified live coverage.

## Passenger requirements

- **P1 WhatsApp:** verify Meta webhooks and use a deterministic conversation to collect boarding stop, destination and whole-kwacha fare per passenger. Default count is one; support explicit groups of 1–14. No generative AI dependency.
- **P2 SMS:** support `RIDE KAMWALA TOWN 20` and optional count (`RIDE KAMWALA TOWN 20 2`). Resolve configured stop aliases; clarify ambiguous names rather than guessing. Provide HELP, STATUS, CANCEL and STOP.
- **P3 Validation:** both stops must exist on an active route with boarding before destination. Fare K1–K1000 per passenger; count integer 1–14. Backend validates configurable bounds. Receipt states stops, fare, count and that no transport is reserved.
- **P4 Identity:** normalize the verified provider sender to E.164. No passenger password/profile. Use a keyed contact identifier privately; do not trust a caller-supplied phone number without provider authentication.
- **P5 Duplicate control:** one active request per contact across WhatsApp/SMS when sender numbers match. Repeated RIDE returns existing demand; changes require explicit confirmation. Different numbers cannot reliably be deduplicated as one human.
- **P6 Idempotency:** persist provider message IDs and atomically apply each effect once. Retries cannot create duplicate demand, renewals or completion. Bound message length, conversation duration, submissions and renewals. Report failed outbound delivery honestly.

## Reminder and expiry requirements

- **L1** Backend time defines active request creation, five-minute reminder and ten-minute expiry. Jobs survive browser closure and Cloud Run restart.
- **L2** At five minutes send “Have you boarded a bus? 1 Yes / 2 Still waiting”. Dispatch target is within one minute of due time; provider delivery is not guaranteed.
- **L3 YES:** complete the request and remove it from aggregates within the normal three-second refresh interval.
- **L4 STILL WAITING:** renew the same request once for that reply, increment its version, and set a fresh five-minute reminder/ten-minute expiry from backend receipt time.
- **L5 Silence:** exclude demand exactly at ten minutes from creation/last valid confirmation, regardless of cleanup or provider delivery. A delayed reminder does not extend the deadline.
- **L6** WhatsApp buttons carry request/version context. SMS bare 1/2 is accepted only for one unambiguous pending prompt; otherwise request a short code. Late, reordered or duplicate replies/jobs cannot change a replacement request. Expired demand requires an explicit new request/restart, not an old reply.
- **L7 CANCEL/STOP:** close active demand and suppress pending work. STOP also prevents future automated sends until explicit re-opt-in.

## Driver and subscription requirements

- **W1** Authenticated driver chooses an entitled route and manually sets current station. Preserve v2's rule: show only stops strictly after that station, excluding current/passed stops.
- **W2** Group by boarding stop and destination; show waiting passengers (sum of counts), distinct waiting boarding stops, fare summaries and total offered fares (fare × count). Proposed fares are not earnings or collected revenue. Each request counts at most once per compatible route; cross-route totals are not unique network-wide passenger counts.
- **W3** Server-generated aggregate snapshots refresh every three seconds while visible and immediately on station/route change. Show last update and stale/offline state. Expired totals must not continue to be asserted as live between refreshes.
- **W4 Privacy:** no phone number, contact key, message text, request ID or raw per-request entry reaches a driver payload/browser storage/Firestore read. Groups of one still reveal that somebody is waiting; do not claim statistical anonymity.
- **W5** Backend checks driver approval, active subscription, route membership and entitlement expiry on every read. Client-selected route IDs never grant access.
- **W6** MVP access is admin-granted or a clearly labelled, backend-gated simulated trial. No public self-grant or payment gateway. Previous K50/K120 plan examples remain illustrative, unapproved pricing.
- **W7** Restricted admin operations manage demo entitlements and provider/job health. Full geographic editors/reporting stay outside the first slice.

## Demonstration and release gates

- **A1** Development-only WhatsApp/SMS simulator uses the same normalization, conversations, validation, persistence, reminders and aggregation as real adapters. Label simulation and disable public production simulator endpoints.
- **A2** One actual WhatsApp **or** SMS request must appear in a separately authenticated driver browser, then disappear after a real boarding reply. Simulator-only success is not a real-channel demonstration. Exercise the second channel in simulation until provisioned.
- **A3** Test route direction, aggregates, contact/event duplicates, subscription denial, privacy, no-browser expiry, provider failure and restart recovery.
- **A4** Preserve legacy code/data without destructive migration. Do not describe existing credentials/config files as proof of successful provider delivery or cloud deployment.

Real integration needs owner-provisioned Meta/SMS accounts and Google project/billing. An Android SMS gateway also needs SIM, internet, power and airtime. Verify current provider prices in the account before budgeting; neither a free production service nor a fixed 4,000-credit outcome is guaranteed. Scope target: one route, deterministic conversation, one SMS adapter, manual/demo access and a real-channel demo.
