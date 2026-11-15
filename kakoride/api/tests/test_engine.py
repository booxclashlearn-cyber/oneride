import json
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
import pytest
from kakoride.api.config import Settings
from kakoride.api.engine import Engine, DomainError
from kakoride.api.store import SQLiteStore
from kakoride.api.providers import dispatch


@pytest.fixture
def engine(tmp_path):
    cfg = Settings(database_path=str(tmp_path / "test.sqlite"))
    return Engine(SQLiteStore(cfg.database_path), cfg, clock=lambda: 1800000000)


def message(e, text, number="+260970000101", channel="sms", event=None):
    import uuid
    return e.ingest("test", event or uuid.uuid4().hex, channel, number, text, simulated=True)


def snapshot(e, route="woodlands-town", station="woodlands"):
    return e.demand("demo-driver", route, station)


def state(e):
    return e.store.atomic(lambda s: s)


def request(e, number="+260970000101", channel="sms"):
    message(e, "RIDE KAMWALA TOWN 20 2", number, channel)
    return next(r for r in state(e)["demands"].values() if r["contact"] == e.contact_key("sim:" + number))


def test_aggregation_direction_station_and_privacy(engine):
    request(engine)
    message(engine, "RIDE CHILENJE TOWN 25", "+260970000102")
    data = snapshot(engine)
    assert (data["passengers"], data["waitingStops"], data["offeredMinor"]) == (3, 2, 6500)
    assert snapshot(engine, station="chilenje")["passengers"] == 2
    assert snapshot(engine, station="kamwala")["passengers"] == 0
    assert snapshot(engine, route="town-woodlands", station="town")["passengers"] == 0
    encoded = json.dumps(data)
    for forbidden in ["+260", "contact", "request", "address", "sender", "message"]:
        assert forbidden not in encoded
    for private_request_id in state(engine)["demands"]:
        assert private_request_id not in encoded


def test_duplicate_provider_event_and_cross_channel_phone(engine):
    message(engine, "RIDE KAMWALA TOWN 20", event="same")
    assert message(engine, "RIDE KAMWALA TOWN 20", event="same")["duplicate"]
    message(engine, "RIDE KAMWALA TOWN 50 4", channel="whatsapp")
    assert snapshot(engine)["passengers"] == 1
    assert snapshot(engine)["offeredMinor"] == 2000
    assert len(state(engine)["demands"]) == 1


def test_concurrent_duplicate_intake_is_atomic(engine):
    with ThreadPoolExecutor(max_workers=6) as pool:
        results = list(pool.map(lambda _: message(engine, "RIDE KAMWALA TOWN 20", event="concurrent"), range(6)))
    assert sum(not r["duplicate"] for r in results) == 1
    assert snapshot(engine)["passengers"] == 1


def test_guided_whatsapp_conversation(engine):
    for text in ["Hi", "2", "1", "K20"]:
        message(engine, text, channel="whatsapp")
    assert snapshot(engine)["passengers"] == 1
    assert "Request active!" in engine.transcript("+260970000101", "whatsapp")["messages"][-1]["text"]


def test_invalid_route_and_values_do_not_create_demand(engine):
    for text in ["RIDE TOWN TOWN 20", "RIDE UNKNOWN TOWN 20", "RIDE KAMWALA TOWN 0", "RIDE KAMWALA TOWN 20 15", "RIDE KAMWALA TOWN 2.5"]:
        message(engine, text)
    assert snapshot(engine)["passengers"] == 0


def test_five_minute_reminder_silent_expiry_independent_of_worker(engine):
    r = request(engine)
    assert r["nextReminderAt"] - r["createdAt"] == 300
    assert engine.advance(300)["remindersQueued"] == 1
    assert engine.sweep()["remindersQueued"] == 0
    assert snapshot(engine)["passengers"] == 2
    # Advance persisted clock without calling sweep. Read-time expiry still excludes demand.
    engine.store.atomic(lambda s: s["meta"].update({"clock": {"offset": 600}}))
    assert snapshot(engine)["passengers"] == 0
    assert state(engine)["demands"][r["id"]]["status"] == "active"


def test_sms_requires_code_and_old_replies_cannot_extend(engine):
    r = request(engine)
    engine.advance(300)
    message(engine, "2")
    assert state(engine)["demands"][r["id"]]["version"] == 1
    code = r["id"][:6].upper() + "1"
    message(engine, "2 " + code, event="renew")
    new = state(engine)["demands"][r["id"]]
    assert new["version"] == 2 and new["expiresAt"] == r["expiresAt"] + 300
    assert message(engine, "2 " + code, event="renew")["duplicate"]
    engine.advance(300)
    message(engine, "1 " + code)
    assert snapshot(engine)["passengers"] == 2
    message(engine, "1 " + r["id"][:6].upper() + "2")
    assert snapshot(engine)["passengers"] == 0


def test_whatsapp_buttons_are_owner_and_generation_bound(engine):
    r = request(engine, channel="whatsapp")
    engine.advance(300)
    button = f"reply:{r['id']}:1:1"
    message(engine, button, "+260970000102", "whatsapp")
    assert snapshot(engine)["passengers"] == 2
    message(engine, button, channel="whatsapp")
    assert snapshot(engine)["passengers"] == 0
    message(engine, "RIDE KAMWALA TOWN 20", channel="whatsapp")
    message(engine, button, channel="whatsapp")
    assert snapshot(engine)["passengers"] == 1


def test_stop_cancels_jobs_and_pending_reminders(engine):
    request(engine)
    engine.advance(300)
    message(engine, "STOP")
    dispatch(engine)
    assert snapshot(engine)["passengers"] == 0
    reminders = [m for m in state(engine)["outbox"].values() if m["context"]]
    assert all(m["status"] == "cancelled" for m in reminders)
    message(engine, "RIDE KAMWALA TOWN 20")
    assert snapshot(engine)["passengers"] == 0
    message(engine, "START")
    message(engine, "RIDE KAMWALA TOWN 20")
    assert snapshot(engine)["passengers"] == 1


def test_entitlements_and_manual_admin_grants(engine):
    with pytest.raises(DomainError, match="subscription"):
        engine.demand("demo-locked", "woodlands-town", "woodlands")
    with pytest.raises(DomainError, match="Administrator"):
        engine.grant("demo-driver", "demo-locked", "woodlands-town", 30)
    engine.grant("demo-admin", "demo-locked", "woodlands-town", 1)
    assert engine.demand("demo-locked", "woodlands-town", "woodlands")["passengers"] == 0
    engine.store.atomic(lambda s: s["meta"].update({"clock": {"offset": 86401}}))
    with pytest.raises(DomainError, match="subscription"):
        engine.demand("demo-locked", "woodlands-town", "woodlands")


def test_persistence_restart_and_outbox_failure(engine):
    # Real-adapter test uses fake sender, so no external message is sent.
    engine.ingest("test", "real-fixture", "sms", "+260970000104", "RIDE KAMWALA TOWN 20")
    class Broken:
        def send(self, address, message):
            raise RuntimeError("PRIVATE provider exception")
    assert dispatch(engine, Broken())["failed"] == 1
    assert "PRIVATE" not in json.dumps(state(engine))
    restored = Engine(SQLiteStore(engine.settings.database_path), engine.settings, clock=engine.clock)
    assert snapshot(restored)["passengers"] == 1
    restored.advance(300)
    assert any(m["context"] for m in state(restored)["outbox"].values())


def test_production_has_no_local_simulator(engine):
    cfg = replace(engine.settings, environment="production", storage="firestore", project="test", contact_key="x" * 40)
    prod = Engine(engine.store, cfg, clock=engine.clock)
    with pytest.raises(DomainError):
        prod.login_demo("driver")
    with pytest.raises(DomainError):
        prod.ingest("sim", "x", "sms", "+260970000101", "Hi", simulated=True)


def test_reordered_real_events_do_not_recreate_closed_demand(engine):
    now = int(engine.clock())
    engine.ingest("provider", "new-request", "sms", "+260970000109", "RIDE KAMWALA TOWN 20", event_time=now)
    engine.ingest("provider", "cancel", "sms", "+260970000109", "CANCEL", event_time=now + 1)
    result = engine.ingest("provider", "old-retry", "sms", "+260970000109", "RIDE KAMWALA TOWN 20", event_time=now - 1)
    assert result["ignored"] == "reordered_event"
    assert snapshot(engine)["passengers"] == 0


def test_provider_acceptance_is_separate_from_delivery_and_stop_blocks_old_receipts(engine):
    engine.ingest("provider", "first", "sms", "+260970000108", "RIDE KAMWALA TOWN 20")
    engine.ingest("provider", "stop", "sms", "+260970000108", "STOP")
    sent = []
    class FakeSender:
        def send(self, address, message):
            sent.append(message["text"])
            return "accepted-message-id"
    assert dispatch(engine, FakeSender())["sent"] == 1
    assert len(sent) == 1 and "Automated messages stopped" in sent[0]
    engine.delivery("accepted-message-id", "delivered")
    engine.delivery("accepted-message-id", "sent")
    record = next(m for m in state(engine)["outbox"].values() if m.get("providerId") == "accepted-message-id")
    assert record["status"] == "sent" and record["deliveryStatus"] == "delivered"
