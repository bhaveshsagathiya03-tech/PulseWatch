# Configuration Reference

Docker Compose reads the optional root `.env` file automatically. `start-windows.bat` creates it from `.env.example` if it does not exist. Compose supplies internal database/Redis URLs and the Redis queue driver; the values below can be changed in `.env` where shown.

| Variable | Default | Required | Purpose |
|---|---|---:|---|
| `APP_NAME` | `PulseWatch` | No | Backend display/service name. |
| `APP_ENV` | `development` | No | Environment label. |
| `POSTGRES_PASSWORD` | `pulsewatch_local_only` | Local default only | PostgreSQL password. Set a strong value before external exposure. |
| `DATABASE_URL` | `sqlite:///./pulsewatch.db` in direct backend mode; Compose overrides it | Runtime | SQLAlchemy connection URL. Use `postgresql+psycopg://...` with PostgreSQL. |
| `REDIS_URL` | `redis://localhost:6379/0` in direct backend mode; Compose overrides it | Runtime for Redis queue mode | Redis connection URL. |
| `EVENT_QUEUE_DRIVER` | `redis` in Compose; `redis` in backend settings | Runtime | `redis` for real queued processing; `inline` only for local testing. |
| `SESSION_SECRET` | Development placeholder | Yes for secure deployment | HMAC signing secret for session tokens. Replace with a long random value. |
| `SESSION_TTL_HOURS` | `168` | No | Session lifetime. |
| `SESSION_COOKIE` | `pulsewatch_session` | No | HttpOnly session cookie name. |
| `COOKIE_SECURE` | `false` | No | Set `true` when serving the application over HTTPS. |
| `CORS_ORIGINS` | `http://localhost:3000,http://127.0.0.1:3000` | No | Comma-separated allowed frontend origins. |
| `NEXT_PUBLIC_API_URL` | `http://localhost:8000` | No | Browser-reachable API base URL, baked into the Next.js frontend at build time. |
| `PUBLIC_API_BASE_URL` | `http://localhost:8000` | No | Publicly reachable API base URL used to construct the project ingestion DSN returned during setup and key rotation. |
| `MAX_EVENT_BYTES` | `262144` | No | Maximum accepted ingestion request body size. |
| `INGEST_RATE_PER_MINUTE` | `120` | No | Per-process, per-key ingestion request limit. |
| `REDIS_STREAM` | `pulsewatch:events` | No | Redis Stream carrying incoming event payloads. |
| `REDIS_CONSUMER_GROUP` | `pulsewatch-workers` | No | Redis consumer group used by workers. |
| `REDIS_DEAD_LETTER_STREAM` | `pulsewatch:events:dead` | No | Stream for messages that exceed the retry limit. |
| `REDIS_CLAIM_IDLE_MS` | `60000` | No | Minimum idle time before abandoned pending messages can be claimed. |
| `LOG_LEVEL` | `INFO` | No | Worker log verbosity. |

For direct backend development without Docker, set `DATABASE_URL=sqlite:///./pulsewatch.db` and `EVENT_QUEUE_DRIVER=inline`. For the bundled Compose deployment, do not change the internal hostnames (`db` and `redis`) in `DATABASE_URL` / `REDIS_URL` unless the services are renamed.
