# PulseWatch MVP — Release Report

## Release contents

The release package contains a Next.js / TypeScript frontend, FastAPI backend, SQLAlchemy models, Alembic schema migration, PostgreSQL and Redis Docker Compose services, a Redis Streams worker, browser and Python SDKs, PWA manifest/service worker/icons, Windows startup and shutdown scripts, automated tests, GitHub Actions CI and technical documentation.

## Verification results in the build environment

| Check | Result | Evidence / limitation |
|---|---|---|
| Backend API and worker workflow tests | PASS | `python -m pytest -q` — 5 tests passed. Covers registration, project creation, key validation/rotation, ingestion, grouping, idempotency, filtering, issue details/actions, dashboard and fake-Redis pending-message recovery. |
| Python SDK tests | PASS | `PYTHONPATH=sdk/python python -m pytest -q sdk/python/tests` — 2 tests passed, covering event payload construction, stack traces, breadcrumbs, user/context metadata and safe transport failure. |
| Worker tests | PASS | Fake Redis stream tests cover event processing and abandoned pending-message recovery path. A real Redis server was not available. |
| Python syntax compilation | PASS | `python -m compileall` completed for backend and Python SDK source. |
| Alembic migration | PASS | Initial migration applied to a temporary SQLite database; expected application tables and Alembic version table were present. |
| JavaScript SDK TypeScript check | PASS | SDK source compiled with the available TypeScript compiler. Compiled `dist` JavaScript and `.d.ts` files are included in the package. |
| Frontend TSX syntax/type-shape check | PARTIAL PASS | TSX syntax and stub-assisted TypeScript checking passed with the available compiler. The official Next.js/React dependency install and production build could not run because the npm registry was unreachable from this environment. |
| Docker Compose YAML parse | PASS | Compose YAML parsed successfully and contained `db`, `redis`, `backend`, `worker` and `frontend` services. |
| Docker Compose config / image build / container startup | NOT RUN | Docker CLI / Engine is not installed in this environment. A successful multi-container launch is not claimed. |
| Browser E2E and actual PWA device installation | NOT RUN | No browser automation/device runtime was available. Manifest, service worker, icons and registration code are included. |
| Configurable project DSN | PASS | Project creation and key rotation returned the configured HTTPS ingestion base when `PUBLIC_API_BASE_URL` was set to a remote API address. |
| ZIP integrity / extraction | PASS | Final ZIP passed archive integrity testing, extracted into a clean directory, contained all required startup/config/source files, and the extracted backend/SDK tests and available configuration checks passed. |

## Known MVP limitations

- Rate limiting is local to an API process; use a shared Redis-backed limiter before scaling API replicas.
- There is no email verification, password reset, MFA, organization invitation flow, event retention scheduler, billing, enterprise SSO, session replay, distributed tracing or performance profiling.
- PWA shell caching is implemented, but offline event submission and queued dashboard mutations are not.
- A native Windows installer, Android APK and iOS application are not included.
- The frontend production build and end-to-end multi-container runtime still need confirmation on a machine with npm registry and Docker access.

## Startup

1. Extract the ZIP.
2. Start Docker Desktop.
3. Run `start-windows.bat`.
4. Open `http://localhost:3000`.

See the root README and `docs/CONFIGURATION.md` for SDK setup, PWA installation and environment variables.
