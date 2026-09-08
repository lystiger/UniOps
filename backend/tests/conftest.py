import asyncio
import json
from pathlib import Path

import httpx
import pytest
from app.database import Base, get_db
from app.integrations.easybooks.sync import FixtureBundle
from app.main import app
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


class ApiClient:
    def request(self, method, path, **kwargs):
        async def send():
            transport = httpx.ASGITransport(app=app)
            async with httpx.AsyncClient(
                transport=transport, base_url="http://testserver"
            ) as client:
                return await client.request(method, path, **kwargs)

        return asyncio.run(send())

    def get(self, path, **kwargs):
        return self.request("GET", path, **kwargs)

    def post(self, path, **kwargs):
        return self.request("POST", path, **kwargs)

    def patch(self, path, **kwargs):
        return self.request("PATCH", path, **kwargs)

    def delete(self, path, **kwargs):
        return self.request("DELETE", path, **kwargs)


@pytest.fixture
def session(tmp_path):
    engine = create_engine(
        f"sqlite:///{tmp_path / 'test.db'}", connect_args={"check_same_thread": False}
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    with factory() as value:
        yield value
    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture
def client(session):
    factory = sessionmaker(bind=session.get_bind(), expire_on_commit=False)

    async def override_db():
        with factory() as request_session:
            yield request_session

    app.dependency_overrides[get_db] = override_db
    yield ApiClient()
    app.dependency_overrides.clear()


@pytest.fixture
def fixture_payload():
    path = Path(__file__).parent / "fixtures" / "easybooks_bundle.json"
    return json.loads(path.read_text())


@pytest.fixture
def fixture_bundle(fixture_payload):
    return FixtureBundle.from_dict(fixture_payload)
