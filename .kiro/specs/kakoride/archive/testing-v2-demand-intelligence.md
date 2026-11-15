# KaKoRide: Testing Strategy (v2)

| Layer | Tool | What it proves | Needs |
|---|---|---|---|
| Pure logic | Vitest | Route direction, destinations ahead, multi-route, demand counts and totals, no double counting, passed stops hidden, expiry filtering, lifecycle transitions | nothing |
| Firestore rules | `@firebase/rules-unit-testing` on the emulator | Subscription gating (none/wrong route/expired), privacy (passengers cannot read each other), one request per session, field bounds, expiry window, demo flag | Java 11+ |
| UI flow | Vitest + Testing Library | Passenger and driver screens render and react to data changes; reminder prompt; dev-only control hidden in production | nothing (data layer faked) |
| Two-session demo | Manual script, run before every submission | Real-time update across independent browsers on the hosted project | Firebase project |

Required cases (from the brief): route direction, demand counts, duplicate requests, subscription access, request expiration.

Honest limits: rules tests cannot run without Java; time-based behaviour is tested with injected clocks, and server-time behaviour is verified manually on the hosted/emulated project.
