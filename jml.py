"""Joiner / Mover / Leaver automation for a Keycloak realm.

Usage:
  python jml.py setup                     create realm + roles
  python jml.py joiners users.csv         create users and assign department role
  python jml.py mover asmith HR           move a user to a new department
  python jml.py leaver bkhan              disable user, kill sessions, remove roles
"""
import csv
import sys

import requests

import common as c


def setup():
    try:
        c.api("POST", "", json={"realm": c.REALM, "enabled": True, "eventsEnabled": True})
        c.audit("REALM_CREATED", "-", c.REALM)
    except requests.HTTPError as e:
        if e.response.status_code != 409:
            raise
        print("Realm already exists")
    for role in c.DEPT_ROLES.values():
        try:
            c.api("POST", f"/{c.REALM}/roles", json={"name": role})
            c.audit("ROLE_CREATED", "-", role)
        except requests.HTTPError as e:
            if e.response.status_code != 409:
                raise


def joiners(path):
    with open(path, newline="") as f:
        for row in csv.DictReader(f):
            if c.find_user(row["username"]):
                print(f"Skip {row['username']}: already exists")
                continue
            role_name = c.DEPT_ROLES.get(row["department"])
            if not role_name:
                print(f"Skip {row['username']}: unknown department {row['department']}")
                continue
            c.api("POST", f"/{c.REALM}/users", json={
                "username": row["username"],
                "firstName": row["first_name"],
                "lastName": row["last_name"],
                "email": row["email"],
                "enabled": True,
                "requiredActions": ["CONFIGURE_TOTP", "UPDATE_PASSWORD"],
                "credentials": [{"type": "password", "value": "ChangeMe!123", "temporary": True}],
            })
            user = c.find_user(row["username"])
            c.api("POST", f"/{c.REALM}/users/{user['id']}/role-mappings/realm",
                  json=[c.get_role(role_name)])
            c.audit("JOINER", row["username"], f"dept={row['department']} role={role_name}")


def mover(username, new_dept):
    user = c.find_user(username)
    if not user:
        sys.exit(f"No such user: {username}")
    new_role = c.DEPT_ROLES.get(new_dept)
    if not new_role:
        sys.exit(f"Unknown department: {new_dept}")
    current = c.api("GET", f"/{c.REALM}/users/{user['id']}/role-mappings/realm")
    old = [r for r in current if r["name"] in c.DEPT_ROLES.values()]
    if old:
        c.api("DELETE", f"/{c.REALM}/users/{user['id']}/role-mappings/realm", json=old)
    c.api("POST", f"/{c.REALM}/users/{user['id']}/role-mappings/realm",
          json=[c.get_role(new_role)])
    c.audit("MOVER", username, f"removed={[r['name'] for r in old]} added={new_role}")


def leaver(username):
    user = c.find_user(username)
    if not user:
        sys.exit(f"No such user: {username}")
    current = c.api("GET", f"/{c.REALM}/users/{user['id']}/role-mappings/realm")
    old = [r for r in current if r["name"] in c.DEPT_ROLES.values()]
    c.api("PUT", f"/{c.REALM}/users/{user['id']}", json={**user, "enabled": False})
    c.api("POST", f"/{c.REALM}/users/{user['id']}/logout")
    if old:
        c.api("DELETE", f"/{c.REALM}/users/{user['id']}/role-mappings/realm", json=old)
    c.audit("LEAVER", username, f"disabled, sessions ended, removed={[r['name'] for r in old]}")


if __name__ == "__main__":
    args = sys.argv[1:]
    if args[:1] == ["setup"]:
        setup()
    elif args[:1] == ["joiners"] and len(args) == 2:
        joiners(args[1])
    elif args[:1] == ["mover"] and len(args) == 3:
        mover(args[1], args[2])
    elif args[:1] == ["leaver"] and len(args) == 2:
        leaver(args[1])
    else:
        print(__doc__)
