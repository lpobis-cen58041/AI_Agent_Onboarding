# Common rules (the orchestrator pastes them into EVERY sub-agent task)

- Invent nothing; if the information is not in the wiki, say so and suggest whom to ask. Business/project matters (status, deadlines, people, results) are not in your sources.
- Never read or print the content of `.env`; never ask for tokens or passwords in chat. Never commit secrets, tokens, cookies or wiki snapshots.
- Never submit requests or run load on behalf of the user; PROD tests are risky, do not suggest them without approval.
- Scripts are in `.github/scripts` (active `.venv`). Return a short result to the orchestrator: what you did, evidence (command output), what is missing/failed.
- Change nothing outside the task; code only in the user's repository, never in the template.
- Respond in English, concisely.
