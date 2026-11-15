# KaKoRide — Technical Design
**Kiroween 2026 · Your Route. Your Ride.**

---

## 1. Architecture Decision: Frontend-only MVP

KaKoRide's MVP runs entirely in the browser. There is no backend, no database, and no network calls. All state lives in a Zustand store. This is a deliberate hackathon tradeoff: it eliminates deployment complexity, infrastructure cost, and the risk of a backend being unavailable during a live demo.

A FastAPI backend is designed and documented here but implemented as an **optional enhancement**. The store interface is designed so the backend can be dropped in without changing component code — components call store actions, not fetch directly.

```
┌─────────────────────────────────────────────────────────┐
│              Browser (React / Vite / TypeScript)        │
│                                                         │
│   PassengerView ─┐                                      │
│                  ├── Zustand Store (all state)          │
│   OperatorView ──┘       │                              │
│                          │ (optional, Phase 2)          │
│                          ▼                              │
│                  ┌──────────────┐                       │
│                  │  FastAPI API │  ← Cloud Run          │
│                  │  PostgreSQL  │  ← Cloud SQL          │
│                  └──────────────┘                       │
└─────────────────────────────────────────────────────────┘
```

---

## 2. Tech Stack

| Layer | Choice | Why |
|---|---|---|
| Framework | React 19 + Vite 6 | Fast dev server, HMR, simple build |
| Language | TypeScript 5 | Type safety throughout |
| State | Zustand | Minimal boilerplate, no context providers, easy DevTools |
| Styling | Tailwind CSS 4 | Utility-first, mobile-first, no runtime overhead |
| Icons | Lucide React | Lightweight, consistent |
| Routing | None (single-page, tab-based) | Zero routing complexity for MVP |
| Testing | Vitest + React Testing Library | Same toolchain as Vite |
| Backend (optional) | FastAPI + Python 3.12 | Simple, typed, Cloud Run-friendly |
| Deployment | Vercel (frontend) + Cloud Run (optional API) | Free tier, zero-config |

---

## 3. Project Structure

```
kakoride/
├── src/
│   ├── data/
│   │   └── seed.ts          # Seeded route, stops, demo requests, demo service
│   ├── store/
│   │   └── index.ts         # Zustand store — all state and actions
│   ├── types/
│   │   └── index.ts         # All TypeScript interfaces
│   ├── utils/
│   │   ├── matching.ts      # isCompatible(request, service): boolean
│   │   ├── fare.ts          # calculateFee(route, boardSeq, destSeq): number
│   │   └── pin.ts           # generatePin(): string (4-digit)
│   ├── components/
│   │   ├── ui/
│   │   │   ├── Badge.tsx     # Status badge with colour variants
│   │   │   ├── Card.tsx      # Base card wrapper
│   │   │   ├── Button.tsx    # Sized, variant button
│   │   │   └── PinInput.tsx  # 4-cell PIN entry
│   │   ├── passenger/
│   │   │   ├── RequestForm.tsx      # Stop selectors + fee preview + submit
│   │   │   ├── ActiveRequest.tsx    # Open/accepted/boarded request status
│   │   │   ├── BookingConfirm.tsx   # PIN display + vehicle info
│   │   │   └── TripSummary.tsx      # Completion + star rating
│   │   ├── operator/
│   │   │   ├── ServiceHeader.tsx    # Vehicle info + seats + position
│   │   │   ├── RequestFeed.tsx      # Compatible request cards
│   │   │   ├── RequestCard.tsx      # Single request + Accept button
│   │   │   ├── ActiveBookings.tsx   # Accepted bookings list
│   │   │   ├── BookingCard.tsx      # Booking + PIN entry + Complete
│   │   │   └── Ledger.tsx           # Totals + booking history table
│   │   └── shared/
│   │       ├── TabBar.tsx           # Passenger / Operator tabs
│   │       ├── RouteProgress.tsx    # Visual stop progress bar
│   │       └── ResetButton.tsx      # Demo reset action
│   ├── views/
│   │   ├── PassengerView.tsx
│   │   └── OperatorView.tsx
│   ├── App.tsx
│   ├── main.tsx
│   └── index.css
├── public/
│   └── kakoride-og.png       # Open Graph image for sharing
├── index.html
├── vite.config.ts
├── tailwind.config.ts
├── tsconfig.json
└── package.json
```

---

## 4. Data Model

### 4.1 Types (`src/types/index.ts`)

```typescript
export interface Stop {
  id: string;
  name: string;
  sequence: number;   // 1-based, determines travel direction
}

export interface Route {
  id: string;
  name: string;         // "Lusaka → Kafue"
  stops: Stop[];        // ordered by sequence ASC
  perSegmentRate: number;  // ZMW per segment (e.g. 5)
}

export interface Vehicle {
  plate: string;         // "TAB 1234 ZM"
  makeModel: string;     // "Toyota Hiace"
}

export interface Service {
  id: string;
  operatorAlias: string;    // "Demo Operator"
  vehicle: Vehicle;
  route: Route;
  totalSeats: number;        // 14
  availableSeats: number;    // decremented on accept
  currentStopSequence: number; // operator's current position (starts at 1)
}

export type RequestStatus = 'open' | 'accepted' | 'cancelled' | 'expired';

export interface PassengerRequest {
  id: string;
  passengerAlias: string;   // "Demo Passenger A"
  boardingStop: Stop;
  destinationStop: Stop;
  fee: number;               // calculated ZMW fee
  status: RequestStatus;
  createdAt: number;         // Date.now() ms
  expiresAt: number;         // createdAt + 5 * 60 * 1000
}

export type BookingStatus = 'accepted' | 'boarded' | 'completed' | 'cancelled';

export interface Booking {
  id: string;
  requestId: string;
  passengerAlias: string;
  boardingStop: Stop;
  destinationStop: Stop;
  vehicle: Vehicle;
  fee: number;
  pin: string;              // 4-digit string
  pinAttempts: number;
  status: BookingStatus;
  createdAt: number;
  completedAt?: number;
}

export interface Rating {
  bookingId: string;
  stars: number;   // 1-5
}

export interface LedgerEntry {
  bookingId: string;
  passengerAlias: string;
  boardingStop: string;
  destinationStop: string;
  fee: number;
  completedAt: number;
}
```

### 4.2 Seeded Data (`src/data/seed.ts`)

```typescript
// Lusaka → Kafue route
export const LUSAKA_KAFUE_ROUTE: Route = {
  id: 'route-lsk-kaf',
  name: 'Lusaka → Kafue',
  perSegmentRate: 5,  // ZMW 5 per segment
  stops: [
    { id: 's1', name: 'Lusaka Intercity Bus Terminus', sequence: 1 },
    { id: 's2', name: 'Chelston',                      sequence: 2 },
    { id: 's3', name: 'Chongwe Turnoff',               sequence: 3 },
    { id: 's4', name: 'Kafue Roundabout',              sequence: 4 },
    { id: 's5', name: 'Kafue Market',                  sequence: 5 },
  ],
};

// Demo operator service
export const DEMO_SERVICE: Service = {
  id: 'svc-001',
  operatorAlias: 'Demo Operator — Chanda M.',
  vehicle: { plate: 'TAB 1234 ZM', makeModel: 'Toyota Hiace' },
  route: LUSAKA_KAFUE_ROUTE,
  totalSeats: 14,
  availableSeats: 14,
  currentStopSequence: 1,
};

// Demo passenger requests (open, various stop pairs)
export const DEMO_REQUESTS: PassengerRequest[] = [
  makeRequest('Mwamba K.',    's1', 's5'),  // Full route — ZMW 20
  makeRequest('Chipo N.',     's2', 's4'),  // 2 segments — ZMW 10
  makeRequest('Bwalya T.',    's1', 's3'),  // 2 segments — ZMW 10
  makeRequest('Namukolo M.',  's3', 's5'),  // 2 segments — ZMW 10
];
```

---

## 5. Store Design (`src/store/index.ts`)

The store is the single source of truth. Views never mutate state directly.

```typescript
interface KaKoRideStore {
  // State
  activeTab: 'passenger' | 'operator';
  service: Service;
  requests: PassengerRequest[];
  bookings: Booking[];
  ratings: Rating[];
  selectedPassengerAlias: string;

  // Actions — Passenger
  setPassengerAlias(alias: string): void;
  submitRequest(boardingStopId: string, destinationStopId: string): void;
  cancelRequest(requestId: string): void;
  submitRating(bookingId: string, stars: number): void;

  // Actions — Operator
  advancePosition(toStopSequence: number): void;
  acceptRequest(requestId: string): void;
  verifyPin(bookingId: string, enteredPin: string): 'ok' | 'wrong' | 'locked';
  completeBooking(bookingId: string): void;
  cancelBooking(bookingId: string): void;

  // Shared
  setActiveTab(tab: 'passenger' | 'operator'): void;
  resetDemo(): void;

  // Derived (computed from state)
  compatibleRequests(): PassengerRequest[];
  activeRequestForPassenger(): PassengerRequest | undefined;
  activeBookingForPassenger(): Booking | undefined;
  ledgerEntries(): LedgerEntry[];
  ledgerTotals(): { trips: number; seats: number; totalFee: number };
}
```

---

## 6. Matching Logic (`src/utils/matching.ts`)

```typescript
export function isCompatible(
  request: PassengerRequest,
  service: Service
): boolean {
  const boardSeq = request.boardingStop.sequence;
  const destSeq  = request.destinationStop.sequence;
  const curSeq   = service.currentStopSequence;

  // 1. Both stops must be on the route (guaranteed by selection UI)
  // 2. Destination must be further along than boarding
  if (destSeq <= boardSeq) return false;
  // 3. Boarding stop must be at or ahead of operator's current position
  if (boardSeq < curSeq) return false;
  // 4. Must have available seats
  if (service.availableSeats < 1) return false;
  // 5. Request must be open and not expired
  if (request.status !== 'open') return false;
  if (Date.now() > request.expiresAt) return false;

  return true;
}
```

---

## 7. Fee Calculation (`src/utils/fare.ts`)

```typescript
export function calculateFee(route: Route, boardSeq: number, destSeq: number): number {
  const segments = destSeq - boardSeq;   // integer, always positive
  return segments * route.perSegmentRate;
}
```

Zambia example: Chelston (2) → Kafue Market (5) = 3 segments × ZMW 5 = **ZMW 15**.

---

## 8. UI Design

### Colour tokens
```css
/* Brand */
--brand-primary:    #4F46E5;  /* indigo-600 */
--brand-secondary:  #7C3AED;  /* violet-600 */
--brand-bg:         #EEF2FF;  /* indigo-50 */

/* Status badges */
--status-open:      #F97316;  /* orange-500 */
--status-accepted:  #2563EB;  /* blue-600 */
--status-boarded:   #16A34A;  /* green-600 */
--status-completed: #6B7280;  /* gray-500 */
--status-cancelled: #DC2626;  /* red-600 */
```

### Mobile-first layout (375px baseline)
- Full-bleed header with route progress bar
- TabBar fixed to bottom (Passenger | Operator)
- Card-based content area with 16px side padding
- Floating "Reset Demo" button (bottom-right, 44px target)

### Request expiry timer
Passengers see a countdown: "Expires in 4:32". Rendered with `useEffect` + `setInterval`. When it hits 0:00, the request status changes to `expired` in the store automatically.

---

## 9. Optional FastAPI Backend (Phase 2)

If network-based real-time sync is desired (e.g. two devices in the same demo), a minimal FastAPI backend can replace the in-memory store.

```
kakoride/
└── api/
    ├── main.py          # FastAPI app, CORS, lifespan
    ├── routes.py        # /requests, /bookings, /service, /reset
    ├── state.py         # In-memory state (or PostgreSQL if deployed)
    ├── matching.py      # Port of matching.ts logic
    └── requirements.txt
```

Endpoints:
- `GET /api/state` — returns full app state (polling every 3s)
- `POST /api/requests` — submit passenger request
- `POST /api/requests/{id}/cancel` — cancel request
- `POST /api/bookings/{id}/accept` — operator accepts
- `POST /api/bookings/{id}/verify-pin` — PIN entry
- `POST /api/bookings/{id}/complete` — journey complete
- `POST /api/service/advance` — operator moves to next stop
- `POST /api/reset` — reset to seeded state
- `POST /api/ratings` — submit star rating

**This is NOT required for the MVP demo.** The store design mirrors this API so it can be added in an afternoon.

---

## 10. Deployment

### Frontend only (MVP)
- Build: `npm run build` → `dist/`
- Deploy: Vercel or Netlify drag-and-drop

### With backend (optional)
- Backend: `docker build -t kakoride-api .` → Cloud Run
- Frontend: set `VITE_API_URL=https://kakoride-api-xxx.run.app` env var

---

## 11. What is Reused from the Existing Project

| Asset | Reused? | Notes |
|---|---|---|
| `backend/db/001_core.sql` | Inspiration only | Schema concepts (stops, routes, segments) inform type design |
| `backend/db/002_markets.sql` | Seed data reference | Zambia stops and route names |
| `backend/src/service.mjs` | No | Too complex; KaKoRide matching is simpler |
| `src/app/` (Next.js) | No | KaKoRide is Vite, not Next.js |
| `.kiro/specs/kakoride/` | New | This spec |
| `tailwind.config.ts` | Possibly | Tailwind 4 config may differ |

The existing `backend/` and `android-app/` are **left untouched**.
