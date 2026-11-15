# KaKoRide — Implementation Tasks
**Kiroween 2026 · Your Route. Your Ride.**

Tasks are ordered for incremental delivery. After Task 6, the core demo flow works end-to-end. Tasks 7–10 polish and prepare for submission.

## Status

- Done and verified by build + 16 tests (including a UI test that runs the full demo script): Tasks 1–7, and the README part of Task 9.
- Deviations from the plan: Tailwind 4 uses CSS `@theme` (no `tailwind.config.ts`); no lint config was added; no HTML manifest link; Task 8 (accessibility) was only partly done (labels, 44px targets, focus outline, aria-live) and has not been checked on a real phone or with a contrast tool.
- Not done: Task 10 (optional FastAPI backend), manual browser/mobile review, deployment.
- The Android app was removed from the workspace at the user's request.

---

## Task 1 · Project Scaffold

**Goal:** Working Vite + React + TypeScript + Tailwind project. `npm run dev` opens a branded page.

- [ ] Create `kakoride/` directory at workspace root
- [ ] Initialise Vite project: `npm create vite@latest . -- --template react-ts`
- [ ] Install dependencies: `tailwindcss`, `@tailwindcss/vite`, `lucide-react`, `zustand`
- [ ] Configure Tailwind: `tailwind.config.ts` with brand colours (indigo-600 primary, violet-600 secondary, status colours)
- [ ] Create `src/index.css` with Tailwind directives and CSS custom properties for brand tokens
- [ ] Create `index.html` with correct title ("KaKoRide — Your Route. Your Ride."), viewport meta, and manifest link
- [ ] Create `App.tsx` rendering a placeholder branded header
- [ ] Verify: `npm run build` and `npm run dev` both succeed with no errors

**Acceptance:** Browser shows "KaKoRide" heading on indigo background at http://localhost:5173.

---

## Task 2 · Types, Seed Data, and Utilities

**Goal:** All domain types defined; Lusaka → Kafue route seeded; matching and fee logic working.

- [ ] Create `src/types/index.ts` with all interfaces from design §4.1 (`Stop`, `Route`, `Vehicle`, `Service`, `PassengerRequest`, `Booking`, `Rating`, `LedgerEntry`)
- [ ] Create `src/data/seed.ts` with the Lusaka → Kafue route (5 stops, sequences 1–5, ZMW 5/segment), demo service (TAB 1234 ZM, 14 seats), and 4 demo passenger requests
- [ ] Create `src/utils/fare.ts` with `calculateFee(route, boardSeq, destSeq): number`
- [ ] Create `src/utils/matching.ts` with `isCompatible(request, service): boolean` implementing all 5 rules from design §6
- [ ] Create `src/utils/pin.ts` with `generatePin(): string` returning a random 4-digit string (e.g. "2847")
- [ ] Write unit tests for `calculateFee` and `isCompatible` using Vitest: cover edge cases (passed stop, full bus, reversed direction, expired request)

**Acceptance:** `npm test` passes all utility tests.

---

## Task 3 · Zustand Store

**Goal:** All application state and actions in one Zustand store. No component state for business logic.

- [ ] Create `src/store/index.ts` implementing `KaKoRideStore` from design §5
- [ ] Implement `submitRequest`: validates boarding < destination sequence; sets expiry to now + 5 min; adds to requests array
- [ ] Implement `cancelRequest`: sets status to `'cancelled'`
- [ ] Implement `acceptRequest`: calls `isCompatible`, decrements `availableSeats`, generates PIN, creates booking, sets request status to `'accepted'`; throw/return error if overbooking attempted
- [ ] Implement `verifyPin`: compares pin, increments `pinAttempts`, returns `'ok' | 'wrong' | 'locked'` (locked after 3 attempts)
- [ ] Implement `completeBooking`: sets booking status to `'completed'`, sets `completedAt`
- [ ] Implement `cancelBooking`: sets booking to `'cancelled'`, restores request to `'open'` if not expired
- [ ] Implement `advancePosition`: updates `service.currentStopSequence`; re-evaluates compatible requests (store derivation handles this automatically)
- [ ] Implement `resetDemo`: restores initial seeded state (deep copy of seed data)
- [ ] Implement derived selectors: `compatibleRequests()`, `activeRequestForPassenger()`, `activeBookingForPassenger()`, `ledgerEntries()`, `ledgerTotals()`
- [ ] Add a `useEffect`-free expiry mechanism: `compatibleRequests()` filters out expired requests on every read; a 30-second interval updates a `now` timestamp in the store to trigger re-renders

**Acceptance:** Store unit tests cover accept/verify/complete/cancel/reset flows.

---

## Task 4 · Shared UI Components

**Goal:** Reusable, accessible UI primitives that all views use.

- [ ] Create `src/components/ui/Badge.tsx`: renders a pill with colour per `RequestStatus` or `BookingStatus`; uses CSS custom properties from design §8
- [ ] Create `src/components/ui/Button.tsx`: primary (indigo fill), secondary (outline), danger (red); size sm/md/lg; disabled state; loading spinner variant
- [ ] Create `src/components/ui/Card.tsx`: white card with shadow, rounded-xl, padding; optional header slot
- [ ] Create `src/components/ui/PinInput.tsx`: 4-cell numeric input; auto-advances focus on each digit; calls `onComplete(pin: string)` when all 4 filled; resets on error
- [ ] Create `src/components/shared/TabBar.tsx`: "Passenger" | "Operator" tabs fixed to bottom; active tab highlighted indigo; icons (UserCircle / Bus)
- [ ] Create `src/components/shared/RouteProgress.tsx`: horizontal stop sequence showing operator's current position; stops ahead highlighted; stops passed greyed out
- [ ] Create `src/components/shared/ResetButton.tsx`: floating button bottom-right; confirms before resetting; calls `store.resetDemo()`
- [ ] Create `src/components/shared/ExpiryTimer.tsx`: shows "Expires in M:SS" countdown from `request.expiresAt`; turns red when < 60 seconds

**Acceptance:** Render all components in isolation; no TypeScript errors; all touch targets ≥ 44px.

---

## Task 5 · Passenger View

**Goal:** Complete passenger workflow: submit request → see booking + PIN → rate trip.

- [ ] Create `src/components/passenger/RequestForm.tsx`:
  - Boarding stop dropdown (all route stops)
  - Destination stop dropdown (filtered to stops with higher sequence than boarding)
  - Live fee preview: "ZMW XX" updates as stops are selected
  - Submit button → calls `store.submitRequest()`
  - Disables submit if passenger already has an open/accepted request
- [ ] Create `src/components/passenger/ActiveRequest.tsx`:
  - Shows request details, boarding/destination, fee, status badge
  - Shows `ExpiryTimer` while status is `'open'`
  - Cancel button (only for `'open'` requests)
- [ ] Create `src/components/passenger/BookingConfirm.tsx`:
  - Shows once booking status is `'accepted'`
  - Large 4-digit PIN in monospace bold
  - Vehicle details: plate, make/model
  - "Show this PIN to the operator" instruction
  - Status transitions automatically to "On board" when booking = `'boarded'`
- [ ] Create `src/components/passenger/TripSummary.tsx`:
  - Shows once booking is `'completed'`
  - Route segment, fee paid, operator alias, vehicle
  - 5-star rating input (tap to select)
  - Submit rating button → calls `store.submitRating()`
  - Shows thank-you message after rating submitted
- [ ] Create `src/views/PassengerView.tsx`: orchestrates all passenger components based on store state; shows appropriate component for each state
- [ ] Add demo passenger alias selector at top of PassengerView (dropdown or preset buttons: "Passenger A" / "Passenger B" / "Passenger C")

**Acceptance:** Full passenger flow demonstrable: select stops → submit → see PIN → see "On board" → see summary → rate. No TypeScript errors.

---

## Task 6 · Operator View

**Goal:** Complete operator workflow: see feed → accept → verify PIN → complete → view ledger.

- [ ] Create `src/components/operator/ServiceHeader.tsx`:
  - Vehicle plate and make/model
  - Route name
  - Seat counter: "10 / 14 seats available" with colour change when low
  - Current position indicator: "Currently at: Chelston"
  - "Advance to next stop" button (disabled when at last stop)
- [ ] Create `src/components/operator/RequestCard.tsx`:
  - Boarding stop → destination stop (arrow)
  - Fee badge (ZMW)
  - Time since submitted (e.g. "2 min ago")
  - Accept button → calls `store.acceptRequest()`
  - Accept button shows loading state briefly; then disappears from feed
- [ ] Create `src/components/operator/RequestFeed.tsx`:
  - Lists all `store.compatibleRequests()` as `RequestCard`s
  - Empty state: "No passengers waiting along your route"
  - Updates reactively when operator advances position or a request expires
- [ ] Create `src/components/operator/BookingCard.tsx`:
  - Shows passenger alias, boarding/destination, fee
  - Status badge
  - For `'accepted'` bookings: `PinInput` component + "Verify boarding" label
  - For `'boarded'` bookings: "Complete Journey" button + "Cancel Booking" button
  - Shows error message on wrong PIN; shows "Locked" state after 3 failures
- [ ] Create `src/components/operator/ActiveBookings.tsx`:
  - Lists all `'accepted'` and `'boarded'` bookings as `BookingCard`s
  - Empty state: "No active bookings"
- [ ] Create `src/components/operator/Ledger.tsx`:
  - Summary row: total trips, total ZMW, total seats filled
  - Scrollable table: booking ID, passenger, boarding, destination, fee, timestamp
  - Shows `'completed'` bookings only
  - Empty state: "No completed trips yet"
- [ ] Create `src/views/OperatorView.tsx`: ServiceHeader + RouteProgress + (RequestFeed | ActiveBookings tabbed) + Ledger section

**Acceptance:** Full operator flow demonstrable: see requests → accept → enter PIN → complete → see ledger. No TypeScript errors.

---

## Task 7 · Integration & Demo Polish

**Goal:** Both views work together. The 3-minute demo script runs without friction.

- [ ] Wire up `App.tsx` with TabBar, PassengerView, OperatorView, and ResetButton
- [ ] Verify shared state: accepting a request on the Operator tab immediately updates PassengerView (no refresh)
- [ ] Add page-level header: KaKoRide logo text, route name ("Lusaka → Kafue"), and a subtle "Demo Mode" badge
- [ ] Add smooth tab transition animation (fade or slide)
- [ ] Add empty state illustrations (SVG placeholders) for: no requests, no active bookings, no ledger entries
- [ ] Test the full demo script from requirements §MVP Demo Script end to end in a browser
- [ ] Fix any state edge cases: cancellation re-opening requests, overbooking prevention, PIN lock UX

**Acceptance:** The 13-step demo script completes in under 3 minutes without any console errors.

---

## Task 8 · Mobile Responsiveness & Accessibility

**Goal:** App works on a 375px phone screen; meets basic WCAG 2.1 AA requirements.

- [ ] Test all views at 375px × 667px (iPhone SE viewport)
- [ ] Verify all touch targets are ≥ 44 × 44 px (especially TabBar, Accept, PinInput cells)
- [ ] Verify colour contrast: indigo-600 on white ≥ 4.5:1; status badges pass AA
- [ ] Add `aria-label` to icon-only buttons and inputs without visible labels
- [ ] Ensure all dropdowns are keyboard-navigable (Tab / Enter / Escape)
- [ ] Add focus-visible outline style for keyboard users
- [ ] Test on actual mobile device or Chrome DevTools mobile simulation

**Acceptance:** No critical WCAG 2.1 AA failures on a 375px viewport.

---

## Task 9 · Build Verification & README

**Goal:** Clean build; judges can run the demo in one command.

- [ ] Run `npm run build` — zero errors, zero TypeScript errors
- [ ] Run `npm test` — all utility tests pass
- [ ] Run `npm run lint` — no ESLint errors
- [ ] Create `kakoride/README.md`:
  - What KaKoRide is (1 paragraph)
  - `npm install && npm run dev` → opens at http://localhost:5173
  - Demo walkthrough instructions (the 13-step script)
  - Architecture notes (Vite + Zustand, no backend, no auth)
  - Hackathon context (Kiroween 2026, Frankenstein category)
- [ ] Verify the app loads correctly in production mode: `npm run build && npm run preview`

**Acceptance:** A judge can clone and run the demo in under 2 minutes with zero configuration.

---

## Task 10 · (Optional) FastAPI Backend

**Goal:** Add a Python API so two devices can share state in real time.

> This task is explicitly optional and must not block submission.

- [ ] Create `kakoride/api/` directory
- [ ] Create `main.py` with FastAPI app, CORS middleware, and an in-memory state module
- [ ] Implement `POST /api/reset`, `GET /api/state`, `POST /api/requests`, `POST /api/requests/{id}/cancel`, `POST /api/bookings/accept`, `POST /api/bookings/{id}/verify-pin`, `POST /api/bookings/{id}/complete`, `POST /api/service/advance`
- [ ] Port matching logic from `matching.ts` to `matching.py`
- [ ] Add `requirements.txt`: `fastapi`, `uvicorn`, `pydantic`
- [ ] Add `Dockerfile` for Cloud Run
- [ ] Update frontend store to call API instead of in-memory state when `VITE_API_URL` is set
- [ ] Add `api/README.md` with `uvicorn main:app --reload` instructions

**Acceptance:** `uvicorn main:app` runs; `curl /api/state` returns seeded data. Frontend demo script works against the API.

---

## Completion Checklist

Before hackathon submission:

- [ ] `npm run build` passes (kakoride/)
- [ ] `npm test` passes (kakoride/)
- [ ] Demo script runs end to end in < 3 minutes
- [ ] App works on mobile viewport (375px)
- [ ] README present with run instructions
- [ ] No real personal data in seed data
- [ ] `.kiro/specs/kakoride/` contains requirements.md, design.md, tasks.md
- [ ] Project name "KaKoRide — Your Route. Your Ride." appears in app header and HTML title
