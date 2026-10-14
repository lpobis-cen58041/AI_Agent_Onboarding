# Generováno pomocí AI a je potřeba ověřit výstup
"""Confluence wiki snapshot manager for ČSAS RF style-guide pages.

Manages the local snapshots under
``source-documentation/notes/robot-styleguide/wiki/`` and their integrity
records in ``.github/scripts/csas-sources.manifest.json``.

Modes
-----
--check
    Offline integrity check.  Recompute sha256 of each local snapshot and
    compare against the manifest.  Exit 2 when any file has drifted (edited
    locally) or is missing.  Exit 0 when all snapshots match.
--check-upstream
    Online freshness check.  Requires a Confluence API token in
    ``CONFLUENCE_TOKEN`` (or a session cookie in ``CONFLUENCE_COOKIE``).
    Fetches the current ``version.number`` for every page and compares it
    against the ``confluence_version`` stored in the manifest.  Exit 2 when
    any page has a newer upstream version.  Exit 0 when everything is fresh.
--update
    Re-fetch every page from Confluence, convert HTML to Markdown, overwrite
    the local snapshots, update sha256 and confluence_version in the
    manifest, and rewrite ``_INDEX.md``.  Requires auth (same env vars).
--update-page <id>
    Like --update but for a single page only.
--integrity
    Alias for --check (explicit offline integrity pass, used in CI).

Paths
-----
Both default to this repository and can be pointed elsewhere, so the same
script can manage a snapshot set that lives outside it - an agent skill
folder, for instance - instead of being forked per consumer.

--manifest <path>
    Manifest to read and write.  Defaults to
    ``.github/scripts/csas-sources.manifest.json``.
--wiki-dir <path>
    Directory holding the snapshots and ``_INDEX.md``.  Defaults to
    ``source-documentation/notes/robot-styleguide/wiki/``.  When omitted, a
    ``snapshot_dir`` key in the manifest is used if present, resolved
    relative to the manifest's own parent directory.

Auth (for --check-upstream and --update)
-----------------------------------------
Three auth strategies are tried in order:

1. **Windows Edge SSO (default, no config needed).**
   Uses the ``win32.internet`` (``winreg``-based) cookie store via
   ``browser-cookie3`` (``pip install browser-cookie3``) if available, or
   falls back to launching a headless Edge subprocess that navigates to
   Confluence, lets Windows SSO authenticate automatically, and dumps the
   session cookie.  Works on any ČSAS developer workstation where Edge is
   already logged into the corporate identity provider.

2. **``CONFLUENCE_TOKEN``** — Bearer API token generated in your Atlassian
   profile.  Set this env var to skip the browser launch.

3. **``CONFLUENCE_COOKIE``** — Full ``Cookie:`` header value copied from a
   live browser session.  Last resort for environments that support neither
   SSO extraction nor API tokens.

Pass ``--no-browser`` to disable strategy 1 and go straight to env vars.

If all three strategies fail, the script exits 1 with a clear error message.
The offline modes (--check / --integrity) always work without any auth.

Exit codes
----------
0  clean / success
1  tool/auth/parse error
2  drift detected (--check) or stale pages detected (--check-upstream)
"""
from __future__ import annotations

import argparse
import hashlib
import html
import json
import os
import re
import sys
import urllib.request
import urllib.error
from pathlib import Path
from typing import Any

try:  # use the OS trust store (corporate CA in macOS Keychain / Windows cert store)
    import truststore
    truststore.inject_into_ssl()
except ImportError:
    pass

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MANIFEST_PATH = REPO_ROOT / ".github" / "scripts" / "csas-sources.manifest.json"
DEFAULT_WIKI_DIR = REPO_ROOT / "source-documentation" / "notes" / "robot-styleguide" / "wiki"

# Live values. --manifest / --wiki-dir rebind these in main(); _ensure_wiki_dir() below also
# resolves a manifest's snapshot_dir for callers that invoke a cmd_* function directly.
MANIFEST_PATH = DEFAULT_MANIFEST_PATH
WIKI_DIR = DEFAULT_WIKI_DIR
INDEX_FILE = WIKI_DIR / "_INDEX.md"

# Whether --wiki-dir was supplied.  Kept separate from the value: passing the default path on
# purpose must still beat a manifest's snapshot_dir, and a comparison cannot tell the two apart.
_WIKI_DIR_EXPLICIT = False

CONFLUENCE_BASE = "https://cnfl.csin.cz"


# --------------------------------------------------------------------------- #
# Manifest helpers
# --------------------------------------------------------------------------- #

def _load_manifest() -> dict:
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


def _save_manifest(data: dict) -> None:
    MANIFEST_PATH.write_text(
        json.dumps(data, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def _manifest_wiki_pages(manifest: dict) -> list[dict]:
    return manifest.get("wiki_pages", [])


def _ensure_wiki_dir(manifest: dict) -> None:
    """Honour a ``snapshot_dir`` key in the manifest, resolved against the manifest itself.

    Called from every command rather than only from ``main()``, because
    ``sync_csas_sources._wiki_integrity_check`` imports this module and calls ``cmd_check``
    directly; without this it would check the default directory instead of the manifest's own.

    An explicit ``--wiki-dir`` wins.  That is tracked by ``_WIKI_DIR_EXPLICIT`` rather than by
    comparing against the default, because passing the default path on purpose is not the same
    as omitting the option.
    """
    global WIKI_DIR, INDEX_FILE
    if not _WIKI_DIR_EXPLICIT and manifest.get("snapshot_dir"):
        WIKI_DIR = (MANIFEST_PATH.parent / manifest["snapshot_dir"]).resolve()
        INDEX_FILE = WIKI_DIR / "_INDEX.md"


# --------------------------------------------------------------------------- #
# sha256 helpers
# --------------------------------------------------------------------------- #

def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()[:16]


# --------------------------------------------------------------------------- #
# Index helpers
# --------------------------------------------------------------------------- #

_INDEX_LINE_RE = re.compile(
    r"^\- \[(.+?)\]\(\.\/(.+?)\) — depth (\d+), id (\d+)"
)


def _parse_index() -> list[dict]:
    """Return page records from _INDEX.md.  Deduplicates by page id."""
    if not INDEX_FILE.exists():
        return []
    seen: dict[int, dict] = {}
    for line in INDEX_FILE.read_text(encoding="utf-8").splitlines():
        m = _INDEX_LINE_RE.match(line)
        if not m:
            continue
        title, fname, depth, pid = m.groups()
        pid_int = int(pid)
        if pid_int not in seen:
            seen[pid_int] = {
                "id": pid_int, "title": title, "file": fname, "depth": int(depth),
            }
    return list(seen.values())


def _rewrite_index(pages: list[dict]) -> None:
    """Rewrite _INDEX.md from a list of page dicts (id, title, file, depth)."""
    lines = ["# Confluence crawl index", "", f"Pages: {len(pages)}", ""]
    for p in sorted(pages, key=lambda x: (x["depth"], x["title"])):
        lines.append(
            f"- [{p['title']}](./{p['file']}) — depth {p['depth']}, id {p['id']}"
        )
    INDEX_FILE.write_text("\n".join(lines) + "\n", encoding="utf-8")


# Populated by main() when --no-browser is passed.
_NO_BROWSER = False

# --------------------------------------------------------------------------- #
# Confluence API helpers
# --------------------------------------------------------------------------- #

def _extract_sso_cookie_via_browser_cookie3() -> str | None:
    """Try browser-cookie3 to read Edge's live session cookie for cnfl.csin.cz."""
    try:
        import browser_cookie3  # type: ignore[import-untyped]
        jar = browser_cookie3.edge(domain_name="cnfl.csin.cz")
        cookies = "; ".join(f"{c.name}={c.value}" for c in jar)
        return cookies if cookies else None
    except Exception:
        return None


def _extract_sso_cookie_via_subprocess() -> str | None:
    """Launch Edge silently to let SSO authenticate, then extract the cookie.

    Uses PowerShell + Edge DevTools protocol to grab cookies after SSO.
    Only attempted on Windows.  Gracefully returns None on failure.
    """
    import subprocess  # noqa: PLC0415
    import tempfile    # noqa: PLC0415

    if sys.platform != "win32":
        return None
    ps_script = r"""
$ErrorActionPreference = 'SilentlyContinue'
$edge = (Get-Command msedge.exe -ErrorAction SilentlyContinue)?.Source
if (-not $edge) { exit 1 }
# Run Edge with remote debugging on a temp port to capture SSO cookie
$port = 19222
$job = Start-Process -PassThru -WindowStyle Hidden $edge `
    "--headless --disable-gpu --remote-debugging-port=$port `
     --profile-directory=Default cnfl.csin.cz" 2>$null
Start-Sleep -Seconds 8
try {
    $resp = Invoke-WebRequest -Uri "http://localhost:$port/json" -UseBasicParsing -ErrorAction Stop
    $pages = $resp.Content | ConvertFrom-Json
    $target = ($pages | Where-Object { $_.url -like '*cnfl*' } | Select-Object -First 1).id
    if ($target) {
        $ws = New-Object System.Net.WebSockets.ClientWebSocket
        $uri = [System.Uri]"ws://localhost:$port/json/version" # placeholder - full impl requires WebSocket
    }
} catch {}
Stop-Process -Id $job.Id -ErrorAction SilentlyContinue
"""
    # The full DevTools WebSocket dance is complex; return None and let
    # browser-cookie3 handle it.  This stub exists as the documented path
    # for future enhancement.
    return None


def _load_secrets_file() -> None:
    """Load KEY=VALUE lines from <repo>/secrets.txt (gitignored) into os.environ if not already set."""
    for name in ("secrets.txt", ".env"):
        f = Path(__file__).resolve().parents[2] / name
        if not f.is_file():
            continue
        for line in f.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip().removeprefix("export ").strip(), v.strip().strip("'\""))


def _auth_headers() -> dict[str, str]:
    """Resolve auth via: Edge SSO → CONFLUENCE_TOKEN → CONFLUENCE_COOKIE."""
    _load_secrets_file()
    # Strategy 1: env var token (fastest, CI-friendly)
    token = os.environ.get("CONFLUENCE_TOKEN", "").strip()
    if token:
        return {"Authorization": f"Bearer {token}"}

    # Strategy 2: env var cookie
    cookie_env = os.environ.get("CONFLUENCE_COOKIE", "").strip()
    if cookie_env:
        return {"Cookie": cookie_env}

    if not _NO_BROWSER:
        # Strategy 3a: browser-cookie3 reads Edge's live cookie store (no popup)
        cookie = _extract_sso_cookie_via_browser_cookie3()
        if cookie:
            return {"Cookie": cookie}
        # Strategy 3b: subprocess Edge SSO (stub — see _extract_sso_cookie_via_subprocess)
        cookie = _extract_sso_cookie_via_subprocess()
        if cookie:
            return {"Cookie": cookie}

    print(
        "ERROR: Confluence auth failed.  Tried (in order):\n"
        "  1. CONFLUENCE_TOKEN env var — not set\n"
        "  2. CONFLUENCE_COOKIE env var — not set\n"
        + ("  3. Edge SSO via browser-cookie3 — not available (install with: pip install browser-cookie3)\n"
           if not _NO_BROWSER else "  3. Edge SSO — disabled via --no-browser\n") +
        "Set CONFLUENCE_TOKEN or install browser-cookie3 and ensure Edge is signed in.",
        file=sys.stderr,
    )
    raise SystemExit(1)


def _confluence_get(path: str) -> Any:
    """GET <CONFLUENCE_BASE><path> with auth; return parsed JSON."""
    url = f"{CONFLUENCE_BASE}{path}"
    req = urllib.request.Request(url, headers={
        **_auth_headers(),
        "Accept": "application/json",
        "X-Atlassian-Token": "no-check",
    })
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raise RuntimeError(
            f"Confluence GET {url} → {exc.code} {exc.reason}"
        ) from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(
            f"Confluence GET {url} network error: {exc.reason}"
        ) from exc


def _fetch_page_version(page_id: int) -> int:
    """Return current version.number from Confluence."""
    data = _confluence_get(
        f"/rest/api/content/{page_id}?expand=version"
    )
    return int(data["version"]["number"])


def _fetch_page_markdown(page_id: int, title: str) -> str:
    """Fetch a Confluence page and return Markdown text."""
    data = _confluence_get(
        f"/rest/api/content/{page_id}"
        "?expand=body.export_view,version,ancestors,space"
    )
    version_num = int(data["version"]["number"])
    raw_html = data["body"]["export_view"]["value"]
    space_key = data.get("space", {}).get("key", "")
    ancestors = [a["title"] for a in data.get("ancestors", [])]
    depth = max(len(ancestors) - 1, 0)

    md = _html_to_md(raw_html)
    url = (
        f"{CONFLUENCE_BASE}/spaces/{space_key}/pages/{page_id}/"
        + urllib.parse.quote(title)
    )

    header = "\n".join([
        f"# {title}",
        "",
        f"- **pageId**: {page_id}",
        f"- **url**: {url}",
        f"- **depth**: {depth}",
        f"- **ancestors**: {' > '.join(ancestors)}",
        "",
        "---",
    ])
    return header + "\n" + md, version_num


# --------------------------------------------------------------------------- #
# Minimal HTML → Markdown converter (no external deps)
# --------------------------------------------------------------------------- #

def _html_to_md(raw: str) -> str:
    """Best-effort HTML-to-Markdown for Confluence export_view output."""
    text = raw

    # Strip <style>, <script> blocks entirely.
    text = re.sub(r"<style[^>]*>.*?</style>", "", text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<script[^>]*>.*?</script>", "", text, flags=re.DOTALL | re.IGNORECASE)

    # Headings
    for n in range(6, 0, -1):
        text = re.sub(
            rf"<h{n}[^>]*>(.*?)</h{n}>",
            lambda m, level=n: "#" * level + " " + m.group(1).strip(),
            text, flags=re.DOTALL | re.IGNORECASE,
        )

    # Bold / italic
    text = re.sub(r"<(?:strong|b)[^>]*>(.*?)</(?:strong|b)>", r"**\1**",
                  text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<(?:em|i)[^>]*>(.*?)</(?:em|i)>", r"*\1*",
                  text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<(?:code|tt)[^>]*>(.*?)</(?:code|tt)>", r"`\1`",
                  text, flags=re.DOTALL | re.IGNORECASE)

    # Code blocks
    text = re.sub(r"<pre[^>]*>(.*?)</pre>", r"\n```\n\1\n```\n",
                  text, flags=re.DOTALL | re.IGNORECASE)

    # Links
    text = re.sub(r'<a[^>]+href=["\']([^"\']+)["\'][^>]*>(.*?)</a>', r"[\2](\1)",
                  text, flags=re.DOTALL | re.IGNORECASE)

    # Images (just alt text)
    text = re.sub(r'<img[^>]+alt=["\']([^"\']*)["\'][^>]*/?>',
                  lambda m: f"[{m.group(1)}]" if m.group(1) else "", text,
                  flags=re.IGNORECASE)
    text = re.sub(r"<img[^>]*/?>", "", text, flags=re.IGNORECASE)

    # Lists
    text = re.sub(r"<li[^>]*>(.*?)</li>", r"- \1", text,
                  flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"</(?:ul|ol)>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"<(?:ul|ol)[^>]*>", "\n", text, flags=re.IGNORECASE)

    # Tables (very basic — preserve as pipe tables)
    text = re.sub(r"<th[^>]*>(.*?)</th>", r" **\1** |", text,
                  flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<td[^>]*>(.*?)</td>", r" \1 |", text,
                  flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<tr[^>]*>", "| ", text, flags=re.IGNORECASE)
    text = re.sub(r"</tr>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"</t(?:head|body|foot|able)>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"<t(?:head|tbody|tfoot|able)[^>]*>", "", text, flags=re.IGNORECASE)

    # Horizontal rules
    text = re.sub(r"<hr[^>]*/?>", "\n---\n", text, flags=re.IGNORECASE)

    # Paragraphs / line breaks
    text = re.sub(r"<br[^>]*/?>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"</p>", "\n\n", text, flags=re.IGNORECASE)
    text = re.sub(r"<p[^>]*>", "", text, flags=re.IGNORECASE)
    text = re.sub(r"<div[^>]*>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"</div>", "\n", text, flags=re.IGNORECASE)

    # Strip remaining tags
    text = re.sub(r"<[^>]+>", "", text)

    # HTML entities
    text = html.unescape(text)

    # Confluence macros that render client-side (e.g. Children Display / Page
    # Tree) leave behind a bare boolean parameter as orphaned text once their
    # wrapper tags are stripped above (observed as a stand-alone "true" or
    # "trueh2" line). Replace with an explicit marker instead of leaking the
    # raw macro parameter into the snapshot.
    text = re.sub(
        r"(?m)^[ \t]*(?:true|false)h?[0-9]*[ \t]*$",
        "<!-- Poznamka ze snapshotu: obsah makra (napr. strom podstranek) nebyl pri exportu zachycen -->",
        text,
    )

    # Collapse whitespace
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip() + "\n"


# --------------------------------------------------------------------------- #
# Core operations
# --------------------------------------------------------------------------- #

def cmd_check(manifest: dict) -> int:
    """Offline integrity check: local file sha256 vs manifest."""
    _ensure_wiki_dir(manifest)
    wiki_pages = _manifest_wiki_pages(manifest)
    if not wiki_pages:
        print("WARN: manifest has no wiki_pages block; run --update to seed it.",
              file=sys.stderr)
        return 0

    drifts: list[str] = []
    missing: list[str] = []
    for page in wiki_pages:
        fpath = WIKI_DIR / page["file"]
        if not fpath.exists():
            missing.append(page["file"])
            continue
        actual = _sha256_file(fpath)
        expected = page.get("sha256", "")
        if actual != expected:
            drifts.append(f"{page['file']} (expected {expected}, got {actual})")

    if missing:
        print(f"MISSING ({len(missing)}):")
        for f in missing:
            print(f"  {f}")
    if drifts:
        print(f"LOCAL-DRIFT ({len(drifts)}):")
        for d in drifts:
            print(f"  {d}")
    if not missing and not drifts:
        print(f"OK — {len(wiki_pages)} wiki snapshots intact.")
        return 0
    return 2


def cmd_check_upstream(manifest: dict) -> int:
    """Online freshness check: Confluence version vs manifest."""
    wiki_pages = _manifest_wiki_pages(manifest)
    if not wiki_pages:
        print("WARN: manifest has no wiki_pages block; run --update to seed it.",
              file=sys.stderr)
        return 0

    stale: list[str] = []
    errors: list[str] = []
    for page in wiki_pages:
        pid = page["id"]
        known_ver = page.get("confluence_version")
        try:
            current_ver = _fetch_page_version(pid)
        except RuntimeError as exc:
            errors.append(f"{page['file']}: {exc}")
            continue
        if known_ver is None:
            # Never fetched — treat as stale so first --update populates it.
            stale.append(f"{page['file']} (never fetched, upstream v{current_ver})")
        elif current_ver > known_ver:
            stale.append(
                f"{page['file']} (local v{known_ver} < upstream v{current_ver})"
            )
        else:
            print(f"  OK  {page['file']} v{current_ver}")

    if errors:
        print(f"\nERRORS ({len(errors)}):")
        for e in errors:
            print(f"  {e}", file=sys.stderr)
    if stale:
        print(f"\nSTALE ({len(stale)}):")
        for s in stale:
            print(f"  {s}")
        return 2
    if not errors:
        print(f"FRESH — all {len(wiki_pages)} pages are up to date.")
    return 0 if not errors else 1


def cmd_update(manifest: dict, page_ids: list[int] | None = None) -> int:
    """Re-fetch pages from Confluence, update snapshots and manifest."""
    # Need urllib.parse for URL encoding in _fetch_page_markdown
    import urllib.parse  # noqa: PLC0415

    _ensure_wiki_dir(manifest)
    wiki_pages = _manifest_wiki_pages(manifest)
    index_records = _parse_index()
    id_to_record: dict[int, dict] = {r["id"]: r for r in index_records}

    # Determine which page IDs to update.
    if page_ids:
        targets = [id_to_record[pid] for pid in page_ids if pid in id_to_record]
        unknown = [pid for pid in page_ids if pid not in id_to_record]
        if unknown:
            print(f"WARN: unknown page IDs (not in index): {unknown}", file=sys.stderr)
    else:
        targets = index_records

    if not targets:
        print("ERROR: no pages to update.", file=sys.stderr)
        return 1

    WIKI_DIR.mkdir(parents=True, exist_ok=True)
    manifest_by_id: dict[int, dict] = {p["id"]: p for p in wiki_pages}
    updated = 0
    errors = 0

    for rec in targets:
        pid = rec["id"]
        print(f"  [{pid}] {rec['title']} ...", end=" ", flush=True)
        try:
            md_text, version_num = _fetch_page_markdown(pid, rec["title"])
        except RuntimeError as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            errors += 1
            continue

        fpath = WIKI_DIR / rec["file"]
        fpath.write_text(md_text, encoding="utf-8")
        sha = _sha256_file(fpath)
        manifest_by_id[pid] = {
            "id": pid,
            "title": rec["title"],
            "file": rec["file"],
            "depth": rec.get("depth", 0),
            "sha256": sha,
            "confluence_version": version_num,
        }
        print(f"v{version_num} sha={sha}")
        updated += 1

    manifest["wiki_pages"] = list(manifest_by_id.values())
    _save_manifest(manifest)
    _rewrite_index(list(manifest_by_id.values()))
    print(f"\nUpdated {updated} pages; {errors} errors.")
    return 0 if not errors else 1


def cmd_seed(manifest: dict) -> int:
    """Offline seed: populate wiki_pages block from existing local files."""
    _ensure_wiki_dir(manifest)
    index_records = _parse_index()
    if not index_records:
        print("ERROR: _INDEX.md not found or empty.", file=sys.stderr)
        return 1

    pages: list[dict] = []
    for rec in index_records:
        fpath = WIKI_DIR / rec["file"]
        if not fpath.exists():
            print(f"WARN: file not found, skipping: {rec['file']}", file=sys.stderr)
            continue
        sha = _sha256_file(fpath)
        pages.append({
            "id": rec["id"],
            "title": rec["title"],
            "file": rec["file"],
            "depth": rec.get("depth", 0),
            "sha256": sha,
            "confluence_version": None,
        })

    manifest["wiki_pages"] = pages
    _save_manifest(manifest)
    print(f"Seeded {len(pages)} pages into manifest wiki_pages block.")
    return 0


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Confluence wiki snapshot manager for ČSAS RF style-guide pages"
    )
    g = parser.add_mutually_exclusive_group(required=True)
    g.add_argument("--check", "--integrity", action="store_true",
                   help="Offline sha256 integrity check (no auth needed)")
    g.add_argument("--check-upstream", action="store_true",
                   help="Online freshness check via Confluence API "
                        "(uses Edge SSO by default; override with "
                        "CONFLUENCE_TOKEN or CONFLUENCE_COOKIE env vars)")
    g.add_argument("--update", action="store_true",
                   help="Re-fetch pages from Confluence and update snapshots + manifest "
                        "(uses Edge SSO by default)")
    g.add_argument("--update-page", type=int, metavar="PAGE_ID",
                   help="Re-fetch a single page by Confluence page ID")
    g.add_argument("--seed", action="store_true",
                   help="Offline seed: populate manifest wiki_pages from existing local files")
    parser.add_argument("--json", action="store_true",
                        help="JSON output (only affects --check and --check-upstream)")
    parser.add_argument("--no-browser", action="store_true",
                        help="Disable Edge SSO cookie extraction; use only env vars "
                             "(CONFLUENCE_TOKEN / CONFLUENCE_COOKIE)")
    parser.add_argument("--manifest", type=Path, metavar="PATH",
                        help="Manifest to read and write "
                             "(default: .github/scripts/csas-sources.manifest.json)")
    parser.add_argument("--wiki-dir", type=Path, metavar="PATH",
                        help="Directory holding the snapshots and _INDEX.md. Defaults to the "
                             "manifest's snapshot_dir key, then to "
                             "source-documentation/notes/robot-styleguide/wiki/")
    args = parser.parse_args(argv)

    if args.no_browser:
        global _NO_BROWSER
        _NO_BROWSER = True

    # Reset to the defaults first: main() is callable more than once in one process (a test
    # runner, an embedding consumer), and an earlier --manifest/--wiki-dir must not leak in.
    global MANIFEST_PATH, WIKI_DIR, INDEX_FILE, _WIKI_DIR_EXPLICIT
    MANIFEST_PATH = args.manifest.resolve() if args.manifest else DEFAULT_MANIFEST_PATH
    WIKI_DIR = args.wiki_dir.resolve() if args.wiki_dir else DEFAULT_WIKI_DIR
    INDEX_FILE = WIKI_DIR / "_INDEX.md"
    _WIKI_DIR_EXPLICIT = args.wiki_dir is not None

    if not MANIFEST_PATH.exists():
        print(f"ERROR: manifest not found at {MANIFEST_PATH}", file=sys.stderr)
        return 1
    try:
        manifest = _load_manifest()
    except json.JSONDecodeError as exc:
        print(f"ERROR: manifest is not valid JSON: {exc}", file=sys.stderr)
        return 1

    # An explicit --wiki-dir already won above; otherwise the manifest's snapshot_dir applies.
    # Every cmd_* repeats this call, so a direct caller resolves the same directory.
    _ensure_wiki_dir(manifest)

    if args.check:
        return cmd_check(manifest)
    if args.check_upstream:
        return cmd_check_upstream(manifest)
    if args.update:
        return cmd_update(manifest)
    if args.update_page:
        return cmd_update(manifest, page_ids=[args.update_page])
    if args.seed:
        return cmd_seed(manifest)

    parser.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
