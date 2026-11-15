# KaKoRide deployment and provider setup

This repository includes deployment artifacts; it does not provision billing, phone numbers or paid services. The local simulator is not evidence of live WhatsApp/SMS delivery.

## Google Cloud / Firestore

1. Choose your project/region, enable Firestore Native mode, Cloud Run and Firebase Authentication Email/Password. Review the illustrative route definitions in `api/catalog.py` with an operator before launch.
2. Create a runtime service account with Firestore access and the Firebase Auth permissions needed to verify/revoke-check tokens. Grant only the required Secret Manager secret access. Deny all browser Firestore reads/writes using `kakoride/firestore.rules`.
3. Build from the **repository root**, with `docker build -f kakoride/api/Dockerfile ...`. The Dockerfile uses Python 3.14 and installs the pinned Python dependencies. Configure the Cloud Run service with `KAKORIDE_ENVIRONMENT=production`, `KAKORIDE_STORAGE=firestore`, `KAKORIDE_GOOGLE_CLOUD_PROJECT`, `KAKORIDE_FIRESTORE_NAMESPACE` and `KAKORIDE_WEB_ORIGINS` (your exact frontend HTTPS origin).
4. Store a random, stable 32+ character `KAKORIDE_CONTACT_HMAC_KEY` and provider credentials in Secret Manager. Changing the HMAC key changes contact identities; plan a migration rather than rotating it blindly. No local SQLite storage is accepted on Cloud Run.
5. Expose the service for signed public provider webhooks and Firebase-authenticated driver requests. The application verifies both. Configure readiness/liveness on `/readyz` and `/healthz`. Keep logs free of bodies/credentials; disable verbose provider HTTP logging.

The first implementation intentionally serializes **bounded pilot transactions** behind a Firestore revision record. Private records live under `kakoridePrivate/{namespace}/{collection}/{id}`. It loads at most 2,000 records and rejects new intake at 1,800 rather than returning partial demand. This is for the one-route demonstration, not a high-volume production architecture: profile costs/latency and replace full-state scans with indexed per-contact/event/request repositories before scaling. Transactions reject changes over 400 documents. The Firestore test uses an isolated local emulator namespace, never your live project.

## Driver authentication and access

Create an Email/Password user through your trusted Firebase administration process. Public driver self-registration and passenger accounts are not implemented. With trusted Google credentials and the production environment configured:

```powershell
python -m kakoride.api.provision driver@example.com --name "Driver Name" --route woodlands-town --days 30
python -m kakoride.api.provision admin@example.com --name "Administrator" --role admin
```

The account must already exist in Firebase Authentication. The CLI saves approval/role and optional route access; it never creates a known password. An administrator can grant/revoke route access from the web admin tools. Subscription access is manual/demo only: no money is charged by this implementation. Revoked/expired route access is enforced on every demand read.

## React hosting

The checked-in `firebase.json` hosts `kakoride/dist` with an SPA fallback. Before the production build, set `VITE_API_BASE_URL` to the actual Cloud Run HTTPS origin (no trailing slash), plus the Firebase web configuration in `kakoride/.env.local`. Do not put server keys or service-account credentials in VITE variables.

```powershell
npm --prefix kakoride ci
npm run build
firebase deploy --only hosting,firestore --project YOUR_PROJECT
```

Firebase CLI is required for deployment. The Hosting config does not invent a Cloud Run service-ID rewrite; the explicit API base URL is required. Add your Hosting domain to Firebase Auth authorized domains and to `KAKORIDE_WEB_ORIGINS`. No deployment URL is claimed until you deploy and verify it.

## WhatsApp Cloud API

Configure your Meta business app/WhatsApp number, permitted test recipients or approved production number, and these server-side secrets:

- `KAKORIDE_WHATSAPP_APP_SECRET`: verifies raw-body `X-Hub-Signature-256` HMAC.
- `KAKORIDE_WHATSAPP_VERIFY_TOKEN`: your chosen handshake secret.
- `KAKORIDE_WHATSAPP_ACCESS_TOKEN`, `KAKORIDE_WHATSAPP_PHONE_NUMBER_ID` and an available `KAKORIDE_WHATSAPP_GRAPH_VERSION`.

Webhook URL: `https://YOUR_API/webhooks/whatsapp`. Subscribe to messages. GET handles the verification challenge; POST separates text/button messages and delivery receipts. The sender uses the Graph Messages API and sends versioned reminder buttons. API acceptance is not proof of delivery; receipt status is stored separately.

Phone-less business-scoped WhatsApp IDs are supported when supplied as `from_user_id`; these cannot be cross-channel deduplicated with an SMS phone number. Phone-based senders normalize to E.164 and share the contact key with SMS. Free-text sends are suppressed after the 24-hour customer-service window; template outreach is not implemented. Current pricing/account permissions still require owner verification.

References: [Meta webhook format](https://developers.facebook.com/documentation/business-messaging/whatsapp/webhooks/overview), [service messages and delivery behavior](https://developers.facebook.com/documentation/business-messaging/whatsapp/messages/send-messages).

## Telerivet SMS / Android gateway

Provision Telerivet with your supported two-way route/Android gateway phone, local SIM, airtime, internet and power. Set `KAKORIDE_TELERIVET_PROJECT_ID`, `KAKORIDE_TELERIVET_API_KEY` and `KAKORIDE_TELERIVET_WEBHOOK_SECRET` server-side.

Create an **incoming-message Webhook API service** in Telerivet pointing to `https://YOUR_API/webhooks/sms/telerivet`, with the matching body `secret`. The implementation accepts Telerivet's form-encoded `incoming_message`, prefers `from_number_e164`, validates project ID and deduplicates message ID. The sender calls `/v1/projects/{project}/messages/send` using API-key HTTP Basic authentication. Unsupported incoming media types are ignored. Status notifications using this endpoint must have its matching body secret; a different Basic-auth status webhook contract needs a separate adapter configuration.

Example: `RIDE KAMWALA TOWN 20`, optional count `RIDE KAMWALA TOWN 20 2`. Quote stop names with spaces or use configured aliases. SMS reminders include a short request code: reply `1 CODE` for boarded / `2 CODE` for still waiting. Requiring a code prevents an old bare reply from renewing a different request. HELP, STATUS, CANCEL, STOP and START are supported.

References: [Telerivet webhook contract](https://telerivet.com/api/webhook), [REST API](https://telerivet.com/api/rest), [Zambia connectivity](https://www.telerivet.com/product/messaging/country/zm). Twilio is not used for inbound Zambia SMS.

## Durable scheduling

Configure `KAKORIDE_INTERNAL_JOB_AUDIENCE` to the Cloud Run origin and `KAKORIDE_JOB_SERVICE_ACCOUNT_EMAIL` to the authorized caller. Create a Cloud Scheduler job running every minute, POSTing `{}` to `/internal/jobs/sweep` with that service account's OIDC token and matching audience. The endpoint verifies signature, audience, issuer and exact verified email; a driver token cannot invoke it.

Optionally set `KAKORIDE_CLOUD_TASKS_QUEUE=projects/PROJECT/locations/REGION/queues/reminders`. The sweep reconciles deterministic task registrations from persisted jobs; callbacks use OIDC to the same internal endpoint. Grant Cloud Tasks enqueue and service-account act-as permissions only where needed. Scheduler reconciliation recovers a crash between database commit and task creation. Either mechanism may retry; persisted generations, transactions and outbox leases prevent duplicate demand effects. Provider sends can still be ambiguous after a timeout, so exactly-once delivery is not promised.

Local `npm run dev` runs an explicit five-second worker process; no request needs an open passenger browser. Production has no in-process timer dependency. Dispatch target is five minutes plus up to the one-minute sweep cadence/provider delay. Expiry is enforced on backend reads at ten minutes, regardless of worker/cleanup progress. [Firestore TTL is not instantaneous](https://firebase.google.com/docs/firestore/ttl) and is not used for demand correctness.

## Retention, failures and validation

Periodic sweeps prune old event/delivery records after 48 hours and expired demand/jobs after 24 hours. Inactive contacts are pruned after 48 hours; opted-out contacts are retained to honor STOP. Define an approved production privacy/retention policy, encryption/key management and scaled abuse controls before public launch. Outbox failures retry with bounded backoff and appear in admin health; `sent` means the provider accepted the send, not confirmed delivery. Provider exceptions are not exposed/logged with credentials.

The repository tests synthetic traffic and authenticated provider fixtures. A live acceptance demonstration still requires actual credentials and a real WhatsApp/SMS message and boarding response visibly changing driver totals. Container execution, production IAM, managed Scheduler/Tasks and real-provider delivery need staging verification after provisioning.
