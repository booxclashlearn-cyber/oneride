# KaKoRide: Design (v2, demand intelligence)
Status: **awaiting approval**

## 1. Architecture
```
 Passenger browser ──┐                    ┌── Firestore (real-time)
  (anonymous auth)   ├─ React + Vite + TS ┤    routes, stops, plans (read-only seed)
 Driver browser ─────┘   Firebase JS SDK  │    requests/{uid}            (passenger private)
  (email/password)       onSnapshot        │    routeDemand/{routeId}/entries/{uid} (anonymous demand)
                                           │    driverSubscriptions/{uid}, config/demo
                                           └── Security Rules enforce access, shape, time
 Hosting: Firebase Hosting (static build)
```
No custom server. Decisions that keep it small: Firebase Auth + Firestore + Hosting only; Zustand removed (Firestore listeners are the state); existing React components, Tailwind, Vitest reused.

## 2. Data model (Firestore)
| Path | Fields | Who can read / write |
|---|---|---|
| `routes/{routeId}` | name, direction, stopIds[] (ordered), active | read: anyone signed in. write: none (seeded) |
| `stops/{stopId}` | name, routeIds[] | read: anyone signed in. write: none |
| `plans/{planId}` | name, routeLimit, priceKwacha | read: signed in. write: none (configurable by editing seed) |
| `requests/{uid}` | boardingStopId, destinationStopId, farePerPassenger (int K), passengerCount, status `active/completed/cancelled/expired`, createdAt, lastConfirmedAt, nextReminderAt, expiresAt | owner only. doc id = anonymous uid, which gives "one active request per session" |
| `routeDemand/{routeId}/entries/{uid}` | boardingStopId, destinationStopId, farePerPassenger, passengerCount, expiresAt | create/update/delete: owner (uid = doc id) while a matching `requests/{uid}` is active. read: driver with active subscription containing routeId |
| `driverSubscriptions/{uid}` | planId, routeIds[], status `active/inactive`, expiresAt | read: that driver. write: only while `config/demo.allowSelfActivate == true`, limited to the plan's route count |
| `config/demo` | allowSelfActivate (bool) | read: signed in. write: none (console) |

Why per-route entries: one subtree per route makes route-based access control a simple path rule that Firestore can verify on queries, and it naturally shows a request in every compatible route while counting once per route. Entries contain no owner field, name or phone. The doc id is an anonymous random uid.

## 3. Rules (summary of what is enforced)
- Passenger create/update on `requests/{uid}`: signed in as `uid`; stop ids exist and appear in order on at least one route; fare 1..1000 whole; count 1..14; `expiresAt` must be within (request.time, request.time + 10 min + 1 min tolerance]; `createdAt == request.time`.
- "Still waiting": allowed only when `request.time >= resource.nextReminderAt - tolerance`, sets lastConfirmedAt = request.time and a fresh 10-minute expiry.
- Reactivate: status expired/cancelled -> active with a new window.
- Entries: written only with data equal to the owner's active request for routes that contain both stops.
- Driver read of `entries`: `driverSubscriptions/{uid}.status == 'active'`, `expiresAt > request.time`, and the path's `routeId` in `routeIds`. Everything else denied.
- Dev-only reminder shortcut writes `nextReminderAt` to now. It cannot extend expiry.

## 4. Expiry, honestly
Firestore has no timers. Expiry is enforced two ways:
1. **Read-time:** every demand count ignores entries where `expiresAt <= now`, so an abandoned request stops counting at its expiry even if the passenger closed the app (R2.4). The driver screen also re-evaluates on a 1-second local tick so counts drop without a new write.
2. **Cleanup (optional, later):** a scheduled Cloud Function deleting stale docs needs the Blaze plan. Not required for correctness.
Residual risk: read-time filtering trusts the driver device clock (skew of seconds). Acceptable for the MVP; noted in section 7.

## 5. Matching and aggregation (pure functions, unit tested)
- `destinationsAhead(routes, boardingStopId)`: stops after boarding on any route.
- `routesFor(routes, boarding, destination)`: ids of compatible routes.
- `aggregateDemand(entries, route, currentStopId, now)`: drops expired, drops boarding stops at or before the current station (only later stops are shown), groups by boarding stop then by destination, returns passengers, fares (fare x count), and totals. One entry = one boarding stop, so no double counting.

## 6. User flows
**Passenger:** open app -> anonymous sign-in -> choose stops, fare, count -> Request Transport -> active card -> (5 min) "Have you boarded a bus?" -> YES: thank you / NOT YET: stays active, next prompt in 5 min -> no answer: demand stops counting at 10 min, "Request expired" with one-tap Reactivate. Cancel at any time.
**Driver:** sign in -> (no subscription) upgrade screen with plan prices, demo Activate -> pick subscribed route -> set current station -> live stop cards with destination breakdown and totals.
**Demo:** two browser windows (or phone + laptop) on the same Firebase project or emulator.

## 7. Technical risks
| # | Risk | Likelihood / impact | Mitigation |
|---|---|---|---|
| 1 | Firebase project/config not ready, or emulator needs Java | High / blocks demo | You create the free Firebase project early (Phase 0); emulator as backup |
| 2 | No timers on the free plan, so expired docs are not deleted | Certain / low | Read-time filtering is the contract; cleanup is optional |
| 3 | Client clock skew affects expiry display | Medium / low | Tolerance windows in rules; counts use rules-checked `expiresAt`; show server time estimate via a `serverTimestamp()` write |
| 4 | Rules are easy to get subtly wrong (privacy, subscription gate) | Medium / high | Rules unit tests with `@firebase/rules-unit-testing` on the emulator (needs Java) |
| 5 | Anyone can submit fake demand (anonymous auth) | High in production / low for demo | Documented limitation; add rate limits/App Check after validation with real users |
| 6 | Self-service demo subscription is a bypass | By design | Gated by `config/demo.allowSelfActivate`, turned off for real use; payments are future work |
| 7 | Multi-write per request (request + route entries) can become inconsistent if the app closes mid-write | Low | Use one Firestore batch (atomic) |
| 8 | Fully private "aggregates only" is not possible without Cloud Functions; drivers' devices receive per-request entries (no identity) | Certain / medium | Entries are anonymous; the Blaze + Functions design is documented as the upgrade path |
| 9 | "New project" competition rule vs earlier OneRide work | Medium / high | Fresh public repo with only KaKoRide code and `.kiro`; do not publish OneRide/backend code |
| 10 | Credit budget | Medium | ~6 small phases; reuse UI components; no new libraries beyond `firebase` and test tooling |

New dependencies: `firebase` (required), `@firebase/rules-unit-testing` + `firebase-tools` (dev, for rules tests and hosting). Nothing else.

## 8. Reuse from current `kakoride/`
Keep: Vite/TS/Tailwind setup, `Button`, `Card`, `Badge`, `TabBar`, test setup. Delete: operator accept/booking/ledger components, PIN, Zustand store, seeded bookings, and the old tests. Replace the seed with routes/stops/plans seed data.
