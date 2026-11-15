# Current Cloud Run deployment

Backend deployed on 15 November 2026.

- Project: `project-c50f6c12-bd47-4316-817`
- Region: `us-central1`
- Service: `kokoride`
- API: `https://kokoride-srzbbfc7ja-uc.a.run.app`
- WhatsApp callback: `https://kokoride-srzbbfc7ja-uc.a.run.app/webhooks/whatsapp`
- Firestore: `(default)`, namespace `kakoride`. The existing `agent-engine` database is separate.
- Runtime identity: `kakoride-api` service account.
- Job identity: `kakoride-jobs` service account.
- Cloud Scheduler: `kakoride-sweep`, every minute, authenticated POST.
- Cloud Tasks: `kakoride-reminders`, one concurrent dispatch.
- Credentials: Secret Manager references; no private credentials in Git or the build upload.

The existing Developer Connect trigger builds `kakoride/api/Dockerfile` on pushes to `main`, pushes the image, and updates the service. It preserves the service environment, secret references, and runtime identity. The root `cloudbuild.yaml` is available for a manual build with an explicit `_IMAGE` substitution. `.gcloudignore` restricts manual build uploads to backend files.

## Finish connecting the client applications

1. In the same Meta app used for the current test number, replace the temporary Cloudflare callback with the Cloud Run callback above. Keep the current private verification token and the `messages` subscription.
2. Test with a fresh passenger message after saving the callback. Local development data is not copied into the cloud database.
3. Deploy the web dashboard to Vercel with `VITE_API_BASE_URL` set to the API origin and Firebase web configuration for this project. Set the exact Vercel origin in `KAKORIDE_WEB_ORIGINS`; add that domain to Firebase Authentication authorized domains. Currently only the two local development web origins are allowed.
4. Enable Firebase Email/Password authentication, create the intended driver/admin accounts, and grant their roles/routes using `provision.py`. Production does not accept demo driver sessions from the local backend.
5. Replace the temporary Meta token with an appropriate system-user token for longer running operation. Add a new Secret Manager version, then update the Cloud Run secret reference explicitly; the deployment pins version 1 to avoid silently changing credentials.

Readiness is `/readyz`; liveness is `/livez`. Driver routes require authentication, demo endpoints are disabled, and direct browser access to Firestore is denied. A successful signed empty webhook test verifies signature processing without creating passenger requests or sending messages. A real passenger acceptance test is still required after changing Meta's callback.

The test number still has Meta's test-recipient restrictions. Public passenger service needs a production WhatsApp number. SMS is not configured on this service yet.
