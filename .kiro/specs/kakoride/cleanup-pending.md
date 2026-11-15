# Preserved legacy artifacts — cleanup awaiting explicit approval

Automatic approval review rejected broad deletion because it included credentials, local database data, generated artifacts and dependencies. The new KaKoRide application does not load these files. No contents/secrets are included here.

The inspected OneRide/Supabase source folders, Next.js-specific source configuration, old environment template and original web manifest/icons have already been removed. Root commands/manifests now run KaKoRide only.

Remaining legacy paths:

- `.env.local`
- `.localdb`
- `.next`
- `.next-dev`
- `node_modules`
- `public`
- `.scratch`
- `tsconfig.tsbuildinfo`

The shared `.tools/` folder is retained: its Java runtime now supports Firestore testing and it contains browser-test tooling. Do not delete it as a legacy application dependency.

A further explicit cleanup approval should cover the listed credentials/data/generated paths before they are permanently deleted. The request to implement was completed independently of that cleanup gate.
