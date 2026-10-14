"""Read-only check of the user's ServiceNow requests against the items needed for onboarding.

Only issues GET requests; never creates or changes tickets.

  python check_tickets.py [--login jnovak] [--team login1,login2] [--show-all]

A request counts if it was requested for you OR opened by you, and, when --team / SERVICENOW_TEAM
(comma-separated logins of colleagues) is given, also if a colleague opened it for you or requested it
for themselves (e.g. a shared team ticket). Matches from colleagues are marked with who opened them.

Config: ../skills/perf-setup/tickets.json (required items + keywords).
Credentials (from .env or environment); with SSO none are needed if you are logged in to ServiceNow in your browser:
  (SSO) the session cookie is read from Edge/Chrome/Safari/Firefox, or set SERVICENOW_COOKIE=...
  SERVICENOW_URL=https://csasprod.service-now.com       (optional, this is the default)
  SERVICENOW_TOKEN=...                                  (Bearer/OAuth token)  or
  SERVICENOW_USER=... and SERVICENOW_PASSWORD=...       (Basic)
  SERVICENOW_LOGIN=...                                  (user_name of the requester; or use --login)
  SERVICENOW_TEAM=login1,login2                         (optional colleagues; or use --team)
Output per required item: FOUND (state) / MISSING. Exit 0 = all found, 2 = something missing, 1 = error.
"""
import argparse
import base64
import json
import re
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

import sync_wiki_pages as sw  # reuses truststore + .env loading

CONFIG = Path(__file__).resolve().parents[1] / "skills" / "perf-setup" / "tickets.json"


def _browser_cookie(base: str) -> str:
    """Read the live SSO session cookie of the ServiceNow host from a local browser."""
    host = base.split("//", 1)[-1].split("/")[0]
    try:
        import browser_cookie3  # type: ignore[import-untyped]
    except ImportError:
        return ""
    for name in ("edge", "chrome", "safari", "firefox", "brave"):
        try:
            jar = getattr(browser_cookie3, name)(domain_name=host)
        except Exception:
            continue
        cookie = "; ".join(f"{c.name}={c.value}" for c in jar)
        if cookie:
            return cookie
    return ""


def _user_token(base: str, cookie: str) -> str:
    """ServiceNow session auth also wants X-UserToken (g_ck), embedded in the home page."""
    req = urllib.request.Request(base + "/", headers={"Cookie": cookie})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            m = re.search(r"g_ck\s*=\s*['\"]([0-9a-fA-F]+)['\"]", r.read().decode("utf-8", "replace"))
            return m.group(1) if m else ""
    except Exception:
        return ""


def headers(base: str = "https://csasprod.service-now.com") -> dict[str, str]:
    sw._load_secrets_file()
    tok = os.environ.get("SERVICENOW_TOKEN", "").strip()
    if tok:
        return {"Authorization": f"Bearer {tok}", "Accept": "application/json"}
    u, p = os.environ.get("SERVICENOW_USER", ""), os.environ.get("SERVICENOW_PASSWORD", "")
    if u and p:
        raw = base64.b64encode(f"{u}:{p}".encode()).decode()
        return {"Authorization": f"Basic {raw}", "Accept": "application/json"}
    cookie = os.environ.get("SERVICENOW_COOKIE", "").strip() or _browser_cookie(base)
    if cookie:
        h = {"Cookie": cookie, "Accept": "application/json"}
        ck = _user_token(base, cookie)
        if ck:
            h["X-UserToken"] = ck
        return h
    print("ERROR: no ServiceNow credentials. Log in to ServiceNow in your browser (SSO) and re-run, "
          "or set SERVICENOW_TOKEN / SERVICENOW_COOKIE in .env", file=sys.stderr)
    raise SystemExit(1)


def get(base: str, path: str) -> list[dict]:
    req = urllib.request.Request(base + path, headers=headers(base))
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read().decode("utf-8")).get("result", [])
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"ServiceNow GET {path.split('?')[0]} -> {e.code} {e.reason}") from e
    except urllib.error.URLError as e:
        raise RuntimeError(f"ServiceNow network error: {e.reason}") from e


def who(i: dict, login: str) -> str:
    """Return ' [opened by X for Y]' when the request was not simply opened by the user for themselves."""
    rf, ob = i.get("request.requested_for"), i.get("request.opened_by")
    name = lambda v: v.get("display_value", "") if isinstance(v, dict) else (v or "")
    rf, ob = name(rf), name(ob)
    return f" [opened by {ob or '?'} for {rf or '?'}]" if ob and rf and ob != rf else ""


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--login")
    ap.add_argument("--team", help="comma-separated colleague logins")
    ap.add_argument("--show-all", action="store_true", help="also list all found requests")
    a = ap.parse_args()
    cfg = json.loads(CONFIG.read_text(encoding="utf-8"))
    sw._load_secrets_file()
    base = os.environ.get("SERVICENOW_URL", "https://csasprod.service-now.com").rstrip("/")
    login = a.login or os.environ.get("SERVICENOW_LOGIN", "")
    if not login:
        print("ERROR: provide --login or SERVICENOW_LOGIN (your ServiceNow user_name).", file=sys.stderr)
        return 1

    team = [t.strip() for t in (a.team or os.environ.get("SERVICENOW_TEAM", "")).split(",") if t.strip()]
    clauses = [f"request.requested_for.user_name={login}", f"request.opened_by.user_name={login}"]
    for t in team:
        clauses += [f"request.opened_by.user_name={t}", f"request.requested_for.user_name={t}"]
    query = "^OR".join(clauses) + "^ORDERBYDESCsys_created_on"
    path = ("/api/now/table/sc_req_item?sysparm_display_value=true&sysparm_limit=200"
            "&sysparm_fields=number,short_description,cat_item,state,stage,opened_at,"
            "request.requested_for,request.opened_by"
            f"&sysparm_query={urllib.parse.quote(query)}")
    try:
        items = get(base, path)
    except RuntimeError as exc:
        print(f"FAILED: {exc}", file=sys.stderr)
        return 1

    def text(i: dict) -> str:
        ci = i.get("cat_item")
        ci = ci.get("display_value", "") if isinstance(ci, dict) else (ci or "")
        return f"{i.get('short_description', '')} {ci}".lower()

    missing = 0
    for need in cfg["required"]:
        hits = [i for i in items if all(k.lower() in text(i) for k in need["keywords"])]
        if hits:
            h = hits[0]
            print(f"  FOUND    {need['name']}: {h['number']} - {h.get('state')} ({h.get('opened_at')})"
                  f"{who(h, login)}")
        else:
            print(f"  MISSING  {need['name']}  -> {need.get('how', '')}")
            missing += 1
    if a.show_all:
        print("\nAll your requests:")
        for i in items:
            print(f"  {i['number']}  {i.get('state')}  {i.get('short_description')}{who(i, login)}")
    return 2 if missing else 0


if __name__ == "__main__":
    raise SystemExit(main())
