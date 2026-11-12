# PulseWatch MVP

PulseWatch is a Sentry-inspired application error monitoring platform. It captures browser and Python exceptions, processes them through Redis Streams, groups similar events into issues, and provides a dashboard for investigation and resolution.

> **MVP scope:** Error ingestion, issue grouping, event history, project-scoped ingestion credentials, issue status/priority actions, basic metrics, browser/Python SDKs, and an installable PWA shell. It is not a complete Sentry replacement.

## Start on Windows

**Requirements:** Windows 10/11, Docker Desktop with the Linux container engine enabled, and internet access on first build (Docker must pull base images and npm/Python packages).

1. Extract the ZIP to a folder such as `C:\Projects\PulseWatch-MVP`.
2. Start Docker Desktop and wait until its engine is running.
3. Double-click `start-windows.bat`.
4. Open [http://localhost:3000](http://localhost:3000), create an account, and create a project.

The startup script creates `.env` from `.env.example` when needed, validates Compose, builds the services, and starts the stack. It prints the local URLs when finished.

You can also run the requested primary command from the project root:

```powershell
docker compose up --build
```

Compose uses safe local-development defaults when `.env` has not been created. Change `SESSION_SECRET` and `POSTGRES_PASSWORD` before exposing the service beyond your computer. For a remote deployment, set both `NEXT_PUBLIC_API_URL` (frontend build-time API URL) and `PUBLIC_API_BASE_URL` (the public API base used in generated SDK DSNs) to the HTTPS API address, and set `COOKIE_SECURE=true`.

### Local URLs

| Service | URL |
|---|---|
| Frontend / PWA | http://localhost:3000 |
| Backend | http://localhost:8000 |
| OpenAPI / Swagger | http://localhost:8000/docs |
| Liveness | http://localhost:8000/health/live |
| Readiness | http://localhost:8000/health/ready |

Stop the services with `stop-windows.bat` or `docker compose down`. Database and Redis data are stored in named Docker volumes and survive container restarts. `docker compose down -v` deletes those volumes and all local data.

## First-run workflow

1. Register an account. Registration also creates a workspace and owner membership.
2. Create a project and select its platform.
3. Copy the project DSN / public ingestion key shown after project creation. The full value is deliberately shown only once.
4. Open **SDK Setup** and follow the JavaScript/React/Next.js or Python instructions.
5. Use **Send a test event** while the first-run credential is visible, or trigger a real exception through the SDK.
6. Open **Issues** to inspect the grouped issue, event stack trace, context, tags and activity.
7. Resolve, reopen, ignore, assign, or change issue priority from the issue drawer.

The project key is a write-only ingestion credential. It cannot authenticate to dashboard, organization, issue, or project administration endpoints. If lost, rotate it under **Project settings**; the previous key is immediately deactivated.

## Connect a React / Next.js application

The SDK source is included locally and is not claimed to be published on npm.

```bash
npm install /path/to/PulseWatch-MVP/sdk/javascript
```

Initialize from a client-side entry point such as Next.js `instrumentation-client.ts`:

```ts
import { init } from "@pulsewatch/browser-sdk";

init({
  dsn: process.env.NEXT_PUBLIC_PULSEWATCH_DSN!,
  environment: process.env.NODE_ENV,
});
```

Then capture handled exceptions:

```ts
import { captureException } from "@pulsewatch/browser-sdk";

try {
  await submitCheckout();
} catch (error) {
  captureException(error, { feature: "checkout" });
  throw error;
}
```

The browser SDK also installs global `error` and `unhandledrejection` listeners, records low-detail click/navigation breadcrumbs, and exposes `addBreadcrumb()` for application-specific context. Network delivery is best-effort and should not interrupt the monitored application.

## Connect a Python / FastAPI application

Install the SDK from the included local source:

```bash
pip install -e ./sdk/python
```

Set the DSN shown by PulseWatch:

```powershell
$env:PULSEWATCH_DSN="http://localhost:8000/api/v1/ingest/YOUR_PROJECT_PUBLIC_KEY"
```

Use the SDK:

```python
from fastapi import FastAPI
from pulsewatch_sdk import init, integrate_fastapi, capture_exception, add_breadcrumb

app = FastAPI()
client = init(environment="production")
integrate_fastapi(app, client)

@app.post("/checkout")
async def checkout():
    add_breadcrumb("checkout", "Checkout route entered")
    try:
        return run_checkout()
    except Exception as exc:
        capture_exception(exc, {"route": "/checkout"})
        raise
```

A FastAPI sample is included at `sdk/python/examples/fastapi_example.py`.

## Install the PWA

PulseWatch includes a web app manifest, service worker and install icons. The browser must be able to reach both the frontend and API. Browsers require HTTPS for installation on remote hosts; `localhost` is treated as a secure development origin.

- **Windows (Chrome / Edge):** open `http://localhost:3000`, then use the install icon in the address bar or the browser menu's **Install PulseWatch** option.
- **Android (Chrome):** open the deployed HTTPS address, open the browser menu, and choose **Install app** or **Add to Home screen** (the label depends on the browser version).
- **Another device on your network:** `localhost` on that device refers to the device itself. Use a reachable LAN/deployed hostname, configure the frontend/API URLs and CORS origins accordingly, and serve the site over HTTPS for installation.

The PWA shell can cache the app entry page and static icons. It does not provide offline event submission, offline dashboard mutation queues, or native APK/installer packages.

## Architecture

```text
Monitored application
       |
       v
JavaScript / Python SDK
       |
       v
FastAPI ingestion endpoint ----> public project key validation
       |                                  |
       v                                  v
  payload limits / rate limiting / Pydantic validation
       |
       v
    Redis Streams
       |
       v
  background worker
       |
       v
fingerprint + idempotent issue grouping
       |
       v
   PostgreSQL <---- FastAPI dashboard API
       |                       |
       |                       v
       +----------------> Next.js PWA dashboard
```

The backend is a modular monolith plus a separate Redis Streams worker. It uses at-least-once delivery with idempotent event IDs, rather than claiming exactly-once delivery. Events are acknowledged only after the database commit. Messages that fail five processing attempts are copied to the dead-letter stream `pulsewatch:events:dead` and acknowledged from the main stream.

## Development without Docker

The backend can run against SQLite for a quick API smoke test. Install the dev requirements and set inline mode (PowerShell shown):

```powershell
cd backend
python -m pip install -r requirements-dev.txt
$env:DATABASE_URL = "sqlite:///./pulsewatch.db"
$env:EVENT_QUEUE_DRIVER = "inline"
uvicorn app.main:app --reload --port 8000
```

Inline mode processes ingested events synchronously and is for development/testing only. The Docker Compose configuration explicitly selects Redis Streams and PostgreSQL.

The backend and Python SDK require Python 3.10+; the Next.js frontend requires Node.js 20.9+ and npm. From `frontend/` run `npm install` and `npm run dev`. Set `NEXT_PUBLIC_API_URL=http://localhost:8000` for the browser-facing API URL.

## Tests

```bash
cd backend
python -m pip install -r requirements-dev.txt
python -m pytest -q
```

The backend tests cover registration/login, project creation, key rotation, valid-key ingestion in inline test mode, issue grouping, event deduplication, filtering and issue actions. The Python SDK has standalone transport/payload tests; run them with `PYTHONPATH=sdk/python python -m pytest sdk/python/tests -q` from the project root. These tests do not replace a full browser/device and multi-container acceptance test.

## Project structure

```text
PulseWatch-MVP/
├── backend/                  # FastAPI, SQLAlchemy, Alembic, Redis worker
├── frontend/                 # Next.js + TypeScript PWA
├── sdk/javascript/           # Browser/React SDK source
├── sdk/python/               # Dependency-free Python SDK source
├── docs/                     # Architecture, ERD, API and release notes
├── docker-compose.yml
├── .env.example
├── start-windows.bat
├── start-windows.ps1
└── stop-windows.bat
```

## Security and operational notes

- Passwords are hashed with PBKDF2-HMAC-SHA256; session tokens are HMAC-signed and stored in HttpOnly cookies.
- CORS defaults to localhost frontend origins. SameSite=Lax cookie policy is used for local deployment.
- Public project keys are SHA-256 hashed in the database and have ingestion-only scope.
- Ingestion validates payload shape, limits payload size and rate limits by project key in each API process.
- Redis processing uses a consumer group, idempotent database writes, retry counters and a dead-letter stream.
- The current rate limiter is process-local. For horizontally scaled API replicas, replace it with a shared Redis rate limiter.
- The current implementation has no email verification, password reset, MFA, audit export, event retention scheduler, organization invitations, billing, or enterprise SSO.
- Do not expose the development Compose defaults to the public internet. Configure strong secrets, HTTPS, secure cookies, backup/retention policy, and infrastructure-level access controls first.

## License

This repository is an MVP scaffold. Add a license before redistributing it publicly.
