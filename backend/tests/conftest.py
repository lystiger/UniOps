import asyncio
import json
import os
from pathlib import Path

import httpx
import pytest
from app.config import Settings
from app.database import Base, get_db
from app.integrations.easybooks.sync import FixtureBundle
from app.main import app
from app.models import UserRole
from app.services import auth
from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.orm import sessionmaker

# Read before the autouse fixture below strips UNIOPS_* from the environment.
# Point it at a PostgreSQL URL to run the same suite against the deploy target.
TEST_DATABASE_URL = os.environ.get("UNIOPS_TEST_DATABASE_URL")
NORMAL_DATABASE_URL = os.environ.get("UNIOPS_DATABASE_URL")


def validate_test_database_url(
    test_url_str: str | None, normal_url_str: str | None
) -> None:
    if not test_url_str:
        return
    try:
        test_url = make_url(test_url_str)
    except Exception as exc:
        raise pytest.UsageError(
            f"Invalid UNIOPS_TEST_DATABASE_URL '{test_url_str}': {exc}"
        ) from exc

    if normal_url_str:
        try:
            normal_url = make_url(normal_url_str)
            if (
                test_url.host == normal_url.host
                and test_url.port == normal_url.port
                and test_url.database == normal_url.database
            ):
                raise pytest.UsageError(
                    f"Refusing to run tests: UNIOPS_TEST_DATABASE_URL matches UNIOPS_DATABASE_URL "
                    f"('{test_url.database}'). The test suite calls Base.metadata.drop_all(), "
                    "which would destroy development or production data. "
                    "Use a dedicated test database (e.g. 'uniops_test')."
                )
        except pytest.UsageError:
            raise
        except Exception:
            pass

    backend_name = test_url.get_backend_name()
    db_name = (test_url.database or "").strip("/").lower()
    if backend_name in ("postgresql", "postgres"):
        if db_name in ("uniops", "postgres", "production", "prod") or "test" not in db_name:
            raise pytest.UsageError(
                f"Refusing to run tests against database '{test_url.database}'. "
                "UNIOPS_TEST_DATABASE_URL must point to a dedicated test database containing "
                "'test' (e.g. 'uniops_test') because test setup drops all tables."
            )


validate_test_database_url(TEST_DATABASE_URL, NORMAL_DATABASE_URL)


@pytest.fixture(autouse=True)
def isolate_settings_from_local_env(monkeypatch):
    """Keep an operator's real .env out of the test suite.

    Settings reads .env by default, so a populated local file silently changed
    test outcomes—an enabled live mode made a "live reads are disabled" case fail.
    Tests must depend only on the values they pass in.
    """
    monkeypatch.setitem(Settings.model_config, "env_file", None)
    for key in [name for name in os.environ if name.startswith("UNIOPS_")]:
        monkeypatch.delenv(key, raising=False)


class ApiClient:
    """A caller that keeps its cookies, so a signed-in session survives calls."""

    def __init__(self):
        self.cookies = httpx.Cookies()

    def request(self, method, path, **kwargs):
        async def send():
            transport = httpx.ASGITransport(app=app)
            async with httpx.AsyncClient(
                transport=transport, base_url="http://testserver", cookies=self.cookies
            ) as client:
                response = await client.request(method, path, **kwargs)
                self.cookies.extract_cookies(response)
                return response

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
    if TEST_DATABASE_URL:
        engine = create_engine(TEST_DATABASE_URL)
        # One shared database across a sequential run, so each test starts from
        # the same clean schema the SQLite temporary file gives for free.
        Base.metadata.drop_all(engine)
    else:
        engine = create_engine(
            f"sqlite:///{tmp_path / 'test.db'}", connect_args={"check_same_thread": False}
        )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    with factory() as value:
        yield value
    Base.metadata.drop_all(engine)
    engine.dispose()


# Long enough to satisfy the real password rule, so the tests exercise it.
ACCOUNT_PASSWORDS = {
    "admin": "admin-password-01",
    "office": "office-password-01",
    "factory": "factory-password-01",
}


@pytest.fixture
def accounts(session):
    """One account per role, so route guards are tested against all three."""
    for username, role in [
        ("admin", UserRole.ADMIN),
        ("office", UserRole.OFFICE),
        ("factory", UserRole.FACTORY_READ),
    ]:
        auth.create_user(
            session, username=username, password=ACCOUNT_PASSWORDS[username], role=role
        )
    return ACCOUNT_PASSWORDS


@pytest.fixture
def client_factory(session, accounts):
    factory = sessionmaker(bind=session.get_bind(), expire_on_commit=False)

    async def override_db():
        with factory() as request_session:
            yield request_session

    app.dependency_overrides[get_db] = override_db

    def build(username: str | None = None) -> ApiClient:
        caller = ApiClient()
        if username is not None:
            response = caller.post(
                "/api/auth/login",
                json={"username": username, "password": accounts[username]},
            )
            assert response.status_code == 200, response.text
        return caller

    yield build
    app.dependency_overrides.clear()


@pytest.fixture
def client(client_factory):
    """Signed in as admin. Most tests are about the route, not about the guard."""
    return client_factory("admin")


@pytest.fixture
def office_client(client_factory):
    return client_factory("office")


@pytest.fixture
def factory_client(client_factory):
    return client_factory("factory")


@pytest.fixture
def anonymous_client(client_factory):
    return client_factory()


@pytest.fixture
def fixture_payload():
    path = Path(__file__).parent / "fixtures" / "easybooks_bundle.json"
    return json.loads(path.read_text())


@pytest.fixture
def fixture_bundle(fixture_payload):
    return FixtureBundle.from_dict(fixture_payload)
