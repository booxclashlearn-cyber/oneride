"""Provider senders and leased outbox dispatch. No external send inside a DB transaction."""
import uuid
import httpx


class Sender:
    def __init__(self, settings):
        self.settings = settings

    def send(self, address, message):
        cfg = self.settings
        if message["channel"] == "whatsapp":
            if not cfg.whatsapp_token or not cfg.whatsapp_number:
                raise RuntimeError("WhatsApp sender is not configured")
            payload = {"messaging_product": "whatsapp", "type": "text", "text": {"body": message["text"]}}
            if address.startswith("wa:"):
                payload["recipient"] = address[3:]
            else:
                payload["to"] = address.lstrip("+")
            if message["context"]:
                context = message["context"]
                payload.pop("text", None)
                payload["type"] = "interactive"
                payload["interactive"] = {"type": "button", "body": {"text": message["text"]}, "action": {"buttons": [{"type": "reply", "reply": {"id": f"reply:{context['request']}:{context['version']}:{i}", "title": label}} for i, label in [(1, "Yes, boarded"), (2, "Still waiting")]]}}
            response = httpx.post(f"https://graph.facebook.com/{cfg.graph_version}/{cfg.whatsapp_number}/messages", headers={"Authorization": "Bearer " + cfg.whatsapp_token}, json=payload, timeout=15)
            response.raise_for_status()
            return response.json()["messages"][0]["id"]
        if not cfg.sms_token or not cfg.sms_project:
            raise RuntimeError("Telerivet sender is not configured")
        response = httpx.post(f"https://api.telerivet.com/v1/projects/{cfg.sms_project}/messages/send", auth=(cfg.sms_token, ""), data={"to_number": address, "content": message["text"]}, timeout=15)
        response.raise_for_status()
        return response.json()["id"]


def dispatch(engine, sender=None):
    sender = sender or Sender(engine.settings)
    summary = {"sent": 0, "simulated": 0, "failed": 0}
    # A short lease bounds retries across concurrent worker processes/restarts.
    for _ in range(30):
        lease = uuid.uuid4().hex
        def claim(s):
            now = engine.now(s)
            for key, m in s["outbox"].items():
                if m["status"] not in ("pending", "sending") or m["dueAt"] > now or (m["status"] == "sending" and m.get("leaseUntil", 0) > now):
                    continue
                c = s["contacts"].get(m["contact"])
                if not c:
                    m["status"] = "cancelled"
                    continue
                if m.get("consentVersion", 0) != c.get("consentVersion", 0):
                    m["status"] = "cancelled"
                    continue
                if m["context"]:
                    r = s["demands"].get(m["context"]["request"], {})
                    if c["stopped"] or r.get("status") != "active" or r.get("version") != m["context"]["version"] or r.get("expiresAt", 0) <= now:
                        m["status"] = "cancelled"
                        continue
                if m["channel"] == "whatsapp" and now - c["channels"].get("whatsapp", 0) >= 86400:
                    m.update({"status": "failed", "error": "customer_service_window_closed"})
                    continue
                m.update({"status": "sending", "lease": lease, "leaseUntil": now + 60, "attempts": m["attempts"] + 1})
                return key, dict(m), c["address"]
            return None
        claimed = engine.store.atomic(claim)
        if not claimed:
            break
        key, message, address = claimed
        error = provider_id = None
        try:
            provider_id = "simulated" if message["simulated"] else sender.send(address, message)
        except Exception:
            # Never persist or log provider exceptions: they may contain tokens/numbers.
            error = "provider_send_failed"
        def finish(s):
            m = s["outbox"].get(key)
            if not m or m.get("lease") != lease:
                return
            if error:
                m.update({"status": "pending" if m["attempts"] < 5 else "failed", "error": error, "dueAt": engine.now(s) + min(600, 15 * 2 ** m["attempts"])})
            else:
                m.update({"status": "simulated" if message["simulated"] else "sent", "providerId": provider_id, "error": None})
        engine.store.atomic(finish)
        summary["failed" if error else "simulated" if message["simulated"] else "sent"] += 1
    return summary
