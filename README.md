# perf-agent

Copilot custom agent **`perf-setup`**: non-technical onboarding of new members into the GEORGEPETE / PERF
(Gatling load tests) process. It uses Confluence snapshots as knowledge base, checks access, tickets and the
local environment, and can optionally scaffold a local sample perf-test repository.

The agent definition is `.github/agents/perf-setup.agent.md` (reload VS Code after changing it).

## Quick start (new user)
```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env        # then fill in values; .env is git-ignored, never commit or paste it into chat
```
Required: `CONFLUENCE_TOKEN` (Confluence → Settings → Personal Access Tokens). Everything else is optional.
Then open the repo in VS Code and talk to the `perf-setup` agent. On first run it downloads the wiki snapshots.

## Configuration (`.env`)
| Variable | Used by | Purpose |
|---|---|---|
| `CONFLUENCE_TOKEN` | `wiki.py`, `read_page.py` | Confluence Personal Access Token (Bearer) |
| `SERVICENOW_URL`, `SERVICENOW_LOGIN`, `SERVICENOW_TEAM` | `check_tickets.py` | instance, your user_name, colleagues' logins |
| `SERVICENOW_TOKEN` / `SERVICENOW_COOKIE` | `check_tickets.py` | optional; with SSO the browser session cookie is used automatically |
| `REDIM_API_KEY`, `REDIM_REQUESTOR` | `request_access.py` | only for the holder of an API Manager key |

## Scripts (`.github/scripts`, run with the venv active)
| Script | What it does | Writes anything? |
|---|---|---|
| `wiki.py sync / status / refresh` | download, compare and refresh Confluence snapshots listed in `sources.json` | local `wiki/` only |
| `check_env.py` | Java 17, Git, IDE, GitHub login + repo access, Artifactory, proxy | no |
| `check_access.py` | check AD/Redim groups from `access.json` (often UNVERIFIED on a Mac) | no |
| `check_tickets.py` | read-only ServiceNow request check (SSO via browser cookie) | no |
| `request_access.py` | submit REDiM requests via API; dry run by default, `--submit` + typed "yes" | only with `--submit` |
| `scaffold.py <name> --dest <dir>` | create a local sample Gatling/Kotlin repo from the template | new local dir |
| `check_connection.py`, `read_page.py`, `crawl_confluence.py`, `sync_wiki_pages.py` | Confluence helpers (`sync_wiki_pages.py` holds shared auth + `.env` loader) | local files |

## Layout
- `.github/agents/perf-setup.agent.md` – agent instructions
- `.github/skills/perf-setup/`
  - `sources.json` – wiki pages/trees to snapshot (`wiki/` and `manifest.json` are git-ignored: internal content)
  - `access.json` – Redim groups per environment, REDiM portals, MiLA API URLs
  - `tickets.json` – ServiceNow items checked (SaaS tools are added here)
  - `glossary.md` – terms explained to non-technical users
  - `template/` – sample repo (Gatling + Kotlin, domain-based layout, detekt)

## Maintenance
- **Wiki changed?** `python wiki.py status` shows NEW/CHANGED/REMOVED; `refresh` updates snapshots. Then check
  whether `access.json`, `tickets.json` or the agent text need updating.
- **Add a wiki page:** add it to `sources.json` (`extra_pages` or `trees`), run `wiki.py sync`.
- **Group names changed:** edit `access.json`. Rights are requested in REDiM (tile *Windows*), not in ServiceNow.
- **Add a SaaS tool to the ticket check:** add an entry to `tickets.json`.
- **Change the sample repo:** edit `.github/skills/perf-setup/template/`, keep it generic (no real endpoints or
  data), verify with `./mvnw test` and `python scaffold.py test-repo --dest /tmp/x`. Follow the reference repo's
  conventions (domain layout, matching path/package/class, weights sum to 100).
- **Agent text:** `.github/agents/perf-setup.agent.md`. Reload VS Code afterwards.

## Security
- Never commit `.env`, tokens, cookies or wiki snapshots (internal content). The agent never reads `.env`.
- Before sharing this repo, make sure its git history contains no snapshots or secrets (the early history did).
- `request_access.py`, `check_tickets.py` and `check_access.py` never change anything unless `--submit` is given.

## Known gaps
- `check_tickets.py` (SSO) and `request_access.py` are not yet verified against the real systems.
- `check_access.py` cannot list AD groups on a Mac.
- REDiM API needs an API Manager key, which requires `XUC\APIMAN_DEVELOPER`; onboarding therefore requests rights manually in REDiM.
