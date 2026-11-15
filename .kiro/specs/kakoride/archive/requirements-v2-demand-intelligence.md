# KaKoRide: Requirements (v2, demand intelligence)
Kiroween 2026. *Your Route. Your Ride.*  Status: **awaiting approval**

Supersedes v1 (ride matching with driver acceptance), kept in `archive/`.

## 1. Product in one paragraph
Passengers (free, no account) say where they are waiting, where they are going and what fare per person they can pay. Subscribed drivers see aggregated, anonymous passenger demand at the stops ahead of them on their route. **KaKoRide is not Uber:** no booking, no driver acceptance, no GPS, no PINs, no ledger.

## 2. What changes from v1 and OneRide
| Removed | Added |
|---|---|
| Operator accept/decline, seats, boarding PIN, ledger, ratings | Aggregated demand dashboard per stop and destination |
| Local in-memory store | Firebase Firestore (real-time, two independent sessions) |
| No auth | Anonymous passenger sessions; driver sign-in; demo subscriptions |
| Simulated fee per segment | Passenger-entered fare per passenger (K) |
| Backend / Android / Supabase code from OneRide | Not used; not part of the submission |

## 3. Actors
- **Passenger:** anonymous Firebase session. One active request per session.
- **Driver:** signed-in, with a demo subscription covering one or more routes.
- **System:** rules + (optional) scheduled cleanup enforcing expiry and access.

## 4. Requirements

### R1 Passenger request
- R1.1 Home shows logo, "Where are you going?", boarding dropdown, destination dropdown, fare (K) labelled **per passenger**, passenger count (default 1), large **Request Transport** button.
- R1.2 Destinations offered are only stops ahead of the boarding stop on at least one supported route. Boarding or destination from a disallowed pair is rejected by the data rules, not just the UI.
- R1.3 No registration. Session is Firebase anonymous auth.
- R1.4 One active request per session (enforced by document id = session uid).
- R1.5 After submit show "Your transport request is active." with boarding, destination, fare, passengers, waiting status, **Cancel Request**.
- R1.6 Fare is a whole number of kwacha, 1 to 1000. Passengers 1 to 14.
- R1.7 Fictional/no personal data is collected.

### R2 Reminder, completion, expiry
- R2.1 Five minutes after creation or last confirmation, ask "Have you boarded a bus?" with **YES, I'VE BOARDED** and **NOT YET, I'M STILL WAITING**.
- R2.2 YES: request becomes `completed`, leaves demand immediately, thank-you shown.
- R2.3 NOT YET: stays active; `lastConfirmedAt` = now; next reminder in 5 minutes; expiry extended to 10 minutes after this confirmation.
- R2.4 No response: the request stops counting as demand **10 minutes after creation or last confirmation**, even if the app is closed. Enforcement is by server-time checks (Firestore rules + read-time filtering), not by the client being open.
- R2.5 Expired requests can be reactivated with one tap (new 10-minute window).
- R2.6 Timestamps come from Firestore server time (`request.time` in rules).
- R2.7 Dev-only, clearly labelled control "Simulate 5 minutes passing" triggers the reminder immediately. Hidden in production builds.

### R3 Driver dashboard
- R3.1 Separate driver area. Driver picks a subscribed route and sets the **current station manually**.
- R3.2 Shows total active waiting passengers ahead, total fares offered (fare x passengers), and cards per upcoming boarding stop with: passengers waiting, per-destination passenger counts, total fares, optional demand bar.
- R3.3 "Ahead" = **only stops after the driver's current station** on the route direction. The current station and stops already passed are hidden. (Decided by the product owner.)
- R3.4 Updates automatically as passengers submit, cancel, complete, expire or reactivate.
- R3.5 Drivers never see names, phone numbers or any identity. Drivers cannot accept, reject or contact a passenger.
- R3.6 A passenger counts once per route, at their one boarding stop. If two routes serve the same journey, the request appears in each route's own demand.

### R4 Route matching
- R4.1 Routes are predefined ordered stop lists with a direction. A request is compatible with a route if boarding and destination are both on it and boarding sequence < destination sequence.
- R4.2 B to D is compatible with A-B-C-D; D to B is not.
- R4.3 Demo data: Lusaka to Kafue (5 stops) plus a second overlapping route so multi-route behaviour can be shown.

### R5 Subscriptions (demo)
- R5.1 Passengers free. Drivers pay monthly for route visibility.
- R5.2 Plans are configuration, not code: Single Route K50/month (1 route), Three Routes K120/month (3 routes).
- R5.3 Demo activation is simulated (no payment gateway). It is only permitted while a demo flag is on in Firestore config.
- R5.4 Only a driver with an `active`, unexpired subscription containing the route can read that route's demand. Enforced by Firestore Security Rules.
- R5.5 A driver without a subscription sees an upgrade screen (simulated activation in demo).

### R6 Experience
- R6.1 Mobile-first, large touch targets (>= 44px), plain language, minimal steps, a first-time passenger needs no instructions.
- R6.2 Light: no maps, no images beyond logo, small bundle for slow connections.
- R6.3 Basic accessibility: labels, focus outline, aria-live for demand changes.

### R7 Demo
Must work with **two independent browser sessions** on shared Firestore (hosted project or local emulator):
1. Passenger submits request. 2. Driver dashboard (other session) increases immediately. 3. Demand grouped by stop and destination. 4. Simulate 5 minutes. 5. "Boarded": driver demand drops. 6. Another passenger "Still waiting": request retained. 7. Passenger who ignores prompts disappears from demand at expiry. Seeded fictional requests are available through a dev-only "Seed demo demand" button.

## 5. Out of scope
Maps, GPS, car animation, driver accept/reject, individual booking, payments, AI prediction, chat, passenger profiles, route optimisation, native apps, multi-country.

## 6. Open questions for you (defaults assumed if you don't answer)
- Q1 Backend: **Firebase on the free Spark plan, no Cloud Functions** (default). Stronger alternative needs the paid Blaze plan; see design section 7.
- Q2 ~~Current station visibility~~ **Decided: later stops only.**
- Q3 Is a new GitHub repo with only `kakoride/` and `.kiro/` acceptable for the "new project" rule? Default: **yes**; OneRide/backend code stays out. Please check the official Kiroween rules.
- Q4 Firebase project: you create it (free) and give me the web config values, or we use the local emulator for the demo (needs Java 11+). Default: **both supported**.
