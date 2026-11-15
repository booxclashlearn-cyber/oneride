# KaKoRide driver web

The active React/TypeScript frontend is in this directory. Passengers use WhatsApp/SMS; this site is for drivers/admins. Development adds an explicitly labelled messaging simulator. Private request/contact data is never read directly from Firestore.

From the repository root, run `npm run dev` to start the frontend, FastAPI and local worker. Open http://127.0.0.1:5173. For frontend-only development, `npm --prefix kakoride run dev` expects the API at 127.0.0.1:8080 via Vite's proxy.

- `npm --prefix kakoride test`: driver presentation and freshness tests.
- `npm run build`: frontend type-check/production build.
- Production: configure HTTPS VITE_API_BASE_URL and Firebase web authentication values before building. Provider secrets belong only on the API.

See the [root README](../README.md), [API documentation](api/README.md), and [deployment guide](api/DEPLOYMENT.md). The previous passenger-browser form, anonymous auth, direct Firestore writes, booking/PIN screens and Zustand dependency are no longer part of the application.