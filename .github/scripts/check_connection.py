"""Quick Confluence connectivity/auth test: fetches the root page title and its children count."""
import sys

import sync_wiki_pages as sw

ROOT_ID = 1447887545


def main() -> int:
    sw._NO_BROWSER = "--no-browser" in sys.argv
    try:
        page = sw._confluence_get(f"/rest/api/content/{ROOT_ID}?expand=version")
        kids = sw._confluence_get(f"/rest/api/content/{ROOT_ID}/child/page?limit=100")
    except (RuntimeError, SystemExit) as exc:
        print(f"FAILED: {exc}", file=sys.stderr)
        return 1
    print(f"OK: '{page['title']}' v{page['version']['number']}, "
          f"{len(kids.get('results', []))} direct child pages")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
