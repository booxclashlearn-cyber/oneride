import hashlib
import hmac
import re
import secrets
import shlex
import time
import uuid
from .catalog import ROUTES, STOPS, matching, menu, resolve_stop, stop_name


class DomainError(Exception):
    def __init__(self, message, status=400):
        self.message, self.status = message, status
        super().__init__(message)


def require(condition, message, status=400):
    if not condition:
        raise DomainError(message, status)


def digest(value):
    return hashlib.sha256(value.encode()).hexdigest()


class Engine:
    def __init__(self, store, settings, clock=time.time):
        self.store, self.settings, self.clock = store, settings, clock
        if settings.development:
            self.store.atomic(self._seed)

    def now(self, state):
        return int(self.clock()) + state["meta"].get("clock", {}).get("offset", 0)

    def _seed(self, s):
        now = self.now(s)
        for uid, role in [("demo-driver", "driver"), ("demo-locked", "driver"), ("demo-admin", "admin")]:
            s["drivers"].setdefault(uid, {"uid": uid, "name": {"demo-driver": "Moses Banda", "demo-locked": "Trial driver", "demo-admin": "Demo administrator"}[uid], "role": role, "approved": True})
        for route in ROUTES:
            s["entitlements"].setdefault("demo-driver_" + route["id"], {"uid": "demo-driver", "routeId": route["id"], "status": "active", "expiresAt": now + 86400 * 30, "source": "local demo"})

    def login_demo(self, profile):
        require(self.settings.development, "Not found", 404)
        require(profile in ("driver", "locked", "admin"), "Unknown demo profile")
        uid = {"driver": "demo-driver", "locked": "demo-locked", "admin": "demo-admin"}[profile]
        token = secrets.token_urlsafe(32)
        def apply(s):
            s["sessions"][digest(token)] = {"uid": uid, "expiresAt": self.now(s) + 43200}
            return {"token": token, "profile": s["drivers"][uid]}
        return self.store.atomic(apply)

    def demo_identity(self, token):
        def apply(s):
            session = s["sessions"].get(digest(token), {})
            require(session.get("expiresAt", 0) > self.now(s), "Sign in again", 401)
            return session["uid"]
        return self.store.atomic(apply)

    def driver(self, uid):
        def apply(s):
            user = s["drivers"].get(uid)
            require(user and user.get("approved"), "Driver access has not been approved", 403)
            now = self.now(s)
            rights = [e for e in s["entitlements"].values() if e["uid"] == uid and e["status"] == "active" and e["expiresAt"] > now]
            return {"profile": user, "entitlements": rights, "routes": [r for r in ROUTES if any(e["routeId"] == r["id"] for e in rights)], "stops": STOPS, "serverNow": now}
        return self.store.atomic(apply)

    def grant(self, actor, uid, route_id, days, active=True):
        require(route_id in [r["id"] for r in ROUTES] and type(days) is int and 1 <= days <= 365, "Invalid route or duration")
        def apply(s):
            require(s["drivers"].get(actor, {}).get("role") == "admin", "Administrator required", 403)
            require(uid in s["drivers"], "Driver not found", 404)
            record = {"uid": uid, "routeId": route_id, "status": "active" if active else "inactive", "expiresAt": self.now(s) + days * 86400, "source": "manual grant"}
            s["entitlements"][uid + "_" + route_id] = record
            return record
        return self.store.atomic(apply)

    def demand(self, uid, route_id, station):
        def apply(s):
            now = self.now(s)
            require(s["drivers"].get(uid, {}).get("approved"), "Driver access has not been approved", 403)
            entitlement = s["entitlements"].get(uid + "_" + route_id, {})
            require(entitlement.get("status") == "active" and entitlement.get("expiresAt", 0) > now, "An active route subscription is required", 403)
            route = next((r for r in ROUTES if r["id"] == route_id), None)
            require(route and station in route["stopIds"], "Choose a station on this route")
            groups, deadlines = {}, []
            for request in s["demands"].values():
                if request["status"] != "active" or request["expiresAt"] <= now or route_id not in request["routes"]:
                    continue
                if route["stopIds"].index(request["boarding"]) <= route["stopIds"].index(station):
                    continue
                deadlines.append(request["expiresAt"])
                group = groups.setdefault(request["boarding"], {"stopId": request["boarding"], "name": stop_name(request["boarding"]), "passengers": 0, "offeredMinor": 0, "destinations": {}})
                dest = group["destinations"].setdefault(request["destination"], {"stopId": request["destination"], "name": stop_name(request["destination"]), "passengers": 0, "offeredMinor": 0, "minFareMinor": request["fareMinor"], "maxFareMinor": request["fareMinor"]})
                for item in (group, dest):
                    item["passengers"] += request["count"]
                    item["offeredMinor"] += request["count"] * request["fareMinor"]
                dest["minFareMinor"] = min(dest["minFareMinor"], request["fareMinor"])
                dest["maxFareMinor"] = max(dest["maxFareMinor"], request["fareMinor"])
            ordered = []
            for stop in route["stopIds"]:
                if stop in groups:
                    g = groups[stop]
                    g["destinations"] = list(g["destinations"].values())
                    ordered.append(g)
            return {"route": route, "groups": ordered, "passengers": sum(g["passengers"] for g in ordered), "waitingStops": len(ordered), "offeredMinor": sum(g["offeredMinor"] for g in ordered), "serverNow": now, "generatedAt": now, "nextExpiryAt": min(deadlines) if deadlines else None, "accessExpiresAt": entitlement["expiresAt"]}
        return self.store.atomic(apply)

    def contact_key(self, address):
        return hmac.new(self.settings.contact_key.encode(), address.encode(), hashlib.sha256).hexdigest()

    def _active(self, s, contact, now):
        r = s["demands"].get(contact.get("active", ""))
        if r and r["status"] == "active":
            if r["expiresAt"] > now:
                return r
            r["status"] = "expired"
        return None

    def _send(self, s, key, channel, text, now, logical, context=None, simulated=False):
        message_id = digest(logical)
        if message_id not in s["outbox"]:
            if channel == "sms":
                text = text.replace("→", ">").replace("–", "-").replace("’", "'")
            contact = s["contacts"][key]
            contact["messageSequence"] = contact.get("messageSequence", 0) + 1
            s["outbox"][message_id] = {"contact": key, "channel": channel, "text": text, "createdAt": now, "sequence": contact["messageSequence"], "consentVersion": contact.get("consentVersion", 0), "dueAt": now, "status": "pending", "attempts": 0, "context": context, "simulated": simulated}

    def _window(self, s, r, now):
        r.update({"version": r.get("version", 0) + 1, "lastConfirmedAt": now, "nextReminderAt": now + 300, "expiresAt": now + 600, "promptedAt": None})
        job_id = r["id"] + "_" + str(r["version"])
        s["jobs"][job_id] = {"request": r["id"], "version": r["version"], "dueAt": now + 300, "status": "pending"}

    def _create(self, s, key, contact, channel, board, dest, fare, count, now, simulated):
        require(matching(board, dest), "Those stops do not form a supported forward route")
        require(type(fare) is int and 1 <= fare <= 1000 and type(count) is int and 1 <= count <= 14, "Use a whole fare K1–K1000 and 1–14 passengers")
        r = {"id": uuid.uuid4().hex, "contact": key, "boarding": board, "destination": dest, "fareMinor": fare * 100, "count": count, "routes": matching(board, dest), "status": "active", "channel": channel, "createdAt": now, "simulated": simulated}
        self._window(s, r, now)
        s["demands"][r["id"]] = r
        contact["active"] = r["id"]
        if channel == "sms":
            return f"Active: {stop_name(board)} > {stop_name(dest)}. {count} pax, K{fare} each. No seat reserved. Check-in in 5 min; expires in 10 min without reply. CANCEL to close."
        return f"Request active! {stop_name(board)} → {stop_name(dest)}. {count} passenger(s), K{fare} each. No seat is reserved. We'll ask if you boarded in 5 minutes; no reply expires it at 10 minutes. CANCEL to close."

    def ingest(self, provider, event_id, channel, address, text, simulated=False, event_time=None):
        require(channel in ("whatsapp", "sms") and 1 <= len(text.strip()) <= 500 and 1 <= len(event_id) <= 250, "Invalid message")
        require(bool(re.fullmatch(r"\+[1-9]\d{6,14}", address)) or (channel == "whatsapp" and bool(re.fullmatch(r"wa:[A-Za-z0-9._-]{1,150}", address))), "Invalid sender")
        require(not simulated or self.settings.development, "Simulator is disabled", 404)
        key = self.contact_key(("sim:" if simulated else "") + address)
        event_key = digest(provider + ":" + event_id)
        def apply(s):
            now = self.now(s)
            if event_key in s["events"]:
                return {"accepted": True, "duplicate": True}
            require(sum(len(s[t]) for t in s) < 1800, "Pilot capacity reached; run retention or scale storage", 503)
            if event_time is not None and (event_time < now - 1200 or event_time > now + 120):
                return {"accepted": True, "ignored": "old_or_future_event"}
            contact = s["contacts"].setdefault(key, {"address": address, "stopped": False, "active": None, "channels": {}})
            last_events = contact.setdefault("lastEventAt", {})
            if event_time is not None and event_time < last_events.get(channel, 0):
                s["events"][event_key] = {"createdAt": now}
                return {"accepted": True, "ignored": "reordered_event"}
            last_events[channel] = event_time if event_time is not None else now
            contact["channels"][channel] = now
            contact["lastSeenAt"] = now
            bucket = now // 60
            if contact.get("rateBucket") != bucket:
                contact.update({"rateBucket": bucket, "rateCount": 0})
            require(contact.get("rateCount", 0) < 20, "Too many messages; wait one minute", 429)
            contact["rateCount"] = contact.get("rateCount", 0) + 1
            s["events"][event_key] = {"createdAt": now}
            active = self._active(s, contact, now)
            conversation_id = key + "_" + channel
            conversation = s["conversations"].get(conversation_id, {})
            if conversation.get("expiresAt", 0) <= now:
                conversation = {}
            command = text.strip()
            upper = command.upper()
            reply = None
            if upper == "STOP":
                contact["stopped"] = True
                contact["consentVersion"] = contact.get("consentVersion", 0) + 1
                if active:
                    active["status"] = "cancelled"
                conversation = {}
                reply = "Your request is closed. Automated messages stopped. Send START to opt in again."
            elif upper == "START":
                contact["stopped"] = False
                contact["consentVersion"] = contact.get("consentVersion", 0) + 1
                reply = "Welcome to KaKoRide! Where are you boarding?\n" + menu()
                conversation = {"step": "boarding", "expiresAt": now + 600}
            elif contact["stopped"]:
                reply = "Messages are stopped. Send START to opt in."
            elif upper == "CANCEL":
                if active:
                    active["status"] = "cancelled"
                conversation = {}
                reply = "Request cancelled. Send HI or RIDE to start a new one."
            elif upper in ("HELP", "STATUS"):
                reply = (f"Still active: {stop_name(active['boarding'])} → {stop_name(active['destination'])}, K{active['fareMinor'] // 100} each, {active['count']} passenger(s). CANCEL to close." if active and upper == "STATUS" else 'SMS: RIDE KAMWALA TOWN 20 [count]. Quote names with spaces. Send HI for guided steps. CANCEL closes demand; STOP opts out. No seat is reserved.')
            elif upper.startswith("REPLY:") or (active and active.get("promptedAt") and upper.split()[0] in ("1", "2", "YES", "WAIT")):
                parts = command.split(":") if upper.startswith("REPLY:") else []
                valid = active and active.get("promptedAt") and channel == active["channel"]
                if parts:
                    valid = valid and len(parts) == 4 and parts[1] == active["id"] and parts[2] == str(active["version"])
                    action = parts[-1]
                else:
                    tokens = upper.split()
                    # SMS always needs the short code: prevents an old bare reply changing a later prompt.
                    valid = valid and channel == "sms" and len(tokens) == 2 and tokens[1] == (active["id"][:6] + str(active["version"])).upper()
                    action = tokens[0]
                valid = valid and (event_time is None or event_time >= active["promptedAt"])
                if not valid:
                    reply = "That reply has expired or needs its request code. Use the latest buttons/code, or STATUS."
                elif action in ("1", "YES"):
                    active["status"] = "completed"
                    reply = "Thanks! Your request is complete and removed from driver demand. Safe journey!"
                elif action in ("2", "WAIT"):
                    require(active["version"] < 12, "Please send a new request after this waiting period")
                    self._window(s, active, now)
                    reply = "Still waiting confirmed. We'll ask again in 5 minutes; no reply expires your request in 10 minutes."
                else:
                    reply = "Choose 1 for boarded or 2 for still waiting, with the latest request code."
            elif active:
                reply = "You already have an active request. Send STATUS to check or CANCEL before changing it."
            elif upper.startswith("RIDE "):
                try:
                    parts = shlex.split(command)
                    require(len(parts) in (4, 5), 'Use RIDE KAMWALA TOWN 20 [count]; quote names containing spaces.')
                    board, dest = resolve_stop(parts[1]), resolve_stop(parts[2])
                    require(board and dest, "Unknown or ambiguous stop. Send HI for the numbered stop menu.")
                    require(parts[3].isdigit() and (len(parts) == 4 or parts[4].isdigit()), "Fare and count must be whole numbers")
                    reply = self._create(s, key, contact, channel, board, dest, int(parts[3]), int(parts[4]) if len(parts) == 5 else 1, now, simulated)
                    conversation = {}
                except (DomainError, ValueError) as error:
                    reply = str(error)
            elif conversation.get("step") == "boarding":
                board = resolve_stop(command)
                if board:
                    choices = [st["id"] for st in STOPS if matching(board, st["id"])]
                    conversation.update({"step": "destination", "boarding": board, "choices": choices})
                    reply = "Where are you going?\n" + menu(choices)
                else:
                    reply = "Choose a boarding stop:\n" + menu()
            elif conversation.get("step") == "destination":
                dest = resolve_stop(command, conversation["choices"])
                if dest:
                    conversation.update({"step": "fare", "destination": dest})
                    reply = "How much can you pay per person? Enter K1 to K1000 (one passenger). For a group, add the count: 20 2."
                else:
                    reply = "Choose a destination from this list:\n" + menu(conversation["choices"])
            elif conversation.get("step") == "fare":
                amount = re.fullmatch(r"K?(\d{1,4})(?:\s+(\d{1,2}))?", upper)
                if amount and 1 <= int(amount[1]) <= 1000 and (not amount[2] or 1 <= int(amount[2]) <= 14):
                    reply = self._create(s, key, contact, channel, conversation["boarding"], conversation["destination"], int(amount[1]), int(amount[2]) if amount[2] else 1, now, simulated)
                    conversation = {}
                else:
                    reply = "Enter a whole fare per person from K1 to K1000. For a group, write fare then count: 20 2."
            elif conversation.get("step") == "count":
                if command.isdigit() and 1 <= int(command) <= 14:
                    reply = self._create(s, key, contact, channel, conversation["boarding"], conversation["destination"], conversation["fare"], int(command), now, simulated)
                    conversation = {}
                else:
                    reply = "Reply with a passenger count from 1 to 14."
            else:
                reply = "Welcome to KaKoRide! Where are you boarding?\n" + menu()
                conversation = {"step": "boarding", "expiresAt": now + 600}
            s["conversations"][conversation_id] = conversation
            self._send(s, key, channel, reply, now, event_key, simulated=simulated)
            # STOP cancels pending reminders; the opt-out receipt itself remains deliverable.
            return {"accepted": True, "duplicate": False}
        return self.store.atomic(apply)

    def sweep(self):
        def apply(s):
            now = self.now(s)
            queued = 0
            expired = processed_jobs = 0
            for r in s["demands"].values():
                if r["status"] == "active" and r["expiresAt"] <= now:
                    r["status"] = "expired"
                    expired += 1
                    if expired >= 25:
                        break
            for job_id, job in s["jobs"].items():
                if processed_jobs >= 25:
                    break
                if job["status"] != "pending" or job["dueAt"] > now:
                    continue
                processed_jobs += 1
                r = s["demands"].get(job["request"], {})
                if r.get("status") == "active" and r["version"] == job["version"] and r["expiresAt"] > now and not s["contacts"][r["contact"]]["stopped"]:
                    code = r["id"][:6].upper() + str(r["version"])
                    text = "Have you boarded a bus?"
                    if r["channel"] == "sms":
                        text += f" Reply 1 {code} for Yes, or 2 {code} for Still waiting."
                    context = {"request": r["id"], "version": r["version"]}
                    self._send(s, r["contact"], r["channel"], text, now, "reminder:" + job_id, context, r["simulated"])
                    r["promptedAt"] = now
                    queued += 1
                job["status"] = "done"
            # Bound retention without forgetting fresh provider retries.
            deleted = 0
            for table in ("events", "outbox", "sessions", "conversations"):
                for key, item in list(s[table].items()):
                    if deleted >= 100:
                        break
                    if table == "events" and item["createdAt"] < now - 172800:
                        del s[table][key]
                        deleted += 1
                    elif table == "sessions" and item["expiresAt"] <= now:
                        del s[table][key]
                        deleted += 1
                    elif table == "conversations" and item.get("expiresAt", 0) < now - 86400:
                        del s[table][key]
                        deleted += 1
                    elif table == "outbox" and item["createdAt"] < now - 172800 and item["status"] in ("sent", "simulated", "cancelled", "failed"):
                        del s[table][key]
                        deleted += 1
            for request_id, r in list(s["demands"].items()):
                if deleted >= 150:
                    break
                if r["status"] != "active" and r["expiresAt"] < now - 86400:
                    del s["demands"][request_id]
                    deleted += 1
                    for job_id, job in list(s["jobs"].items()):
                        if job["request"] == request_id:
                            del s["jobs"][job_id]
                            deleted += 1
            for key, c in list(s["contacts"].items()):
                if deleted >= 175:
                    break
                if not c["stopped"] and c.get("lastSeenAt", now) < now - 172800 and not self._active(s, c, now):
                    del s["contacts"][key]
                    deleted += 1
            return {"remindersQueued": queued, "serverNow": now}
        return self.store.atomic(apply)

    def delivery(self, provider_id, status, errors=None):
        if status not in ("queued", "pending", "sent", "delivered", "read", "failed", "not_delivered"):
            return
        def apply(s):
            ranks = {"queued": 0, "pending": 0, "sent": 1, "delivered": 2, "read": 3, "failed": 4, "not_delivered": 4}
            for message in s["outbox"].values():
                if message.get("providerId") == provider_id:
                    if ranks[status] >= ranks.get(message.get("deliveryStatus"), -1):
                        message.update({"deliveryStatus": status, "deliveryUpdatedAt": self.now(s)})
                        # Store numeric diagnostics only; provider text can contain personal data.
                        message["deliveryErrorCodes"] = [e["code"] for e in (errors or []) if isinstance(e, dict) and type(e.get("code")) is int]
        self.store.atomic(apply)

    def advance(self, seconds):
        require(self.settings.development and type(seconds) is int and 0 < seconds <= 3600, "Invalid simulated time", 400)
        self.store.atomic(lambda s: s["meta"].update({"clock": {"offset": s["meta"].get("clock", {}).get("offset", 0) + seconds}}))
        return self.sweep()

    def transcript(self, address, channel):
        require(self.settings.development, "Not found", 404)
        key = self.contact_key("sim:" + address)
        def apply(s):
            c = s["contacts"].get(key, {})
            r = self._active(s, c, self.now(s))
            ordered = sorted(s["outbox"].items(), key=lambda item: (item[1]["createdAt"], item[1].get("sequence", 0)))
            return {"messages": [{"id": k, "text": o["text"], "at": o["createdAt"], "context": o["context"], "status": o["status"]} for k, o in ordered if o["contact"] == key and o["channel"] == channel and o["simulated"]][-40:], "active": bool(r), "serverNow": self.now(s)}
        return self.store.atomic(apply)
