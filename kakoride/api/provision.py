"""Trusted operator CLI: creates approved drivers/admins and manual route grants."""
import argparse
import firebase_admin
from firebase_admin import auth
from .config import Settings
from .store import make_store
from .catalog import ROUTES


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("email")
    parser.add_argument("--name", required=True)
    parser.add_argument("--role", choices=["driver", "admin"], default="driver")
    parser.add_argument("--route", choices=[r["id"] for r in ROUTES])
    parser.add_argument("--days", type=int, default=30)
    args = parser.parse_args()
    settings = Settings.from_env()
    if settings.storage != "firestore" or not settings.project:
        parser.error("Configure Firestore and Google project first")
    if not 1 <= args.days <= 365:
        parser.error("Days must be 1–365")
    firebase_admin.initialize_app(options={"projectId": settings.project})
    user = auth.get_user_by_email(args.email)
    import time
    def provision(s):
        s["drivers"][user.uid] = {"uid": user.uid, "name": args.name, "role": args.role, "approved": True}
        if args.route:
            s["entitlements"][user.uid + "_" + args.route] = {"uid": user.uid, "routeId": args.route, "status": "active", "expiresAt": int(time.time()) + args.days * 86400, "source": "trusted CLI"}
    make_store(settings).atomic(provision)
    print("Approved account and optional route grant saved.")


if __name__ == "__main__":
    main()
