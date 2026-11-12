from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app.models import Event, Issue


def test_complete_error_monitoring_workflow(client):
    registration = client.post("/api/v1/auth/register", json={
        "name": "Taylor Developer", "email": "taylor@example.com", "password": "correct-horse-battery",
        "organization_name": "Example Engineering",
    })
    assert registration.status_code == 201
    assert registration.json()["user"]["email"] == "taylor@example.com"

    project_response = client.post("/api/v1/projects", json={"name": "Storefront", "platform": "react"})
    assert project_response.status_code == 201
    created = project_response.json()
    project_id = created["project"]["id"]
    public_key = created["public_key"]
    assert public_key.startswith("pw_pub_")

    payload = {
        "event_id": "test-event-001", "message": "Payment provider timed out for order 123",
        "exception_type": "TimeoutError", "stacktrace": "TimeoutError: Payment provider timed out\n    at checkout (src/checkout.ts:20:4)",
        "severity": "error", "environment": "production", "user_id": "customer-42",
        "url": "https://example.test/checkout", "context": {"route": "/checkout"}, "tags": {"release": "1.2.0"},
        "breadcrumbs": [{"category": "navigation", "message": "Checkout opened", "timestamp": "2026-11-12T08:00:00Z"}],
    }
    ingest_url = f"/api/v1/ingest/{public_key}"
    first = client.post(ingest_url, json=payload)
    assert first.status_code == 202
    assert first.json()["accepted"] is True
    issue_id = first.json()["issue_id"]

    # A second distinct event with the same signature joins the same grouped issue.
    second_payload = {**payload, "event_id": "test-event-002"}
    second = client.post(ingest_url, json=second_payload)
    assert second.status_code == 202
    assert second.json()["issue_id"] == issue_id
    assert second.json()["event_count"] == 2

    # Re-delivery of the exact same event ID is idempotent.
    duplicate = client.post(ingest_url, json=payload)
    assert duplicate.status_code == 202
    assert duplicate.json()["duplicate"] is True

    issue_list = client.get(f"/api/v1/issues?project_id={project_id}&status=unresolved")
    assert issue_list.status_code == 200
    assert issue_list.json()["total"] == 1
    assert issue_list.json()["items"][0]["event_count"] == 2
    production_only = client.get(f"/api/v1/issues?project_id={project_id}&environment=production")
    assert production_only.status_code == 200 and production_only.json()["total"] == 1
    development_only = client.get(f"/api/v1/issues?project_id={project_id}&environment=development")
    assert development_only.status_code == 200 and development_only.json()["total"] == 0

    detail = client.get(f"/api/v1/issues/{issue_id}")
    assert detail.status_code == 200
    assert len(detail.json()["events"]) == 2
    assert detail.json()["events"][0]["stacktrace"].startswith("TimeoutError")
    assert detail.json()["events"][0]["breadcrumbs"][0]["message"] == "Checkout opened"

    resolved = client.post(f"/api/v1/issues/{issue_id}/actions", json={"action": "resolve"})
    assert resolved.status_code == 200
    assert resolved.json()["status"] == "resolved"

    reopened = client.post(f"/api/v1/issues/{issue_id}/actions", json={"action": "reopen"})
    assert reopened.status_code == 200
    assert reopened.json()["status"] == "unresolved"
    priority = client.post(f"/api/v1/issues/{issue_id}/actions", json={"action": "priority", "value": "urgent"})
    assert priority.status_code == 200 and priority.json()["priority"] == "urgent"

    dashboard = client.get(f"/api/v1/dashboard?project_id={project_id}&window=24h")
    assert dashboard.status_code == 200
    assert dashboard.json()["metrics"]["events"] == 2

    with SessionLocal() as db:
        assert db.query(Event).count() == 2
        assert db.query(Issue).count() == 1


def test_project_key_is_not_an_admin_session(client):
    client.post("/api/v1/auth/register", json={
        "name": "Morgan", "email": "morgan@example.com", "password": "secure-password-123",
        "organization_name": "Morgan Labs",
    })
    created = client.post("/api/v1/projects", json={"name": "API", "platform": "python"}).json()
    key = created["public_key"]
    # A project ingestion key must not authorize administrative routes.
    client.cookies.clear()
    response = client.get("/api/v1/projects", headers={"Authorization": f"Bearer {key}"})
    assert response.status_code == 401


def test_ingestion_rejects_invalid_project_key(client):
    response = client.post("/api/v1/ingest/pw_pub_invalid", json={"message": "nope"})
    assert response.status_code == 401


def test_key_rotation_deactivates_previous_ingestion_key(client):
    client.post("/api/v1/auth/register", json={
        "name": "Jordan", "email": "jordan@example.com", "password": "strong-password-456",
        "organization_name": "Jordan Engineering",
    })
    created = client.post("/api/v1/projects", json={"name": "Web app", "platform": "nextjs"}).json()
    project_id = created["project"]["id"]
    old_key = created["public_key"]
    rotated = client.post(f"/api/v1/projects/{project_id}/rotate-key")
    assert rotated.status_code == 200
    new_key = rotated.json()["public_key"]
    payload = {"event_id": "rotate-001", "message": "post rotation test", "exception_type": "Error"}
    assert client.post(f"/api/v1/ingest/{old_key}", json=payload).status_code == 401
    assert client.post(f"/api/v1/ingest/{new_key}", json=payload).status_code == 202
