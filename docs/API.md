# API Reference

Base URL: `http://localhost:8000` by default. Interactive OpenAPI docs: `/docs`. Configure `PUBLIC_API_BASE_URL` to control the public API hostname embedded in project DSNs returned during project creation and key rotation.

## Health

- `GET /health/live` — process liveness.
- `GET /health/ready` — database readiness.

## Authentication

- `POST /api/v1/auth/register` — `{name,email,password,organization_name}`; creates user, workspace and owner membership.
- `POST /api/v1/auth/login` — `{email,password}`; sets HttpOnly session cookie.
- `POST /api/v1/auth/logout` — clears the cookie.
- `GET /api/v1/me` — current user and organizations.

## Projects

- `GET /api/v1/projects` — list projects accessible through memberships.
- `POST /api/v1/projects` — `{name,platform,organization_id?}`; returns project and one-time `public_key` / `dsn`.
- `GET /api/v1/projects/{project_id}` — project details.
- `GET /api/v1/projects/{project_id}/setup` — setup metadata, active key prefix and whether an event has arrived.
- `POST /api/v1/projects/{project_id}/rotate-key` — deactivates old keys and returns the new key once.

## Ingestion

`POST /api/v1/ingest/{project_public_key}` — public endpoint for SDKs. Body fields: `event_id?`, `message`, `exception_type`, `stacktrace`, `severity`, `environment`, `timestamp?`, `user_id?`, `url?`, `context`, `tags`, `breadcrumbs`. Enforces project key, size and per-process rate limit. Returns `202 Accepted` in Redis mode. The browser-facing SDK DSN uses `PUBLIC_API_BASE_URL` (default `http://localhost:8000`).

## Dashboard and issues

- `GET /api/v1/dashboard?project_id={id}&window=24h|7d|30d`
- `GET /api/v1/issues?project_id={id}&status=unresolved|resolved|ignored|all&severity=...&q=...&sort=last_seen|frequency&limit=25&offset=0`
- `GET /api/v1/issues/{issue_id}` — issue plus latest 50 events and activities.
- `POST /api/v1/issues/{issue_id}/actions` — `{action: resolve|reopen|ignore|assign_to_me|priority, value?}`.
- `GET /api/v1/stream?project_id={id}` — authenticated SSE refresh events.

All dashboard and administrative endpoints require an authenticated session and membership in the project's organization.
