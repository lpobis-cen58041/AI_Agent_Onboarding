# perf-agent

Agent `perf-setup` + Confluence snapshot tooling.

## Setup
```
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
export CONFLUENCE_TOKEN=...     # or CONFLUENCE_COOKIE="..."; never commit it
```

## Test connection
```
cd .github/scripts
python check_connection.py --no-browser
```

## Crawl root page + subpages
```
python crawl_confluence.py --root 1447887545 --no-browser \
  --wiki-dir ../skills/perf-setup/wiki --manifest ../skills/perf-setup/manifest.json
python sync_wiki_pages.py --manifest ../skills/perf-setup/manifest.json --check
```
