"""Submit REDiM group-membership requests via the MiLA REDiM API (for the holder of an API key).

Default is a DRY RUN that only prints the payloads. Nothing is sent without --submit AND a typed
confirmation. Only groups listed in access.json for the chosen environment can be requested, and
only the "add user to group" request type is supported.

Usage:
  python request_access.py --env test --account cen12345 --note "Onboarding to GEORGEPETE perf tests"
  python request_access.py --env test --account cen12345 --groups CSINT\\GeorgePete_Viewer --submit
  python request_access.py --env test --status 1234

.env: REDIM_API_KEY=<key from API Manager>, REDIM_REQUESTOR=<your PRIMARY account, e.g. cen58041>
Assumptions to verify with the IAM team: header name "web-api-key", that the requestor may file
requests for other accounts, that approval workflow matches the REDiM UI, and that these groups are
AppAccess groups (the API only covers those).
"""
import argparse
import json
import os
import sys
import urllib.error
import urllib.request
import uuid
from pathlib import Path

import sync_wiki_pages as sw  # truststore + .env loading

CONFIG = Path(__file__).resolve().parents[1] / "skills" / "perf-setup" / "access.json"
REQUEST_TYPE = "AddUserToPrimWinAppAccessAdGroupRequest"


def call(method: str, url: str, key: str, body: dict | None = None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method, headers={
        "web-api-key": key, "Content-Type": "application/json", "Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return r.status, r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")
    except urllib.error.URLError as e:
        raise SystemExit(f"Network error (VPN/bank network needed?): {e.reason}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--env", choices=["test", "prod"], required=True)
    ap.add_argument("--account", help="primary account of the person who needs the rights")
    ap.add_argument("--groups", nargs="*", help="subset of groups from access.json (default: all for the env)")
    ap.add_argument("--note", default="Onboarding to GEORGEPETE performance tests")
    ap.add_argument("--status", help="request id to look up")
    ap.add_argument("--submit", action="store_true", help="really send (asks for confirmation)")
    a = ap.parse_args()

    sw._load_secrets_file()
    cfg = json.loads(CONFIG.read_text(encoding="utf-8"))
    base = cfg["api"][a.env].rstrip("/")
    key = os.environ.get("REDIM_API_KEY", "").strip()
    requestor = os.environ.get("REDIM_REQUESTOR", "").strip()

    if a.status:
        if not key:
            raise SystemExit("Set REDIM_API_KEY in .env")
        code, text = call("GET", f"{base}/requests/{a.status}", key)
        print(code, text)
        return 0 if code == 200 else 1

    if not a.account:
        raise SystemExit("--account is required")
    allowed = cfg["groups"][a.env]
    chosen = a.groups or allowed
    bad = [g for g in chosen if g not in allowed]
    if bad:
        raise SystemExit(f"Not in access.json for {a.env}: {bad}")

    batch = uuid.uuid4().hex[:8]
    payloads = [{
        "requestor": requestor or "<REDIM_REQUESTOR>",
        "externalId": f"perf-setup-{batch}-{i}",
        "note": a.note,
        "requestType": REQUEST_TYPE,
        "adGroupName": g.split("\\")[-1],
        "accountName": a.account,
    } for i, g in enumerate(chosen, 1)]

    print(f"Target: {a.env.upper()}  {base}/requests")
    for p in payloads:
        print(json.dumps(p, ensure_ascii=False))
    if not a.submit:
        print("\nDRY RUN - nothing sent. Add --submit to send.")
        return 0
    if not key or not requestor:
        raise SystemExit("Set REDIM_API_KEY and REDIM_REQUESTOR in .env")
    if input(f"\nSend {len(payloads)} request(s) to {a.env.upper()} for {a.account}? Type 'yes': ").strip() != "yes":
        print("Aborted.")
        return 1
    rc = 0
    for p in payloads:
        code, text = call("POST", f"{base}/requests", key, p)
        print(f"{p['adGroupName']}: {code} {text}")
        rc |= code != 201
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
