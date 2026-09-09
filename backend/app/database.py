from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import get_settings


class Base(DeclarativeBase):
    pass


def _engine_options(url: str) -> dict:
    if url.startswith("sqlite"):
        return {"connect_args": {"check_same_thread": False}}
    # A pooled connection can be closed by the server or a network device while
    # it sits idle. Without pre-ping the next request gets the dead one and
    # fails for a reason that has nothing to do with the request.
    return {"pool_pre_ping": True, "pool_size": 5, "max_overflow": 5}


settings = get_settings()
engine = create_engine(settings.database_url, **_engine_options(settings.database_url))
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


async def get_db() -> Generator[Session, None, None]:
    with SessionLocal() as session:
        yield session
