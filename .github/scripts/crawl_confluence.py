"""Crawl a Confluence page and all its descendants into local Markdown snapshots.

Reuses auth + HTML->MD from sync_wiki_pages.py (must sit in the same folder).
Writes snapshots + _INDEX.md + manifest, so afterwards
`sync_wiki_pages.py --check / --check-upstream / --update` work as usual.

Usage:
  python crawl_confluence.py --root 1447887545 \
      --wiki-dir ../skills/perf-setup/wiki \
      --manifest ../skills/perf-setup/manifest.json [--no-browser]
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
import urllib.parse
from pathlib import Path

import sync_wiki_pages as sw


def slug(title: str, pid: int) -> str:
    t = unicodedata.normalize("NFKD", title).encode("ascii", "ignore").decode()
    t = re.sub(r"[^A-Za-z0-9]+", "-", t).strip("-").lower()[:60] or "page"
    return f"{t}-{pid}.md"


def children(pid: int) -> list[dict]:
    out, start = [], 0
    while True:
        data = sw._confluence_get(
            f"/rest/api/content/{pid}/child/page?limit=100&start={start}"
        )
        res = data.get("results", [])
        out += [{"id": int(r["id"]), "title": r["title"]} for r in res]
        if len(res) < 100:
            return out
        start += len(res)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", type=int, required=True, help="root page id")
    ap.add_argument("--wiki-dir", type=Path, required=True)
    ap.add_argument("--manifest", type=Path, required=True)
    ap.add_argument("--no-browser", action="store_true")
    a = ap.parse_args()
    sw._NO_BROWSER = a.no_browser

    wiki = a.wiki_dir.resolve()
    wiki.mkdir(parents=True, exist_ok=True)
    manifest_path = a.manifest.resolve()
    manifest_path.parent.mkdir(parents=True, exist_ok=True)

    root = sw._confluence_get(f"/rest/api/content/{a.root}")
    queue = [(a.root, root["title"], 0)]
    seen: set[int] = set()
    pages: list[dict] = []
    errors = 0

    while queue:
        pid, title, depth = queue.pop(0)
        if pid in seen:
            continue
        seen.add(pid)
        print(f"{'  ' * depth}[{pid}] {title} ...", end=" ", flush=True)
        try:
            md, ver = sw._fetch_page_markdown(pid, title)
            kids = children(pid)
        except RuntimeError as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            errors += 1
            continue
        fname = slug(title, pid)
        (wiki / fname).write_text(md, encoding="utf-8")
        pages.append({
            "id": pid, "title": title, "file": fname, "depth": depth,
            "sha256": sw._sha256_file(wiki / fname), "confluence_version": ver,
        })
        print(f"v{ver}, {len(kids)} children")
        queue += [(k["id"], k["title"], depth + 1) for k in kids]

    lines = ["# Confluence crawl index", "", f"Pages: {len(pages)}", ""]
    for p in sorted(pages, key=lambda x: (x["depth"], x["title"])):
        lines.append(f"- [{p['title']}](./{p['file']}) — depth {p['depth']}, id {p['id']}")
    (wiki / "_INDEX.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    manifest = {}
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["snapshot_dir"] = Path(
        __import__("os").path.relpath(wiki, manifest_path.parent)
    ).as_posix()
    manifest["wiki_pages"] = pages
    manifest_path.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(f"\nCrawled {len(pages)} pages, {errors} errors.")
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
