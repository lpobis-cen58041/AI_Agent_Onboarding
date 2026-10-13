"""Read-only fetch of a single Confluence page (published or draft) to Markdown on stdout.

Only issues HTTP GET requests; never modifies the page or its draft.

  python read_page.py 2318991891 --draft [--no-browser] [-o out.md]
"""
import argparse
import urllib.parse

import sync_wiki_pages as sw


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("page_id", type=int)
    ap.add_argument("--draft", action="store_true", help="read the draft version")
    ap.add_argument("--no-browser", action="store_true")
    ap.add_argument("-o", "--output")
    a = ap.parse_args()
    sw._NO_BROWSER = a.no_browser

    q = "expand=body.export_view,version,space"
    if a.draft:
        q += "&status=draft"
    try:
        data = sw._confluence_get(f"/rest/api/content/{a.page_id}?{q}")
    except RuntimeError as exc:
        if a.draft:
            print(f"Draft not readable ({exc}); trying published version...")
            data = sw._confluence_get(f"/rest/api/content/{a.page_id}?{q.replace('&status=draft', '')}")
        else:
            raise
    md = f"# {data['title']}\n\n- **pageId**: {a.page_id}\n- **status**: {data.get('status')}\n\n---\n"
    md += sw._html_to_md(data["body"]["export_view"]["value"])
    if a.output:
        open(a.output, "w", encoding="utf-8").write(md)
        print(f"Saved {a.output} ({len(md)} chars)")
    else:
        print(md)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
