import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    environment: str = "development"
    storage: str = "sqlite"
    database_path: str = str(Path(__file__).resolve().parent / ".data" / "development.sqlite")
    project: str = ""
    namespace: str = "kakoride"
    contact_key: str = "local-development-contact-key-not-for-production"
    origins: str = "http://127.0.0.1:5173,http://localhost:5173"
    whatsapp_secret: str = ""
    whatsapp_verify: str = ""
    whatsapp_token: str = ""
    whatsapp_number: str = ""
    graph_version: str = "v27.0"
    sms_secret: str = ""
    sms_token: str = ""
    sms_project: str = ""
    internal_audience: str = ""
    scheduler_email: str = ""
    tasks_queue: str = ""

    @property
    def development(self):
        return self.environment == "development" and not os.getenv("K_SERVICE")

    @classmethod
    def from_env(cls):
        defaults = cls()
        names = {"environment": "ENVIRONMENT", "storage": "STORAGE", "database_path": "LOCAL_DATABASE",
                 "project": "GOOGLE_CLOUD_PROJECT", "namespace": "FIRESTORE_NAMESPACE", "contact_key": "CONTACT_HMAC_KEY",
                 "origins": "WEB_ORIGINS", "whatsapp_secret": "WHATSAPP_APP_SECRET", "whatsapp_verify": "WHATSAPP_VERIFY_TOKEN",
                 "whatsapp_token": "WHATSAPP_ACCESS_TOKEN", "whatsapp_number": "WHATSAPP_PHONE_NUMBER_ID",
                 "graph_version": "WHATSAPP_GRAPH_VERSION", "sms_secret": "TELERIVET_WEBHOOK_SECRET", "sms_token": "TELERIVET_API_KEY",
                 "sms_project": "TELERIVET_PROJECT_ID", "internal_audience": "INTERNAL_JOB_AUDIENCE",
                 "scheduler_email": "JOB_SERVICE_ACCOUNT_EMAIL", "tasks_queue": "CLOUD_TASKS_QUEUE"}
        values = {k: os.getenv("KAKORIDE_" + v, getattr(defaults, k)) for k, v in names.items()}
        result = cls(**values)
        if result.storage not in ("sqlite", "firestore"):
            raise RuntimeError("KAKORIDE_STORAGE must be sqlite or firestore")
        if not result.development:
            if result.storage != "firestore" or not result.project or len(result.contact_key) < 32 or result.contact_key == defaults.contact_key:
                raise RuntimeError("Production requires Firestore, project and a private 32+ character contact HMAC key")
        return result
