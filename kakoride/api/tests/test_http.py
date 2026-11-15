import hashlib
import hmac
import json
from dataclasses import replace
import pytest
from fastapi.testclient import TestClient
from kakoride.api.app import create_app, WebhookOnly
from kakoride.api.config import Settings
from kakoride.api.store import SQLiteStore


@pytest.fixture
def client(tmp_path):
    cfg = Settings(database_path=str(tmp_path / "http.sqlite"), whatsapp_secret="fixture-secret", whatsapp_verify="fixture-verify", sms_secret="sms-fixture", sms_project="p1")
    return TestClient(create_app(cfg), raise_server_exceptions=True)


def login(client, profile="driver"):
    result = client.post("/dev/login", json={"profile": profile})
    assert result.status_code == 200
    return {"Authorization": "Bearer " + result.json()["token"]}


def test_auth_dashboard_simulator_and_expiry(client):
    assert client.get("/api/driver/routes").status_code == 401
    headers = login(client)
    assert client.get("/api/driver/routes", headers=headers).status_code == 200
    result = client.post("/dev/messages", headers=headers, json={"channel": "sms", "sender": "+260970000101", "text": "RIDE KAMWALA TOWN 20", "eventId": "http-event"})
    assert result.status_code == 200, result.text
    url = "/api/driver/demand?routeId=woodlands-town&currentStopId=woodlands"
    assert client.get(url, headers=headers).json()["passengers"] == 1
    assert client.get(url, headers=login(client, "locked")).status_code == 403
    assert client.post("/dev/clock", headers=headers, json={"seconds": 600}).status_code == 200
    assert client.get(url, headers=headers).json()["passengers"] == 0
    assert client.post("/api/auth/logout", headers=headers).status_code == 200
    assert client.get("/api/driver/routes", headers=headers).status_code == 401


def test_meta_signature_handshake_and_ignored_receipts(client):
    assert client.get("/webhooks/whatsapp?hub.mode=subscribe&hub.verify_token=fixture-verify&hub.challenge=123").text == "123"
    assert client.get("/webhooks/whatsapp?hub.mode=subscribe&hub.verify_token=wrong").status_code == 403
    raw = json.dumps({"object": "whatsapp_business_account", "entry": [{"changes": [{"value": {"statuses": [{"status": "delivered"}]}}]}]}).encode()
    assert client.post("/webhooks/whatsapp", content=raw).status_code == 403
    signature = "sha256=" + hmac.new(b"fixture-secret", raw, hashlib.sha256).hexdigest()
    result = client.post("/webhooks/whatsapp", content=raw, headers={"x-hub-signature-256": signature})
    assert result.status_code == 200 and result.json()["accepted"] == 0


def test_telerivet_form_e164_and_duplicate(client):
    body = {"secret": "sms-fixture", "event": "incoming_message", "id": "sms-1", "project_id": "p1", "from_number": "0970000101", "from_number_e164": "+260970000101", "content": "RIDE KAMWALA TOWN 20", "message_type": "sms"}
    assert client.post("/webhooks/sms/telerivet", data={**body, "secret": "bad"}).status_code == 403
    assert client.post("/webhooks/sms/telerivet", data=body).json()["duplicate"] is False
    assert client.post("/webhooks/sms/telerivet", data=body).json()["duplicate"] is True


def test_production_driver_role_and_no_simulator(tmp_path):
    cfg = Settings(environment="production", storage="firestore", project="test", contact_key="test-private-key" * 4)
    store = SQLiteStore(tmp_path / "prod-test.sqlite")
    app = create_app(cfg, store, verifier=lambda token: "unapproved")
    c = TestClient(app)
    assert c.post("/dev/login", json={"profile": "admin"}).status_code == 404
    assert c.post("/dev/clock", json={"seconds": 300}).status_code == 404
    assert c.get("/api/driver/routes", headers={"Authorization": "Bearer valid-test-token"}).status_code == 403
    assert c.post("/internal/jobs/sweep").status_code == 503


def test_request_bounds_and_no_dev_login_cross_origin(client):
    assert client.post("/dev/login", json={"profile": "admin"}, headers={"Origin": "https://evil.example"}).status_code == 403
    assert client.post("/webhooks/whatsapp", content=b"x" * 65537).status_code == 413
    headers = login(client)
    assert client.post("/api/admin/entitlements", headers=headers, json={"uid": "demo-driver", "routeId": "woodlands-town", "days": 30}).status_code == 403


def test_authenticated_meta_phone_less_sender(client):
    import time
    payload = {"object": "whatsapp_business_account", "entry": [{"changes": [{"value": {"messages": [{"id": "wa-bsuid-test", "from_user_id": "US.TEST123", "timestamp": str(int(time.time())), "type": "text", "text": {"body": "RIDE KAMWALA TOWN 20"}}]}}]}]}
    raw = json.dumps(payload).encode()
    signature = "sha256=" + hmac.new(b"fixture-secret", raw, hashlib.sha256).hexdigest()
    assert client.post("/webhooks/whatsapp", content=raw, headers={"x-hub-signature-256": signature}).json()["accepted"] == 1
    data = client.get("/api/driver/demand?routeId=woodlands-town&currentStopId=woodlands", headers=login(client)).json()
    assert data["passengers"] == 1 and "US.TEST123" not in json.dumps(data)


def test_public_tunnel_only_exposes_verified_webhook_routes(client):
    tunnel = TestClient(WebhookOnly(client.app))
    assert tunnel.post("/dev/login", json={"profile": "admin"}).status_code == 404
    assert tunnel.get("/api/driver/routes").status_code == 404
    assert tunnel.post("/internal/jobs/sweep", json={}).status_code == 404
    assert tunnel.get("/docs").status_code == 404
    assert tunnel.get("/webhooks/whatsapp?hub.mode=subscribe&hub.verify_token=fixture-verify&hub.challenge=123").text == "123"
    assert tunnel.post("/webhooks/whatsapp", json={}).status_code == 403
    assert tunnel.post("/webhooks/sms/telerivet", data={"secret": "wrong"}).status_code == 403
