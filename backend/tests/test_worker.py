import json
from app.core.security import new_id
from app.db.session import SessionLocal
from app.models import Event, Membership, Organization, Project, User
from app.worker import recover_pending


class FakeRedis:
    def __init__(self, messages):
        self.messages = messages
        self.acked = []
        self.deleted = []
    def xautoclaim(self, *args, **kwargs):
        return ("0-0", self.messages, [])
    def xack(self, stream, group, stream_id):
        self.acked.append((stream, group, stream_id))
    def delete(self, key):
        self.deleted.append(key)


def test_worker_recovers_abandoned_pending_event(client):
    with SessionLocal() as db:
        user = User(id=new_id(), email="worker@example.com", name="Worker Test", password_hash="not-used")
        org = Organization(id=new_id(), name="Worker Org", slug="worker-org-test")
        db.add_all([user, org])
        db.flush()
        db.add(Membership(id=new_id(), user_id=user.id, organization_id=org.id, role="owner"))
        project = Project(id=new_id(), organization_id=org.id, name="Worker Project", platform="python")
        db.add(project)
        db.commit()
        project_id = project.id

    payload = {"event_id": "pending-worker-event", "message": "Abandoned worker event", "exception_type": "RuntimeError"}
    fake = FakeRedis([("1710000000000-0", {"project_id": project_id, "payload": json.dumps(payload)})])
    recover_pending(fake, "worker-test")

    assert fake.acked and fake.acked[0][2] == "1710000000000-0"
    with SessionLocal() as db:
        stored = db.query(Event).filter_by(event_id="pending-worker-event").first()
        assert stored is not None
        assert stored.message == "Abandoned worker event"
