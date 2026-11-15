# Test KaKoRide with actual WhatsApp and SMS messages

The app's simulator does not send actual messages. Real tests need provider accounts/credentials and a temporary public HTTPS URL. Cloud deployment is not required for a local test.

## 1. Prepare your local environment

From `C:\Users\chilo\Desktop\oneride`, create the new server environment only if it does not already exist:

```powershell
if (!(Test-Path .\kakoride\api\.env)) {
    Copy-Item .\kakoride\api\.env.example .\kakoride\api\.env
}
```

Edit `kakoride/api/.env` with the relevant credentials below. Never put provider tokens in the frontend environment or paste them into chat. Keep development mode and SQLite for this local test. Stop any previous dev command with Ctrl+C, then restart:

```powershell
npm run dev
```

This now starts the dashboard at 5173, the private local API at 8080, a **webhook-only listener at 8081**, and the local reminder/outbox worker. Keep the command running: the worker delivers provider replies and five-minute prompts.

Open http://127.0.0.1:5173 and choose Open demo dashboard. Select **Woodlands → Town Centre**, current station **Woodlands**. A request boarding at Kamwala will then be ahead of you and visible in totals. Real contacts are separate from synthetic simulator contacts.

## 2. Give the providers an HTTPS callback

Install `cloudflared` for Windows from [Cloudflare's official downloads](https://developers.cloudflare.com/tunnel/downloads/). In a second terminal:

```powershell
cloudflared tunnel --url http://127.0.0.1:8081
```

It prints a temporary URL such as `https://YOUR-HOST.trycloudflare.com`. Use the actual printed hostname in the callback URLs below. Keep this terminal open. A Quick Tunnel does not require a Cloudflare account/domain, and its hostname changes on restart; update provider callbacks whenever it changes. Do not enable interactive email authentication on this tunnel because providers cannot answer that challenge. [Official Quick Tunnel instructions](https://developers.cloudflare.com/tunnel/get-started/quick-tunnels/).

Expose **8081**, not 8080 or 5173. The 8081 entry point only permits WhatsApp webhook GET/POST and Telerivet webhook POST; it does not expose demo login, driver/admin APIs, documentation or internal jobs. Provider authentication remains required. This is a local testing port; the production Cloud Run app already disables demo endpoints.

## 3. WhatsApp

1. Sign into Meta for Developers, create/select an app with the WhatsApp use case and open its WhatsApp API testing/setup panel. Obtain the test business number, add/verify your personal phone as an allowed test recipient, and obtain the access token and **Phone Number ID**. The ID is not the displayed telephone number or WhatsApp Business Account ID. Follow the setup shown in your logged-in dashboard; labels may vary.
2. Put the following in `kakoride/api/.env`, replacing placeholders locally:

```dotenv
KAKORIDE_WHATSAPP_APP_SECRET=YOUR_META_APP_SECRET
KAKORIDE_WHATSAPP_VERIFY_TOKEN=YOUR_OWN_RANDOM_VERIFICATION_SECRET
KAKORIDE_WHATSAPP_ACCESS_TOKEN=YOUR_META_ACCESS_TOKEN
KAKORIDE_WHATSAPP_PHONE_NUMBER_ID=YOUR_PHONE_NUMBER_ID
KAKORIDE_WHATSAPP_GRAPH_VERSION=v27.0
```

3. Restart `npm run dev` after saving credentials. Configure the WhatsApp callback URL:

```text
https://YOUR-HOST.trycloudflare.com/webhooks/whatsapp
```

Use the exact `KAKORIDE_WHATSAPP_VERIFY_TOKEN` value as Meta's verify token, verify/save, then subscribe to **messages**. The app secret verifies incoming POST signatures; it is different from your chosen verify token. Meta documents the configuration panel and message webhook subscription [here](https://developers.facebook.com/documentation/business-messaging/whatsapp/webhooks/overview).
4. From your allowed personal phone, send the test business number:

```text
RIDE KAMWALA TOWN 20
```

Or send `Hi` and answer the numbered boarding/destination questions, then enter `20` as the fare. One passenger is the default; `20 2` at the fare step means two passengers. The backend should return a receipt and the driver dashboard should add one passenger/K20 for the single-person command.
5. Wait five actual minutes. Tap **Yes, boarded** to remove the request, or **Still waiting** to renew it. No response expires demand at ten minutes. For the first real test, use actual time instead of advancing the shared development clock.

Meta test recipient eligibility/token availability is controlled by your account. If the access token expires, obtain a current one, update `.env` and restart. No successful live Meta delivery is claimed until you complete this phone test.

## 4. SMS using Telerivet

1. Create a Telerivet project. Install/connect its Android Gateway app on a dedicated Android phone with a local SIM. Keep the phone online, powered and with SMS airtime. Use a **second phone** as the passenger, sending to the gateway SIM's telephone number.
2. Obtain the Telerivet Project ID and REST API key. Choose an incoming-webhook secret. Add:

```dotenv
KAKORIDE_TELERIVET_PROJECT_ID=YOUR_PROJECT_ID
KAKORIDE_TELERIVET_API_KEY=YOUR_API_KEY
KAKORIDE_TELERIVET_WEBHOOK_SECRET=YOUR_OWN_RANDOM_SMS_WEBHOOK_SECRET
```

3. Restart `npm run dev`. In Telerivet, add an **incoming-message Webhook API service** with:

```text
https://YOUR-HOST.trycloudflare.com/webhooks/sms/telerivet
```

Set that service's `secret` to the exact matching environment value. This is the incoming-message service, not a separate status-only webhook. [Official Telerivet webhook setup](https://telerivet.com/api/webhook).
4. From the second phone, text the gateway SIM:

```text
RIDE KAMWALA TOWN 20
```

Expect a receipt and demand in the driver dashboard. Add a final count for a group, e.g. `RIDE CHILENJE TOWN 25 2`.
5. The five-minute SMS prompt contains a short request code. Reply `1 CODE` for boarded or `2 CODE` for still waiting, replacing CODE with the exact received code. `CANCEL` closes demand; `STOP` opts out; `START` opts back in. If the same phone already has active WhatsApp demand, that SMS does not create extra demand. Cancel the old request or use a different passenger number when testing a separate request.

## 5. If messages do not appear

| Symptom | Check |
|---|---|
| Callback cannot verify/connect | App/tunnel terminals running; current hostname; port 8081; exact callback path; restart after saving `.env` |
| WhatsApp GET verification fails | Chosen verify token exactly matches; do not substitute app secret/access token |
| WhatsApp POST gets 403 | Meta app secret and Phone Number ID match the configured app/number |
| Request appears but no reply arrives | Worker running; sender token/project/phone configured; test recipient allowed; gateway online/airtime; provider logs |
| SMS never reaches the webhook | Telerivet phone connected; incoming-message service enabled; sender allowed if gateway Test Mode is enabled |
| No demand visible | Correct subscribed route/current station; boarding must be strictly ahead; request not expired; use STATUS/CANCEL to inspect/restart |
| Duplicate request does not increase totals | Expected: one active demand request per matching contact across both channels |

Use local admin tools for outbox pending/failed counts, and provider logs for delivery errors. A provider accepting a send is not confirmed delivery. SMS/provider charges may apply. Do not leave a temporary tunnel running after testing.

### Meta shows an incoming payload but KaKoRide receives nothing

Seeing a payload in Meta's API-testing viewer proves phone-to-Meta intake, not delivery to this application's callback. Both the app-level `messages` subscription and the WhatsApp account's app subscription must exist. The built-in `WA DevX Webhook Events 1P App` subscription alone does not register KaKoRide. With the correct app-issued token and management permission, the account link is registered through Meta's `/{WHATSAPP_ACCOUNT_ID}/subscribed_apps` endpoint. Check which app the token belongs to before linking; do not confuse the phone ID with the account ID.

The configured callback hostname must also match the currently running Quick Tunnel. Its public hostname can be inspected locally at `http://127.0.0.1:20241/quicktunnel` (the next ports through 20245 may be used if multiple tunnels are running). Update Meta's callback manually with the current hostname plus `/webhooks/whatsapp`, use the existing private verify token, and send a fresh phone message after verification. Do not print the verify token or include it in screenshots.

## Verification note

The webhook-only listener's regression test now passes in `api/tests/test_http.py`: all seven HTTP tests passed, covering allowed callback paths, signature/secret checks and denial of demo/admin/internal endpoints. A read-only Meta API check also confirmed that the user's configured access token can read the configured phone number; no test message was sent. Run locally:

```powershell
python -m pytest kakoride/api/tests/test_http.py -q
```
