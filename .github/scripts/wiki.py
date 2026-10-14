"""Manage Confluence snapshots for the perf-setup agent (read-only against Confluence, GET only).

  python wiki.py sync      # first run: download everything if snapshots are missing
  python wiki.py status    # compare Confluence with local snapshots, print changes + diffs (exit 2 if changed)
  python wiki.py refresh   # re-download everything, print what changed

Config: ../skills/perf-setup/sources.json (extra_pages list; 'trees' = pages crawled with all subpages).
Auth: CONFLUENCE_TOKEN or CONFLUENCE_COOKIE (use --no-browser).
"""
import argparse
import difflib
import json
import sys
import urllib.parse  # noqa: F401  (needed by sync_wiki_pages._fetch_page_markdown)
from pathlib import Path

import sync_wiki_pages as sw
from crawl_confluence import children, slug

SKILL = Path(__file__).resolve().parents[1] / "skills" / "perf-setup"
WIKI = SKILL / "wiki"
MANIFEST = SKILL / "manifest.json"
CONFIG = SKILL / "sources.json"


def fetch_all(cfg: dict) -> dict[str, dict]:
    """Return {filename: page record incl. 'md'} for the whole tree plus extra pages."""
    out: dict[str, dict] = {}
    roots = list(cfg.get("trees", []))
    if cfg.get("root_id"):
        roots.append({"root_id": cfg["root_id"]})
    seen: set[int] = set()
    for tree in roots:
        rid = tree["root_id"]
        root = sw._confluence_get(f"/rest/api/content/{rid}")
        queue = [(rid, root["title"], 0)]
        while queue:
            pid, title, depth = queue.pop(0)
            if pid in seen:
                continue
            seen.add(pid)
            md, ver = sw._fetch_page_markdown(pid, title)
            out[slug(title, pid)] = {"id": pid, "title": title, "depth": depth, "md": md, "ver": ver}
            queue += [(k["id"], k["title"], depth + 1) for k in children(pid)]
    for ex in cfg.get("extra_pages", []):
        q = "expand=body.export_view,version" + ("&status=draft" if ex.get("draft") else "")
        try:
            d = sw._confluence_get(f"/rest/api/content/{ex['id']}?{q}")
        except RuntimeError:
            d = sw._confluence_get(f"/rest/api/content/{ex['id']}?expand=body.export_view,version")
        md = f"# {d['title']}\n\n- **pageId**: {ex['id']}\n- **status**: {d.get('status')}\n\n---\n"
        md += sw._html_to_md(d["body"]["export_view"]["value"])
        out[ex["file"]] = {"id": ex["id"], "title": d["title"], "depth": 1, "md": md,
                           "ver": d["version"]["number"]}
    return out


def write_all(pages: dict[str, dict]) -> None:
    WIKI.mkdir(parents=True, exist_ok=True)
    for old in WIKI.glob("*.md"):
        if old.name not in pages:
            old.unlink()
    records = []
    for fname, p in pages.items():
        (WIKI / fname).write_text(p["md"], encoding="utf-8")
        records.append({"id": p["id"], "title": p["title"], "file": fname, "depth": p["depth"],
                        "sha256": sw._sha256_file(WIKI / fname), "confluence_version": p["ver"]})
    lines = ["# Confluence crawl index", "", f"Pages: {len(records)}", ""]
    for r in sorted(records, key=lambda x: (x["depth"], x["file"])):
        lines.append(f"- [{r['title']}](./{r['file']}) — depth {r['depth']}, id {r['id']}")
    (WIKI / "_INDEX.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    MANIFEST.write_text(json.dumps({"snapshot_dir": "wiki", "wiki_pages": records},
                                   indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def compare(pages: dict[str, dict]) -> int:
    changed = 0
    local = {p.name for p in WIKI.glob("*.md") if p.name != "_INDEX.md"}
    for fname in sorted(set(pages) - local):
        print(f"NEW      {fname} ({pages[fname]['title']})")
        changed += 1
    for fname in sorted(local - set(pages)):
        print(f"REMOVED  {fname} (no longer in Confluence)")
        changed += 1
    for fname in sorted(set(pages) & local):
        old = (WIKI / fname).read_text(encoding="utf-8")
        if old != pages[fname]["md"]:
            changed += 1
            print(f"CHANGED  {fname}")
            diff = difflib.unified_diff(old.splitlines(), pages[fname]["md"].splitlines(),
                                        "local", "confluence", lineterm="", n=1)
            print("\n".join(list(diff)[:60]))
    return changed


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["sync", "status", "refresh"])
    ap.add_argument("--no-browser", action="store_true")
    a = ap.parse_args()
    sw._NO_BROWSER = a.no_browser
    cfg = json.loads(CONFIG.read_text(encoding="utf-8"))

    if a.cmd == "sync" and MANIFEST.exists() and any(WIKI.glob("*.md")):
        print("Snapshots already present - nothing to do (use 'status' or 'refresh').")
        return 0
    try:
        pages = fetch_all(cfg)
    except (RuntimeError, SystemExit) as exc:
        print(f"FAILED: {exc}", file=sys.stderr)
        return 1

    if a.cmd == "sync":
        write_all(pages)
        print(f"Downloaded {len(pages)} pages to {WIKI}")
        return 0
    n = compare(pages) if WIKI.exists() else len(pages)
    if a.cmd == "status":
        print("No changes - snapshots are up to date." if not n else f"\n{n} difference(s). Run 'refresh' to update.")
        return 2 if n else 0
    write_all(pages)
    print(f"\nRefreshed {len(pages)} pages ({n} changed).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
