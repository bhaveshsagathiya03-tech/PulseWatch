from datetime import datetime, timezone
from sqlalchemy import func
from sqlalchemy.orm import Session
from app.models import Event, Issue, IssueActivity
from app.core.security import new_id
from app.services.fingerprints import fingerprint_for


def _dt(value):
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    if value:
        try:
            parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
            return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
        except ValueError:
            pass
    return datetime.now(timezone.utc)


def process_event(db: Session, project_id: str, payload: dict) -> dict:
    event_id = str(payload.get("event_id") or new_id())[:100]
    existing_event = db.query(Event).filter_by(event_id=event_id).first()
    if existing_event:
        # Event IDs are globally unique; do not disclose a different project's issue identifier.
        return {"duplicate": True, "issue_id": existing_event.issue_id if existing_event.project_id == project_id else None}

    message = str(payload.get("message") or "Unhandled error")[:8000]
    exception_type = str(payload.get("exception_type") or "Error")[:160]
    stacktrace = str(payload.get("stacktrace") or "")[:50000]
    fingerprint = fingerprint_for(project_id, exception_type, message, stacktrace)
    now = _dt(payload.get("timestamp"))
    severity = str(payload.get("severity") or "error").lower()
    if severity not in {"fatal", "error", "warning", "info", "debug"}:
        severity = "error"
    issue = db.query(Issue).filter_by(project_id=project_id, fingerprint=fingerprint).first()

    if issue is None:
        issue = Issue(
            id=new_id(), project_id=project_id, fingerprint=fingerprint,
            title=f"{exception_type}: {message[:180]}", exception_type=exception_type,
            message=message, severity=severity, status="unresolved", priority="normal",
            event_count=0, affected_users=0, first_seen=now, last_seen=now,
        )
        db.add(issue)
        db.flush()
        db.add(IssueActivity(id=new_id(), issue_id=issue.id, action="created", detail="First event received"))

    event = Event(
        id=new_id(), event_id=event_id, project_id=project_id, issue_id=issue.id,
        message=message, exception_type=exception_type, stacktrace=stacktrace,
        environment=str(payload.get("environment") or "production")[:80],
        user_id=str(payload.get("user_id"))[:160] if payload.get("user_id") is not None else None,
        url=str(payload.get("url"))[:2048] if payload.get("url") else None,
        context=payload.get("context") if isinstance(payload.get("context"), dict) else {},
        tags=payload.get("tags") if isinstance(payload.get("tags"), dict) else {},
        breadcrumbs=payload.get("breadcrumbs") if isinstance(payload.get("breadcrumbs"), list) else [],
        created_at=now,
    )
    db.add(event)
    db.flush()
    issue.event_count += 1
    previous_last_seen = _dt(issue.last_seen) if issue.last_seen else now
    issue.last_seen = max(previous_last_seen, now)
    issue.affected_users = int(
        db.query(func.count(func.distinct(Event.user_id))).filter(
            Event.issue_id == issue.id, Event.user_id.isnot(None)
        ).scalar() or 0
    )
    db.commit()
    return {"duplicate": False, "issue_id": issue.id, "event_id": event_id, "event_count": issue.event_count}
