"""Shared helpers: Keycloak admin API access and audit logging."""
import csv
import os
from datetime import datetime, timezone

import requests

BASE = os.getenv("KC_URL", "http://localhost:8080")
ADMIN_USER = os.getenv("KC_ADMIN_USER", "admin")
ADMIN_PASS = os.getenv("KC_ADMIN_PASS", "admin")
REALM = os.getenv("KC_REALM", "demo-corp")

# Department -> realm role (simple role-based access control model)
DEPT_ROLES = {
    "Finance": "finance-user",
    "IT-Support": "it-support",
    "HR": "hr-user",
    "Security": "security-analyst",
}

AUDIT_FILE = "audit_log.csv"


def token():
    r = requests.post(
        f"{BASE}/realms/master/protocol/openid-connect/token",
        data={
            "client_id": "admin-cli",
            "grant_type": "password",
            "username": ADMIN_USER,
            "password": ADMIN_PASS,
        },
        timeout=15,
    )
    r.raise_for_status()
    return r.json()["access_token"]


def api(method, path, **kwargs):
    """Call the Keycloak admin API. Path is relative to /admin/realms."""
    headers = {"Authorization": f"Bearer {token()}"}
    r = requests.request(
        method, f"{BASE}/admin/realms{path}", headers=headers, timeout=15, **kwargs
    )
    r.raise_for_status()
    return r.json() if r.text else None


def audit(action, username, detail=""):
    """Append one line to the audit log (who, what, when)."""
    new = not os.path.exists(AUDIT_FILE)
    with open(AUDIT_FILE, "a", newline="") as f:
        w = csv.writer(f)
        if new:
            w.writerow(["timestamp_utc", "action", "username", "detail"])
        w.writerow([datetime.now(timezone.utc).isoformat(), action, username, detail])
    print(f"[{action}] {username} {detail}")


def find_user(username):
    users = api("GET", f"/{REALM}/users", params={"username": username, "exact": "true"})
    return users[0] if users else None


def get_role(name):
    return api("GET", f"/{REALM}/roles/{name}")
