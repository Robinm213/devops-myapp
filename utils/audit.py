# utils/audit.py
from datetime import datetime
import csv, os

LOG_PATH = os.path.join("data", "audit_log.csv")

def log(event: str, details: dict | None = None):
    os.makedirs("data", exist_ok=True)
    exists = os.path.exists(LOG_PATH)
    with open(LOG_PATH, "a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if not exists:
            w.writerow(["ts_iso", "event", "details"])
        w.writerow([datetime.utcnow().isoformat(), event, (details or {})])
