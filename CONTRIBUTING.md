# Contributing

1. Create a feature branch from the default branch.
2. Keep API contracts and SDK payloads backward-compatible where practical.
3. Add or update tests for backend behavior.
4. Run `cd backend && python -m pytest -q`, `PYTHONPATH=sdk/python python -m pytest sdk/python/tests -q`, and build the frontend with `cd frontend && npm install && npm run build` when package access is available.
5. Do not commit `.env`, database files, credentials or generated build directories.
6. Document changes to environment variables and event payload contracts.
