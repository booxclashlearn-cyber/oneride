"""Local persistent job/outbox worker. Production uses authenticated Scheduler sweeps."""
import argparse
import time
from .config import Settings
from .engine import Engine
from .store import make_store
from .providers import dispatch
from .scheduling import schedule_pending


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--once", action="store_true")
    args = parser.parse_args()
    settings = Settings.from_env()
    engine = Engine(make_store(settings), settings)
    while True:
        try:
            result = {**engine.sweep(), **dispatch(engine), **schedule_pending(engine)}
            if args.once:
                print(result)
        except Exception:
            print("Worker sweep failed; data remains pending for retry.", flush=True)
            if args.once:
                raise
        if args.once:
            return
        time.sleep(5)


if __name__ == "__main__":
    main()
