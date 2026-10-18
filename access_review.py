"""Access review: who has which role, and what looks wrong.

Flags:
  - DISABLED_WITH_ACCESS : disabled account that still holds a role
  - MULTIPLE_ROLES       : user holds more than one department role (privilege creep)
  - NO_ROLE              : enabled account with no department role
Writes access_review.csv.
"""
import csv

import common as c


def main():
    users = c.api("GET", f"/{c.REALM}/users", params={"max": 1000})
    rows = []
    for u in users:
        mappings = c.api("GET", f"/{c.REALM}/users/{u['id']}/role-mappings/realm")
        roles = sorted(r["name"] for r in mappings if r["name"] in c.DEPT_ROLES.values())
        flags = []
        if not u.get("enabled") and roles:
            flags.append("DISABLED_WITH_ACCESS")
        if len(roles) > 1:
            flags.append("MULTIPLE_ROLES")
        if u.get("enabled") and not roles:
            flags.append("NO_ROLE")
        rows.append([u["username"], u.get("enabled"), ";".join(roles), ";".join(flags) or "OK"])
    with open("access_review.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["username", "enabled", "roles", "finding"])
        w.writerows(rows)
    issues = [r for r in rows if r[3] != "OK"]
    print(f"Reviewed {len(rows)} accounts, {len(issues)} findings. See access_review.csv")


if __name__ == "__main__":
    main()
