# Rules (the orchestrator pastes them into EVERY sub-agent task)

- Never read or print the content of `.env`; never ask for tokens or passwords in chat. Never commit secrets, tokens, cookies or internal URLs.
- Use dummy data only (`local-dummy-*`). Never add real endpoints or data.
- Never run load against TEST/PROD; a smoke run only against the user's own local mock. PROD tests are risky; do not suggest them without approval.
- Change only what the task requires, inside this repository (source, tests, config for the requested domain).
- Make small steps and run the tests after each; return what you did, the evidence (command output) and what is missing/failed.
- Invent nothing; if you do not know, say so.
- Respond in English, concisely.
