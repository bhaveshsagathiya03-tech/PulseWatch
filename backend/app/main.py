import asyncio
import json
import time
from contextlib import asynccontextmanager
from collections import defaultdict, deque
from datetime import datetime, timedelta, timezone
from uuid import uuid4
from fastapi import Depends, FastAPI, HTTPException, Query, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from sqlalchemy import func, or_, text
from sqlalchemy.orm import Session
from app.api.deps import current_user
from app.core.config import settings
from app.core.security import create_project_key, create_session_token, hash_password, hash_project_key, new_id, verify_password
from app.db.base import Base
from app.db.session import engine, get_db, SessionLocal
from app.models import Event, Issue, IssueActivity, Membership, Organization, Project, ProjectKey, User
from app.schemas.api import IngestEvent, IssueActionIn, LoginIn, ProjectCreateIn, RegisterIn
from app.services.access import require_org_access, require_project_access
from app.services.processing import process_event
from app.queue import publish_event

@asynccontextmanager
async def lifespan(_app: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(title="PulseWatch API", version="1.0.0", description="Application error monitoring and issue investigation API", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=list(settings.allowed_origins),
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "X-Requested-With"],
)

_rate_buckets: dict[str, deque] = defaultdict(deque)


@app.get("/health/live")
def health_live():
    return {"status": "ok", "service": "pulsewatch-api"}


@app.get("/health/ready")
def health_ready(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
        return {"status": "ready", "database": "connected"}
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Database unavailable") from exc


def _set_session(response: Response, user_id: str):
    response.set_cookie(
        key=settings.session_cookie, value=create_session_token(user_id),
        httponly=True, secure=settings.cookie_secure, samesite="lax",
        max_age=settings.session_ttl_hours * 3600, path="/",
    )


def _slug(name: str) -> str:
    base = "-".join("".join(c.lower() if c.isalnum() else " " for c in name).split()) or "workspace"
    return f"{base[:150]}-{uuid4().hex[:6]}"


def _user_payload(user: User):
    organizations = [{"id": m.organization.id, "name": m.organization.name, "slug": m.organization.slug, "role": m.role}
                     for m in user.memberships]
    return {"id": user.id, "name": user.name, "email": user.email, "organizations": organizations}


@app.post("/api/v1/auth/register", status_code=201)
def register(body: RegisterIn, response: Response, db: Session = Depends(get_db)):
    email = body.email.lower().strip()
    if db.query(User).filter_by(email=email).first():
        raise HTTPException(status_code=409, detail="An account with this email already exists")
    user = User(id=new_id(), email=email, name=body.name.strip(), password_hash=hash_password(body.password))
    organization = Organization(id=new_id(), name=body.organization_name.strip(), slug=_slug(body.organization_name))
    membership = Membership(id=new_id(), organization=organization, user=user, role="owner")
    db.add_all([user, organization, membership])
    db.commit()
    db.refresh(user)
    _set_session(response, user.id)
    return {"user": _user_payload(user)}


@app.post("/api/v1/auth/login")
def login(body: LoginIn, response: Response, db: Session = Depends(get_db)):
    user = db.query(User).filter_by(email=body.email.lower().strip()).first()
    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Email or password is incorrect")
    _set_session(response, user.id)
    return {"user": _user_payload(user)}


@app.post("/api/v1/auth/logout")
def logout(response: Response):
    response.delete_cookie(settings.session_cookie, path="/")
    return {"ok": True}


@app.get("/api/v1/me")
def me(user: User = Depends(current_user)):
    return {"user": _user_payload(user)}


@app.post("/api/v1/projects", status_code=201)
def create_project(body: ProjectCreateIn, db: Session = Depends(get_db), user: User = Depends(current_user)):
    organization_id = body.organization_id
    if not organization_id:
        if not user.memberships:
            raise HTTPException(status_code=400, detail="Create an organization before creating a project")
        organization_id = user.memberships[0].organization_id
    require_org_access(db, user.id, organization_id)
    platform = body.platform.lower().strip()
    allowed = {"javascript", "react", "nextjs", "python", "fastapi"}
    if platform not in allowed:
        raise HTTPException(status_code=422, detail=f"Platform must be one of: {', '.join(sorted(allowed))}")
    project = Project(id=new_id(), organization_id=organization_id, name=body.name.strip(), platform=platform)
    key = create_project_key()
    key_row = ProjectKey(id=new_id(), project=project, key_hash=hash_project_key(key), key_prefix=key[:16], is_active=True)
    db.add_all([project, key_row])
    db.commit()
    db.refresh(project)
    return {"project": project, "public_key": key, "dsn": f"{settings.public_api_base_url}/api/v1/ingest/{key}"}


@app.get("/api/v1/projects")
def list_projects(db: Session = Depends(get_db), user: User = Depends(current_user)):
    org_ids = [m.organization_id for m in user.memberships]
    if not org_ids:
        return {"items": []}
    projects = db.query(Project).filter(Project.organization_id.in_(org_ids)).order_by(Project.created_at.desc()).all()
    return {"items": projects}


@app.get("/api/v1/projects/{project_id}")
def get_project(project_id: str, db: Session = Depends(get_db), user: User = Depends(current_user)):
    return require_project_access(db, user.id, project_id)


@app.post("/api/v1/projects/{project_id}/rotate-key")
def rotate_project_key(project_id: str, db: Session = Depends(get_db), user: User = Depends(current_user)):
    project = require_project_access(db, user.id, project_id)
    for key in project.keys:
        key.is_active = False
    public_key = create_project_key()
    db.add(ProjectKey(id=new_id(), project_id=project.id, key_hash=hash_project_key(public_key), key_prefix=public_key[:16], is_active=True))
    db.commit()
    return {"public_key": public_key, "dsn": f"{settings.public_api_base_url}/api/v1/ingest/{public_key}"}


def _rate_limit(key_hash: str):
    now = time.time()
    bucket = _rate_buckets[key_hash]
    while bucket and bucket[0] < now - 60:
        bucket.popleft()
    if len(bucket) >= settings.ingest_rate_per_minute:
        raise HTTPException(status_code=429, detail="Ingestion rate limit exceeded")
    bucket.append(now)


@app.post("/api/v1/ingest/{project_public_key}", status_code=202)
async def ingest(project_public_key: str, request: Request, db: Session = Depends(get_db)):
    raw = await request.body()
    if len(raw) > settings.max_event_bytes:
        raise HTTPException(status_code=413, detail="Event payload is too large")
    try:
        parsed = json.loads(raw or b"{}")
        event = IngestEvent.model_validate(parsed)
    except (json.JSONDecodeError, ValueError) as exc:
        raise HTTPException(status_code=422, detail="Invalid event payload") from exc
    key_hash = hash_project_key(project_public_key)
    key_row = db.query(ProjectKey).filter_by(key_hash=key_hash, is_active=True).first()
    if not key_row:
        raise HTTPException(status_code=401, detail="Invalid project ingestion key")
    _rate_limit(key_hash)
    payload = event.model_dump(mode="json")
    if not payload.get("event_id"):
        payload["event_id"] = str(uuid4())
    if settings.event_queue_driver == "inline":
        result = process_event(db, key_row.project_id, payload)
        return {"accepted": True, "mode": "inline", **result}
    try:
        stream_id = publish_event(key_row.project_id, payload)
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Event queue unavailable; retry the event") from exc
    return {"accepted": True, "stream_id": stream_id}


def _project_query(db: Session, user: User, project_id: str | None):
    if project_id:
        return require_project_access(db, user.id, project_id)
    org_ids = [m.organization_id for m in user.memberships]
    project = db.query(Project).filter(Project.organization_id.in_(org_ids)).order_by(Project.created_at.asc()).first() if org_ids else None
    if not project:
        raise HTTPException(status_code=404, detail="Create a project to start monitoring errors")
    return project


@app.get("/api/v1/dashboard")
def dashboard(project_id: str | None = None, window: str = Query(default="24h", pattern="^(24h|7d|30d)$"), db: Session = Depends(get_db), user: User = Depends(current_user)):
    project = _project_query(db, user, project_id)
    now = datetime.now(timezone.utc)
    start = now - {"24h": timedelta(hours=24), "7d": timedelta(days=7), "30d": timedelta(days=30)}[window]
    issues = db.query(Issue).filter_by(project_id=project.id)
    total_events = db.query(func.count(Event.id)).filter(Event.project_id == project.id, Event.created_at >= start).scalar() or 0
    unresolved = issues.filter(Issue.status == "unresolved").count()
    new_issues = issues.filter(Issue.first_seen >= start).count()
    affected = db.query(func.count(func.distinct(Event.user_id))).filter(Event.project_id == project.id, Event.created_at >= start, Event.user_id.isnot(None)).scalar() or 0
    recent = db.query(Issue).filter_by(project_id=project.id).order_by(Issue.last_seen.desc()).limit(6).all()
    top = db.query(Issue).filter_by(project_id=project.id).order_by(Issue.event_count.desc()).limit(5).all()
    buckets = []
    count = 24 if window == "24h" else (7 if window == "7d" else 30)
    step = timedelta(hours=1) if window == "24h" else timedelta(days=1)
    for i in range(count):
        bucket_start = start + step * i
        bucket_end = bucket_start + step
        event_count = db.query(func.count(Event.id)).filter(
            Event.project_id == project.id, Event.created_at >= bucket_start, Event.created_at < bucket_end
        ).scalar() or 0
        buckets.append({"label": bucket_start.strftime("%H:%M" if window == "24h" else "%b %d"), "events": int(event_count)})
    return {
        "project": {"id": project.id, "name": project.name, "platform": project.platform},
        "window": window,
        "metrics": {"events": int(total_events), "unresolved_issues": int(unresolved), "new_issues": int(new_issues), "affected_users": int(affected)},
        "trend": buckets,
        "recent_issues": [_issue_summary(i) for i in recent],
        "top_issues": [_issue_summary(i) for i in top],
    }


def _issue_summary(issue: Issue):
    return {
        "id": issue.id, "title": issue.title, "exception_type": issue.exception_type,
        "message": issue.message, "severity": issue.severity, "status": issue.status,
        "priority": issue.priority, "event_count": issue.event_count,
        "affected_users": issue.affected_users, "first_seen": issue.first_seen,
        "last_seen": issue.last_seen,
    }


@app.get("/api/v1/issues")
def list_issues(project_id: str | None = None, status: str | None = None, severity: str | None = None,
                environment: str | None = None, since: datetime | None = None,
                q: str | None = None, sort: str = "last_seen", limit: int = Query(25, ge=1, le=100),
                offset: int = Query(0, ge=0), db: Session = Depends(get_db), user: User = Depends(current_user)):
    project = _project_query(db, user, project_id)
    query = db.query(Issue).filter(Issue.project_id == project.id)
    if status and status != "all": query = query.filter(Issue.status == status)
    if severity and severity != "all": query = query.filter(Issue.severity == severity)
    if environment and environment != "all": query = query.filter(Issue.events.any(Event.environment == environment))
    if since: query = query.filter(Issue.last_seen >= since)
    if q: query = query.filter(or_(Issue.title.ilike(f"%{q}%"), Issue.message.ilike(f"%{q}%"), Issue.exception_type.ilike(f"%{q}%")))
    total = query.count()
    order_column = Issue.event_count if sort == "frequency" else Issue.last_seen
    items = query.order_by(order_column.desc()).offset(offset).limit(limit).all()
    return {"items": [_issue_summary(i) for i in items], "total": total, "limit": limit, "offset": offset}


@app.get("/api/v1/issues/{issue_id}")
def issue_detail(issue_id: str, db: Session = Depends(get_db), user: User = Depends(current_user)):
    issue = db.query(Issue).filter_by(id=issue_id).first()
    if not issue: raise HTTPException(status_code=404, detail="Issue not found")
    require_project_access(db, user.id, issue.project_id)
    events = db.query(Event).filter_by(issue_id=issue.id).order_by(Event.created_at.desc()).limit(50).all()
    activities = db.query(IssueActivity).filter_by(issue_id=issue.id).order_by(IssueActivity.created_at.desc()).limit(50).all()
    return {
        **_issue_summary(issue), "fingerprint": issue.fingerprint,
        "project": {"id": issue.project.id, "name": issue.project.name, "platform": issue.project.platform},
        "events": [{"id": e.id, "event_id": e.event_id, "message": e.message, "exception_type": e.exception_type,
                    "stacktrace": e.stacktrace, "environment": e.environment, "user_id": e.user_id,
                    "url": e.url, "context": e.context, "tags": e.tags, "breadcrumbs": e.breadcrumbs, "created_at": e.created_at} for e in events],
        "activity": [{"id": a.id, "action": a.action, "detail": a.detail, "created_at": a.created_at} for a in activities],
    }


@app.post("/api/v1/issues/{issue_id}/actions")
def issue_action(issue_id: str, body: IssueActionIn, db: Session = Depends(get_db), user: User = Depends(current_user)):
    issue = db.query(Issue).filter_by(id=issue_id).first()
    if not issue: raise HTTPException(status_code=404, detail="Issue not found")
    require_project_access(db, user.id, issue.project_id)
    action = body.action.lower()
    details = ""
    if action == "resolve": issue.status = "resolved"; details = "Issue marked as resolved"
    elif action == "reopen": issue.status = "unresolved"; details = "Issue reopened"
    elif action == "ignore": issue.status = "ignored"; details = "Issue ignored"
    elif action == "assign_to_me": issue.assigned_user_id = user.id; details = f"Assigned to {user.name}"
    elif action == "priority":
        if body.value not in {"low", "normal", "high", "urgent"}:
            raise HTTPException(status_code=422, detail="Priority must be low, normal, high or urgent")
        issue.priority = body.value; details = f"Priority changed to {body.value}"
    else:
        raise HTTPException(status_code=422, detail="Unsupported issue action")
    db.add(IssueActivity(id=new_id(), issue_id=issue.id, actor_user_id=user.id, action=action, detail=details))
    db.commit()
    db.refresh(issue)
    return _issue_summary(issue)


@app.get("/api/v1/projects/{project_id}/setup")
def project_setup(project_id: str, db: Session = Depends(get_db), user: User = Depends(current_user)):
    project = require_project_access(db, user.id, project_id)
    active_key = db.query(ProjectKey).filter_by(project_id=project.id, is_active=True).order_by(ProjectKey.created_at.desc()).first()
    return {"project_id": project.id, "project_name": project.name, "platform": project.platform,
            "key_prefix": active_key.key_prefix if active_key else None,
            "installed": db.query(Event).filter_by(project_id=project.id).count() > 0,
            "warning": "The full public key is shown only when the project is created or its key is rotated."}


@app.get("/api/v1/stream")
async def stream(project_id: str, user: User = Depends(current_user)):
    # Authorize before opening the stream; each message contains only a lightweight invalidation.
    with SessionLocal() as db:
        require_project_access(db, user.id, project_id)
    async def events():
        last_seen = datetime.now(timezone.utc) - timedelta(seconds=10)
        while True:
            with SessionLocal() as db:
                newest = db.query(func.max(Event.created_at)).filter(Event.project_id == project_id).scalar()
                if newest and (newest.replace(tzinfo=timezone.utc) if newest.tzinfo is None else newest) > last_seen:
                    last_seen = newest.replace(tzinfo=timezone.utc) if newest.tzinfo is None else newest
                    yield f"event: refresh\ndata: {json.dumps({'updated_at': last_seen.isoformat()})}\n\n"
            yield ": keep-alive\n\n"
            await asyncio.sleep(3)
    return StreamingResponse(events(), media_type="text/event-stream", headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@app.get("/api/v1/organizations")
def list_organizations(user: User = Depends(current_user)):
    return {"items": [{"id": m.organization.id, "name": m.organization.name, "role": m.role} for m in user.memberships]}
