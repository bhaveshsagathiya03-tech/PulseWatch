# PulseWatch Architecture

## Runtime components

- **Next.js PWA:** user authentication flows, project onboarding, dashboards, issue feed, issue investigation drawer, SDK instructions and project settings.
- **FastAPI API:** session auth, organization/project authorization, project key rotation, read APIs, issue actions, ingestion validation and SSE refresh notifications.
- **PostgreSQL:** users, organizations, memberships, projects, hashed ingestion keys, issues, individual events and issue activity.
- **Redis Streams:** decoupled event buffer and consumer group.
- **Worker:** fingerprinting, deduplication, issue grouping and database persistence.

## Event lifecycle

1. SDK forms an event payload and posts to `/api/v1/ingest/{project_public_key}`.
2. Ingestion rejects oversized payloads, validates the credential and rate limits the project key.
3. Pydantic validates event data. A server event UUID is generated when the SDK omitted one.
4. In Redis mode, the API appends the payload to `pulsewatch:events` and returns `202 Accepted`.
5. The consumer group worker reads a new message and computes a SHA-256 fingerprint scoped to the project, exception type, normalized message and first useful stack frame.
6. A unique `(project_id, fingerprint)` constraint identifies the grouped issue. The unique event ID prevents duplicate processing from inflating event counts.
7. The worker commits the event and issue update before acknowledging the Redis entry.
8. After five failed attempts, the message is copied into `pulsewatch:events:dead`.
9. Authenticated dashboards query PostgreSQL; SSE emits lightweight invalidation messages when new events are recorded.

## Delivery semantics

Redis Streams consumer groups provide at-least-once delivery. A worker may process a message again after interruption, so the database operation is idempotent by globally unique event ID. It is not exactly-once delivery. The included worker creates a consumer group, reads new entries, and periodically uses Redis 6.2+ `XAUTOCLAIM` to recover entries abandoned by crashed consumers after the configured idle threshold. Keep the worker count conservative for this MVP and monitor pending/DLQ stream depth.

## Boundaries

The public ingestion key is a write-only credential: the code hashes it and only uses the hash in the ingestion handler. Administrative endpoints require an HMAC-signed user session plus organization membership. The browser SDK should use only the ingestion DSN.
