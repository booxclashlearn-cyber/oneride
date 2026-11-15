"""Atomic private records. SQLite is local-only; Firestore is the production store.

The one-route pilot deliberately serializes bounded transactions behind a revision
record. It fails explicitly at the scan limit rather than returning partial totals.
"""
import copy
import json
import sqlite3
import random
import threading
import time
from pathlib import Path

TABLES = ("contacts", "demands", "conversations", "events", "outbox", "jobs", "drivers", "entitlements", "sessions", "meta")
MAX_RECORDS = 2000


def empty():
    return {name: {} for name in TABLES}


class SQLiteStore:
    def __init__(self, path):
        self.path = str(path)
        Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        with self.connection() as db:
            db.execute("CREATE TABLE IF NOT EXISTS state (id INTEGER PRIMARY KEY CHECK(id=1), payload TEXT NOT NULL)")
            db.execute("INSERT OR IGNORE INTO state VALUES(1,?)", (json.dumps(empty()),))

    def connection(self):
        return sqlite3.connect(self.path, timeout=30)

    def atomic(self, operation):
        with self.connection() as db:
            db.execute("BEGIN IMMEDIATE")
            state = json.loads(db.execute("SELECT payload FROM state WHERE id=1").fetchone()[0])
            result = operation(state)
            db.execute("UPDATE state SET payload=? WHERE id=1", (json.dumps(state, separators=(",", ":")),))
            return copy.deepcopy(result)


class FirestoreStore:
    def __init__(self, project, namespace):
        from google.cloud import firestore
        self.fs = firestore
        self.client = firestore.Client(project=project)
        self.root = self.client.collection("kakoridePrivate").document(namespace)
        # One Cloud Run worker should not compete with itself for the pilot's
        # global revision. Firestore remains authoritative across processes.
        self.lock = threading.RLock()

    def atomic(self, operation):
        @self.fs.transactional
        def commit(tx):
            guard = self.root.get(transaction=tx)
            state = empty()
            total = 0
            for table in TABLES:
                docs = list(self.root.collection(table).limit(MAX_RECORDS + 1).stream(transaction=tx))
                total += len(docs)
                if total > MAX_RECORDS:
                    raise RuntimeError("Pilot record limit exceeded; run retention/scale the repository before accepting more data")
                state[table] = {d.id: d.to_dict() for d in docs}
            before = copy.deepcopy(state)
            result = operation(state)
            changes = []
            for table in TABLES:
                for key in before[table].keys() | state[table].keys():
                    if before[table].get(key) != state[table].get(key):
                        changes.append((self.root.collection(table).document(key), state[table].get(key)))
            if len(changes) > 400:
                raise RuntimeError("Pilot transaction limit exceeded")
            if changes:
                tx.set(self.root, {"revision": (guard.to_dict() or {}).get("revision", 0) + 1})
                for ref, value in changes:
                    if value is None:
                        tx.delete(ref)
                    else:
                        tx.set(ref, value)
            return result
        from google.api_core.exceptions import Aborted
        with self.lock:
            for attempt in range(3):
                try:
                    return commit(self.client.transaction(max_attempts=5))
                except (Aborted, ValueError) as error:
                    if not isinstance(error, Aborted) and not isinstance(error.__cause__, Aborted):
                        raise
                    if attempt == 2:
                        raise
                    time.sleep(random.uniform(.05, .2) * (attempt + 1))


def make_store(settings):
    return FirestoreStore(settings.project, settings.namespace) if settings.storage == "firestore" else SQLiteStore(settings.database_path)
