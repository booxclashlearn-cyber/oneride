from dataclasses import replace
from types import SimpleNamespace
import sys
from fastapi.testclient import TestClient
from kakoride.api.config import Settings
from kakoride.api.store import SQLiteStore
from kakoride.api.engine import Engine
from kakoride.api.scheduling import schedule_pending
from kakoride.api.providers import Sender, dispatch
from kakoride.api.app import create_app


def test_tasks_register_receipts_reminders_and_retry_generations(tmp_path, monkeypatch):
    calls = []
    class Queue:
        def create_task(self, **kwargs):
            calls.append(kwargs)
    monkeypatch.setitem(sys.modules, "google.cloud.tasks_v2", SimpleNamespace(CloudTasksClient=Queue, HttpMethod=SimpleNamespace(POST=1)))
    cfg = Settings(database_path=str(tmp_path / "queue.sqlite"), tasks_queue="projects/demo/locations/test/queues/q", internal_audience="https://api.example.test", scheduler_email="jobs@example.test")
    engine = Engine(SQLiteStore(cfg.database_path), cfg, clock=lambda: 1800000000)
    engine.ingest("fixture", "incoming", "sms", "+260970000101", "RIDE KAMWALA TOWN 20")
    assert schedule_pending(engine)["tasksScheduled"] == 2
    assert any("/tasks/reminder-" in call["task"]["name"] for call in calls)
    assert any("/tasks/outbox-" in call["task"]["name"] for call in calls)
    assert all(call["task"]["http_request"]["oidc_token"]["audience"] == cfg.internal_audience for call in calls)
    assert schedule_pending(engine)["tasksScheduled"] == 0
    class BrokenSender:
        def send(self, address, message):
            raise RuntimeError("provider unavailable")
    dispatch(engine, BrokenSender())
    assert schedule_pending(engine)["tasksScheduled"] == 1
    assert calls[-1]["task"]["name"].endswith("-1")


def test_internal_jobs_require_verified_service_identity(tmp_path, monkeypatch):
    cfg = Settings(environment="production", storage="firestore", project="demo", contact_key="private-test-key" * 4, internal_audience="https://api.example.test", scheduler_email="jobs@example.test")
    app = create_app(cfg, SQLiteStore(tmp_path / "auth.sqlite"))
    client = TestClient(app)
    from google.oauth2 import id_token
    def bad(*args):
        raise ValueError("invalid signature")
    monkeypatch.setattr(id_token, "verify_oauth2_token", bad)
    assert client.post("/internal/jobs/sweep").status_code == 401
    monkeypatch.setattr(id_token, "verify_oauth2_token", lambda *args: {"email": "driver@example.test", "email_verified": True})
    assert client.post("/internal/jobs/sweep", headers={"Authorization": "Bearer fixture"}).status_code == 403
    def verified(token, request, audience):
        assert audience == cfg.internal_audience
        return {"email": cfg.scheduler_email, "email_verified": True}
    monkeypatch.setattr(id_token, "verify_oauth2_token", verified)
    assert client.post("/internal/jobs/sweep", headers={"Authorization": "Bearer fixture"}).status_code == 200


def test_provider_payloads_and_no_phone_whatsapp_address(monkeypatch):
    calls = []
    class Response:
        def raise_for_status(self):
            pass
        def json(self):
            return {"messages": [{"id": "wa-accepted"}], "id": "sms-accepted"}
    def post(url, **kwargs):
        calls.append((url, kwargs))
        return Response()
    monkeypatch.setattr("kakoride.api.providers.httpx.post", post)
    cfg = Settings(whatsapp_token="fixture", whatsapp_number="number", sms_token="sms-fixture", sms_project="project")
    sender = Sender(cfg)
    assert sender.send("wa:US.SYNTHETIC", {"channel": "whatsapp", "text": "Have you boarded?", "context": {"request": "request123", "version": 2}}) == "wa-accepted"
    payload = calls[-1][1]["json"]
    assert payload["recipient"] == "US.SYNTHETIC" and "to" not in payload
    assert payload["interactive"]["action"]["buttons"][1]["reply"]["id"] == "reply:request123:2:2"
    assert sender.send("+260970000101", {"channel": "sms", "text": "Fixture text", "context": None}) == "sms-accepted"
    assert calls[-1][0].endswith("/v1/projects/project/messages/send")
    assert calls[-1][1]["data"]["to_number"] == "+260970000101"
