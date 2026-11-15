"""Integration checks against an explicitly started local Firestore emulator only."""
import os
import uuid
from concurrent.futures import ThreadPoolExecutor
import pytest
from kakoride.api.config import Settings
from kakoride.api.engine import Engine, DomainError
from kakoride.api.store import FirestoreStore


@pytest.mark.skipif(not os.getenv("FIRESTORE_EMULATOR_HOST"), reason="Start a local Firestore emulator to exercise real transactions")
def test_firestore_atomic_roundtrip_restart_and_duplicate_intake():
    require_host = os.environ["FIRESTORE_EMULATOR_HOST"]
    assert require_host.startswith(("127.0.0.1:", "localhost:")), "Tests must never connect to a live Firestore project"
    namespace = "test-" + uuid.uuid4().hex
    cfg = Settings(storage="firestore", project="demo-kakoride", namespace=namespace)
    engine = Engine(FirestoreStore(cfg.project, namespace), cfg, clock=lambda: 1800000000)
    def intake(_):
        return engine.ingest("fixture", "same-event", "sms", "+260970000101", "RIDE KAMWALA TOWN 20", simulated=True)
    with ThreadPoolExecutor(max_workers=3) as pool:
        results = list(pool.map(intake, range(3)))
    assert sum(not r["duplicate"] for r in results) == 1
    restored = Engine(FirestoreStore(cfg.project, namespace), cfg, clock=lambda: 1800000000)
    assert restored.demand("demo-driver", "woodlands-town", "woodlands")["passengers"] == 1
    with pytest.raises(DomainError):
        restored.demand("demo-locked", "woodlands-town", "woodlands")
    restored.advance(300)
    assert restored.sweep()["remindersQueued"] == 0
    restored.advance(300)
    assert restored.demand("demo-driver", "woodlands-town", "woodlands")["passengers"] == 0


@pytest.mark.skipif(not os.getenv("FIRESTORE_EMULATOR_HOST"), reason="Start the rules-enabled local emulator")
def test_browser_cannot_read_private_firestore_documents():
    import httpx
    host = os.environ["FIRESTORE_EMULATOR_HOST"]
    assert host.startswith(("127.0.0.1:", "localhost:"))
    url = f"http://{host}/v1/projects/demo-kakoride/databases/(default)/documents/kakoridePrivate/forbidden/contacts"
    response = httpx.get(url, timeout=10)
    assert response.status_code in (401, 403), response.text
