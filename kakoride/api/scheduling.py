"""Cloud Tasks registration, reconciled from persisted jobs after partial failures."""
import json


def schedule_pending(engine):
    cfg = engine.settings
    if not cfg.tasks_queue:
        return {"tasksScheduled": 0}
    if not cfg.internal_audience or not cfg.scheduler_email:
        raise RuntimeError("Cloud Tasks requires internal audience and job service account")
    from google.cloud import tasks_v2
    from google.api_core.exceptions import AlreadyExists
    from google.protobuf.timestamp_pb2 import Timestamp
    client = tasks_v2.CloudTasksClient()
    def due_work(s):
        reminders = [("jobs", key, dict(job)) for key, job in s["jobs"].items() if job["status"] == "pending" and not job.get("scheduled")][:25]
        messages = [("outbox", key, dict(message)) for key, message in s["outbox"].items() if message["status"] == "pending" and not message["simulated"] and message.get("scheduledAttempt") != message["attempts"]][:25]
        return reminders + messages
    pending = engine.store.atomic(due_work)
    done = 0
    for table, key, job in pending:
        timestamp = Timestamp(seconds=job["dueAt"])
        task_id = "reminder-" + key if table == "jobs" else "outbox-" + key + "-" + str(job["attempts"])
        task = {"name": cfg.tasks_queue + "/tasks/" + task_id, "schedule_time": timestamp, "http_request": {"http_method": tasks_v2.HttpMethod.POST, "url": cfg.internal_audience.rstrip("/") + "/internal/jobs/sweep", "headers": {"Content-Type": "application/json"}, "body": json.dumps({}).encode(), "oidc_token": {"service_account_email": cfg.scheduler_email, "audience": cfg.internal_audience}}}
        try:
            client.create_task(parent=cfg.tasks_queue, task=task, timeout=5)
        except AlreadyExists:
            pass
        def mark(s):
            if key in s[table]:
                if table == "jobs":
                    s[table][key]["scheduled"] = True
                elif s[table][key]["attempts"] == job["attempts"]:
                    s[table][key]["scheduledAttempt"] = job["attempts"]
        engine.store.atomic(mark)
        done += 1
    return {"tasksScheduled": done}
