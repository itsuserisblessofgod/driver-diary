import os

os.environ["DATABASE_URL"] = "sqlite://"  # tests never touch PostgreSQL
os.environ["APP_TZ"] = "Etc/GMT-5"  # fixed UTC+5, independent of the system tz database

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool


@pytest.fixture
def client():
    from app.db import Base
    from app.main import app, get_db

    engine = create_engine("sqlite://", poolclass=StaticPool, connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    Session = sessionmaker(engine, expire_on_commit=False)

    def override():
        with Session() as db:
            yield db

    app.dependency_overrides[get_db] = override
    yield TestClient(app)
    app.dependency_overrides.clear()
