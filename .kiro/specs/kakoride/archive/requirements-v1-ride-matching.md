# KaKoRide — Requirements Specification
**Kiroween 2026 Hackathon · Frankenstein Category**
*Your Route. Your Ride.*

---

## What is KaKoRide?

KaKoRide solves a real problem in Zambian shared transport: **minibus operators sit at terminals waiting for a full load while passengers further down the same route wait for a bus that may never come.** Neither side has visibility into the other.

KaKoRide gives operators a live feed of passenger demand along their route and lets passengers signal where they are and where they're going — so the right bus finds the right people without detours, guesswork, or empty seats.

---

## Relationship to Previous Specifications

KaKoRide replaces the OneRide / RoadRide specifications. The key changes are:

| Dimension | OneRide (Previous) | KaKoRide (This spec) |
|---|---|---|
| Name | OneRide / RoadRide | KaKoRide |
| Client platform | Native Android + web admin | **React/Vite web app** (mobile-first, runs in browser) |
| Backend | Node.js + Cloud SQL (deployed) | **FastAPI/Python** (simple, deployable to Cloud Run) |
| Auth | Scrypt passwords, HttpOnly cookies, Keystore | Simple session tokens — demo-safe |
| GPS/location | Real device GPS, accuracy validation | **No live GPS.** Passengers select a stop from a list. |
| Fare negotiation | Full offer/counter/confirm flow | **Simulated fee** — displayed, not transacted |
| Scope | Global multi-country, Android, full admin | **Zambia one-route MVP**, demonstrable in < 3 minutes |
| Complexity | Production-ready, 36 tests, Android APK | **Hackathon MVP** — polished, functional, ship-fast |

The existing `backend/`, `android-app/`, and `src/` are **not reused** for KaKoRide. The new project lives in a separate directory (`kakoride/`) within this workspace.

---

## Actors

| Actor | Description |
|---|---|
| **Passenger** | A person waiting at a stop who needs a ride to a destination on the route |
| **Operator** | A minibus driver or conductor running a vehicle on a named route |
| **System** | Automated logic: route matching, seat tracking, PIN generation, fee calculation |

> There is no admin role in the KaKoRide MVP. Demo data is seeded. No user management UI.

---

## Glossary

| Term | Definition |
|---|---|
| **Stop** | A named pickup/drop-off point on a route (e.g. "Lusaka Intercity", "Kafue Market") |
| **Route** | An ordered list of stops representing one direction of travel |
| **Service** | An operator's active run on a route — has a vehicle, a remaining capacity, and a current position |
| **Request** | A passenger's signal: "I am at stop X and need to go to stop Y" |
| **Booking** | A confirmed match: an operator has accepted a passenger's request |
| **Boarding PIN** | A short numeric code the passenger shows; the operator enters it to confirm pickup |
| **Simulated fee** | A calculated fare displayed in ZMW for record-keeping; no real payment is taken |
| **Ledger** | A per-operator running record of accepted requests, fees collected, and seats filled |

---

## Requirements

### REQ-1 · Demonstration Data

**REQ-1.1** — The app ships with one pre-seeded Zambian minibus route: **Lusaka → Kafue**, with the following stops in order:

1. Lusaka Intercity Bus Terminus
2. Chelston
3. Chongwe Turnoff
4. Kafue Roundabout
5. Kafue Market

**REQ-1.2** — A set of demonstration passenger requests is included at startup, distributed across different boarding/destination pairs on the route.

**REQ-1.3** — A demonstration operator service is seeded with vehicle details (plate, make/model) and an initial capacity of 14 seats.

**REQ-1.4** — Demonstration data must not contain any real personal information. All names and phone numbers are fictional.

**REQ-1.5** — There is a "Reset demo" button that clears live state and restores the seeded data, so the demo can be restarted for judges without refreshing the page.

---

### REQ-2 · Passenger Workflow

**REQ-2.1** — Any visitor can open the Passenger view without logging in. The passenger is identified by a demo name chosen at the start (e.g. "Demo Passenger A").

**REQ-2.2** — The passenger selects a **boarding stop** from the route stop list.

**REQ-2.3** — The passenger selects a **destination stop**. Only stops with a higher sequence number than the boarding stop are valid.

**REQ-2.4** — The passenger sees the **simulated fee** for their journey (calculated from the route's per-segment rate × number of segments) before submitting.

**REQ-2.5** — The passenger submits the request. It becomes visible to operators running this route.

**REQ-2.6** — The passenger's request expires automatically after **5 minutes** if no operator accepts it.

**REQ-2.7** — Once an operator accepts, the passenger sees:
- The operator's vehicle details (plate, make/model)
- Their **boarding PIN** (4 digits)
- A status of "Waiting for pickup"

**REQ-2.8** — After the operator verifies the PIN, the passenger's status updates to **"On board"**.

**REQ-2.9** — After the operator marks the journey complete, the passenger sees a **trip summary** (route segment, fee, operator) and is prompted to rate (1–5 stars).

**REQ-2.10** — A passenger can **cancel** their open request before it is accepted.

---

### REQ-3 · Operator Workflow

**REQ-3.1** — Any visitor can open the Operator view without logging in. The operator is identified by a demo name (e.g. "Demo Operator — Plate TAB 1234 ZM").

**REQ-3.2** — The operator sees their **vehicle details**, the **route name**, and the **remaining seat count**.

**REQ-3.3** — The operator sees a **live feed** of open passenger requests that are **compatible** with their route:
- The passenger's boarding stop must be on the operator's route
- The passenger's destination must be further along the route (higher sequence number)
- The boarding stop must be **at or ahead** of the operator's current position

**REQ-3.4** — Each request card shows: boarding stop, destination, simulated fee, and time since submitted.

**REQ-3.5** — The operator can **accept** a request. This:
- Decrements the available seat count by 1
- Sends the booking (with PIN) to the passenger
- Removes the request from the feed

**REQ-3.6** — The operator can **advance their position** stop-by-stop along the route. Requests for stops the operator has already passed drop off the feed.

**REQ-3.7** — The operator sees a list of **active bookings** (accepted but not yet complete).

**REQ-3.8** — For each active booking, the operator can **enter the boarding PIN** to confirm the passenger has boarded.

**REQ-3.9** — The operator can mark a booking as **complete** after the passenger has been dropped at their destination.

**REQ-3.10** — The operator can **cancel** an active booking (e.g. breakdown). The passenger's request returns to open.

**REQ-3.11** — The operator sees a **ledger** showing: total trips completed, total fees collected (ZMW), total seats filled, and a list of recent completed bookings.

---

### REQ-4 · Route Matching Logic

**REQ-4.1** — A request is **compatible** with a service if:
1. The boarding stop is on the service's route
2. The destination stop is on the service's route
3. The boarding stop's sequence number is strictly less than the destination stop's sequence number
4. The boarding stop's sequence number is **greater than or equal to** the service's current position sequence number (i.e., the vehicle has not yet passed that stop)
5. The service has at least 1 available seat

**REQ-4.2** — Compatibility is re-evaluated in real time. When an operator advances their position, incompatible requests disappear from their feed immediately.

**REQ-4.3** — The system prevents overbooking: accepting a request when available seats = 0 is rejected.

---

### REQ-5 · Boarding PIN

**REQ-5.1** — Each booking is assigned a unique 4-digit PIN generated at acceptance time.

**REQ-5.2** — The PIN is shown only to the passenger in their booking view.

**REQ-5.3** — The operator enters the PIN to confirm pickup. If the PIN matches, the booking status changes to "boarded".

**REQ-5.4** — An incorrect PIN shows an error. After 3 failed attempts the booking is flagged and the operator is prompted to contact support.

---

### REQ-6 · Simulated Fee & Ledger

**REQ-6.1** — Each route has a **per-segment rate** in ZMW (e.g. ZMW 5 per segment). The fee for a journey = rate × number of segments between boarding and destination.

**REQ-6.2** — Fees are displayed prominently to both passenger and operator before and during a booking. No real payment is taken.

**REQ-6.3** — The operator ledger records: booking ID, passenger alias, boarding stop, destination, fee (ZMW), status, and timestamp.

**REQ-6.4** — The ledger shows a running total: ZMW collected (simulated), seats filled, trips completed.

---

### REQ-7 · Interface & Experience

**REQ-7.1** — The app is a **single-page React application** running entirely in the browser. No login is required.

**REQ-7.2** — The UI has **two tabs**: Passenger and Operator. Switching tabs switches the active view. Both views share the same in-memory data state.

**REQ-7.3** — The design is **mobile-first**: fully usable at 375px viewport width. Touch targets ≥ 44 × 44 px.

**REQ-7.4** — The interface updates in **near-real-time** without page refresh. When the operator accepts a request (from the Operator tab), switching back to the Passenger tab reflects the new booking status immediately.

**REQ-7.5** — Status is communicated with clear **colour-coded badges**: open (orange), accepted (blue), boarded (green), completed (grey), cancelled (red).

**REQ-7.6** — The app functions fully offline (no backend calls). All logic is in-browser.

**REQ-7.7** — A **"Reset demo"** action restores the initial seeded state so the demo can be re-run without refreshing.

**REQ-7.8** — The design uses the KaKoRide brand: indigo/purple primary, clean card-based layout, Zambia transport context in copy.

---

### REQ-8 · Non-Functional Requirements

**REQ-8.1 — No live GPS.** The system never requests device location. Passengers pick a stop from a list.

**REQ-8.2 — No payments.** Fees are simulated and displayed only. No payment SDK or external service is called.

**REQ-8.3 — No auth required.** The demo runs without accounts or login to minimise demo friction.

**REQ-8.4 — No backend for MVP.** All state is managed in React (Zustand or Context). A FastAPI backend is an optional enhancement described in the tasks but is not required for the demo.

**REQ-8.5 — Demonstrable in under 3 minutes.** The complete passenger → operator → boarding → completion flow must be walkthrough-able in a single browser window in under 3 minutes.

**REQ-8.6 — TypeScript throughout.** All source files use TypeScript.

**REQ-8.7 — Build must pass.** `npm run build` completes without errors before submission.

---

### REQ-9 · Out of Scope

The following are **explicitly excluded** from the KaKoRide MVP:

- Real user accounts or authentication
- Multiple routes or multi-city support
- Live GPS or map display
- Real payment processing
- Push or background notifications
- Native mobile app (Android/iOS)
- Admin dashboard
- Multi-country architecture
- Fleet operator management
- Counter-offer fare negotiation
- Supabase, Firebase, or any managed BaaS

---

## MVP Demo Script (< 3 minutes)

The following walkthrough must be possible with a single browser window:

1. Open the app → land on Passenger tab.
2. Passenger selects "Chelston" (boarding) → "Kafue Market" (destination).
3. Passenger sees fee: ZMW 20 (4 segments × ZMW 5). Submits request.
4. Switch to Operator tab → request appears in feed.
5. Operator taps Accept → seats decrement; request leaves feed.
6. Switch to Passenger tab → PIN and vehicle details visible.
7. Switch to Operator tab → active booking visible → enter PIN.
8. Boarding confirmed → status changes to "On board".
9. Operator taps Complete → booking moves to ledger.
10. Switch to Passenger tab → trip summary and rating prompt.
11. Passenger submits 5-star rating.
12. Operator ledger shows ZMW 20 collected, 1 trip, 1 seat.
13. Press "Reset demo" → state resets.

Total: ≈ 2 minutes with narration.
