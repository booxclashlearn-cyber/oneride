import hashlib
import hmac
import json
import os
import secrets
from contextlib import asynccontextmanager
from urllib.parse import parse_qs
from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, PlainTextResponse
from pydantic import BaseModel, Field, ConfigDict
from starlette.concurrency import run_in_threadpool
from .config import Settings
from .engine import DomainError, Engine, require
from .store import make_store
from .providers import dispatch
from .scheduling import schedule_pending
from .catalog import ROUTES


class DemoLogin(BaseModel):
    profile: str = "driver"


class Message(BaseModel):
    model_config = ConfigDict(extra="forbid")
    channel: str
    sender: str = Field(min_length=7, max_length=160)
    text: str = Field(min_length=1, max_length=500)
    eventId: str = Field(min_length=1, max_length=250)


class Advance(BaseModel):
    seconds: int = Field(strict=True, gt=0, le=3600)


class Grant(BaseModel):
    uid: str = Field(min_length=1, max_length=128)
    routeId: str
    days: int = Field(default=30, strict=True, ge=1, le=365)
    active: bool = True


def create_app(settings=None, store=None, verifier=None):
    cfg = settings or Settings.from_env()
    if not cfg.development and cfg.storage != "firestore":
        raise RuntimeError("Local storage is forbidden in production")
    engine = Engine(store or make_store(cfg), cfg)
    def kick_outbox():
        if cfg.tasks_queue:
            try:
                schedule_pending(engine)
            except Exception:
                # The intake is already durable. The authenticated periodic
                # sweep reconciles unscheduled work after this best-effort kick.
                engine.store.atomic(lambda s: s["meta"].update({"scheduling": {"retryNeeded": True}}))
    @asynccontextmanager
    async def lifespan(app):
        yield
    api = FastAPI(title="KaKoRide demand API", version="0.3.0", lifespan=lifespan, docs_url="/docs" if cfg.development else None, redoc_url=None)
    api.state.engine, api.state.settings = engine, cfg
    api.add_middleware(CORSMiddleware, allow_origins=[o.strip() for o in cfg.origins.split(",")], allow_methods=["GET", "POST"], allow_headers=["Authorization", "Content-Type"])

    @api.middleware("http")
    async def bounded(request, call_next):
        if request.method == "POST":
            total, chunks = 0, []
            async for chunk in request.stream():
                total += len(chunk)
                if total > 65536:
                    return JSONResponse({"error": "Message too large"}, status_code=413)
                chunks.append(chunk)
            request._body = b"".join(chunks)
        response = await call_next(request)
        response.headers["Cache-Control"] = "no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"
        return response

    @api.exception_handler(DomainError)
    async def domain_error(request, error):
        return JSONResponse({"error": error.message}, status_code=error.status)

    @api.exception_handler(Exception)
    async def private_error(request, error):
        return JSONResponse({"error": "Service unavailable. Try again shortly."}, status_code=503)

    def identity(request: Request):
        token = request.headers.get("authorization", "")
        require(token.startswith("Bearer ") and len(token) < 5000, "Sign in to continue", 401)
        token = token[7:]
        if cfg.development:
            return engine.demo_identity(token)
        try:
            if verifier:
                return verifier(token)
            import firebase_admin
            from firebase_admin import auth
            if not firebase_admin._apps:
                firebase_admin.initialize_app(options={"projectId": cfg.project})
            return auth.verify_id_token(token, check_revoked=True)["uid"]
        except Exception:
            raise DomainError("Sign in again", 401)

    def admin(uid=Depends(identity)):
        require(engine.driver(uid)["profile"]["role"] == "admin", "Administrator required", 403)
        return uid

    @api.get("/livez")
    @api.get("/healthz")
    def health():
        return {"status": "ok"}

    @api.get("/readyz")
    def ready():
        engine.store.atomic(lambda s: True)
        return {"status": "ready"}

    @api.get("/api/config")
    def config():
        return {"development": cfg.development, "simulatorEnabled": cfg.development, "storage": cfg.storage, "demoRoutes": any(r.get("demo", True) for r in ROUTES)}

    @api.get("/api/driver/routes")
    @api.get("/api/driver/access")
    def routes(uid=Depends(identity)):
        return engine.driver(uid)

    @api.get("/api/driver/demand")
    def demand(routeId: str, currentStopId: str, uid=Depends(identity)):
        return engine.demand(uid, routeId, currentStopId)

    @api.post("/api/auth/logout")
    def logout(request: Request, uid=Depends(identity)):
        if cfg.development:
            hashed = hashlib.sha256(request.headers["authorization"][7:].encode()).hexdigest()
            engine.store.atomic(lambda s: s["sessions"].pop(hashed, None))
        return {"ok": True}

    @api.post("/api/admin/entitlements")
    def grant(body: Grant, uid=Depends(admin)):
        return engine.grant(uid, body.uid, body.routeId, body.days, body.active)

    @api.get("/api/admin/health")
    def operational(uid=Depends(admin)):
        def summary(s):
            return {"outbox": {status: sum(m["status"] == status for m in s["outbox"].values()) for status in ("pending", "sending", "sent", "simulated", "failed")}, "delivery": {status: sum(m.get("deliveryStatus") == status for m in s["outbox"].values()) for status in ("delivered", "read", "failed", "not_delivered")}, "pendingJobs": sum(j["status"] == "pending" for j in s["jobs"].values()), "serverNow": engine.now(s)}
        return engine.store.atomic(summary)

    @api.get("/webhooks/whatsapp", response_class=PlainTextResponse)
    def handshake(request: Request):
        q = request.query_params
        require(bool(cfg.whatsapp_verify) and q.get("hub.mode") == "subscribe" and secrets.compare_digest(q.get("hub.verify_token", ""), cfg.whatsapp_verify), "Webhook verification failed", 403)
        return q.get("hub.challenge", "")

    @api.post("/webhooks/whatsapp")
    async def whatsapp(request: Request):
        raw = await request.body()
        expected = "sha256=" + hmac.new(cfg.whatsapp_secret.encode(), raw, hashlib.sha256).hexdigest()
        require(bool(cfg.whatsapp_secret) and secrets.compare_digest(request.headers.get("x-hub-signature-256", ""), expected), "Invalid webhook signature", 403)
        try:
            payload = json.loads(raw)
            require(isinstance(payload, dict), "Invalid webhook payload")
            require(payload.get("object") == "whatsapp_business_account", "Invalid webhook object")
            accepted = 0
            for entry in payload.get("entry", []):
                for change in entry.get("changes", []):
                    value = change.get("value", {})
                    if cfg.whatsapp_number:
                        require(value.get("metadata", {}).get("phone_number_id") == cfg.whatsapp_number, "Wrong WhatsApp phone number", 403)
                    for receipt in value.get("statuses", []):
                        engine.delivery(receipt.get("id"), receipt.get("status"), receipt.get("errors", []))
                    for message in value.get("messages", []):
                        sender = message.get("from")
                        sender = "+" + sender.lstrip("+") if sender else "wa:" + message.get("from_user_id", "")
                        text = message.get("text", {}).get("body") if message.get("type") == "text" else None
                        if message.get("type") == "interactive":
                            text = message.get("interactive", {}).get("button_reply", {}).get("id")
                        if text:
                            await run_in_threadpool(engine.ingest, "meta", message["id"], "whatsapp", sender, text, event_time=int(message["timestamp"]))
                            accepted += 1
            await run_in_threadpool(kick_outbox)
            return {"accepted": accepted}
        except (KeyError, ValueError, TypeError):
            raise DomainError("Invalid webhook payload")

    @api.post("/webhooks/sms/telerivet")
    async def telerivet(request: Request):
        raw = (await request.body()).decode("utf-8", errors="strict")
        try:
            if "application/json" in request.headers.get("content-type", ""):
                body = json.loads(raw)
            else:
                body = {k: v[0] for k, v in parse_qs(raw).items()}
            require(isinstance(body, dict), "Invalid SMS payload")
            require(bool(cfg.sms_secret) and secrets.compare_digest(str(body.get("secret", "")), cfg.sms_secret), "Invalid SMS webhook secret", 403)
            if body.get("event") == "send_status":
                engine.delivery(body.get("id"), body.get("status"))
                return {"accepted": True, "receipt": True}
            if body.get("event") != "incoming_message" or body.get("message_type", "sms") != "sms":
                return {"accepted": False, "ignored": True}
            if cfg.sms_project:
                require(body.get("project_id") == cfg.sms_project, "Wrong SMS project", 403)
            event_time = int(body["time_created"]) if body.get("time_created") else None
            result = await run_in_threadpool(engine.ingest, "telerivet", body["id"], "sms", body.get("from_number_e164") or body["from_number"], body["content"], event_time=event_time)
            await run_in_threadpool(kick_outbox)
            return result
        except (KeyError, ValueError, TypeError):
            raise DomainError("Invalid SMS payload")

    @api.post("/internal/jobs/sweep")
    def sweep(request: Request):
        require(bool(cfg.internal_audience and cfg.scheduler_email), "Internal jobs are not configured", 503)
        try:
            from google.oauth2 import id_token
            from google.auth.transport import requests
            token = request.headers.get("authorization", "").removeprefix("Bearer ")
            claims = id_token.verify_oauth2_token(token, requests.Request(), cfg.internal_audience)
            require(claims.get("email") == cfg.scheduler_email and claims.get("email_verified") is True, "Job service account denied", 403)
        except DomainError:
            raise
        except Exception:
            raise DomainError("Invalid service identity", 401)
        return {**engine.sweep(), **dispatch(engine), **schedule_pending(engine)}

    if cfg.development:
        @api.post("/dev/login")
        def demo_login(body: DemoLogin, request: Request):
            # This capability only exists on the loopback development server, never Cloud Run.
            origin = request.headers.get("origin")
            require(not origin or origin in cfg.origins.split(","), "Origin is not allowed", 403)
            return engine.login_demo(body.profile)

        @api.post("/dev/messages")
        def dev_message(body: Message, uid=Depends(identity)):
            engine.driver(uid)
            result = engine.ingest("simulator", body.eventId, body.channel, body.sender, body.text, simulated=True)
            dispatch(engine)
            return {**result, **engine.transcript(body.sender, body.channel)}

        @api.get("/dev/messages")
        def dev_transcript(sender: str, channel: str, uid=Depends(identity)):
            engine.driver(uid)
            return engine.transcript(sender, channel)

        @api.post("/dev/clock")
        def advance(body: Advance, uid=Depends(identity)):
            engine.driver(uid)
            result = engine.advance(body.seconds)
            dispatch(engine)
            return result

    return api


app = create_app()


class WebhookOnly:
    """Public-tunnel entry point: never expose development login/admin endpoints."""
    def __init__(self, application):
        self.application = application

    async def __call__(self, scope, receive, send):
        if scope["type"] == "lifespan":
            return await self.application(scope, receive, send)
        allowed = {("GET", "/webhooks/whatsapp"), ("POST", "/webhooks/whatsapp"), ("POST", "/webhooks/sms/telerivet")}
        if scope["type"] == "http" and (scope["method"], scope["path"]) in allowed:
            return await self.application(scope, receive, send)
        if scope["type"] == "websocket":
            return await send({"type": "websocket.close", "code": 1008})
        return await JSONResponse({"error": "Not found"}, status_code=404)(scope, receive, send)


webhook_app = WebhookOnly(app)
