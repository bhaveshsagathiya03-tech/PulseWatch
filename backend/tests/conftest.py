import os
os.environ["DATABASE_URL"] = "sqlite:///./test_pulsewatch.db"
os.environ["EVENT_QUEUE_DRIVER"] = "inline"

import pytest
from fastapi.testclient import TestClient
from app.db.base import Base
from app.db.session import engine
from app.main import app


@pytest.fixture()
def client():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    with TestClient(app) as test_client:
        yield test_client
    Base.metadata.drop_all(bind=engine)
