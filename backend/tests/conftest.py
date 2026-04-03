from __future__ import annotations

from collections.abc import AsyncGenerator
from typing import Any

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings
from app.core.database import Base, get_db
from app.core.security import Role, create_access_token, hash_password
from app.main import app
from app.models.user import User

# Use a separate test database — append _test suffix
TEST_DATABASE_URL = settings.DATABASE_URL.replace("/crece_v2", "/crece_v2_test")

test_engine = create_async_engine(TEST_DATABASE_URL, echo=False)
test_session_factory = async_sessionmaker(
    test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
    async with test_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(scope="session")
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture(autouse=True)
async def setup_database() -> AsyncGenerator[None, None]:
    """Create all tables before each test and drop them after."""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Provide a clean database session for tests."""
    async with test_session_factory() as session:
        yield session


@pytest.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    """Async HTTP test client."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture
async def admin_user(db_session: AsyncSession) -> User:
    """Create and return an admin user."""
    user = User(
        email="admin@crece.mx",
        hashed_password=hash_password("admin123"),
        full_name="Admin User",
        role=Role.ADMIN,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
async def analyst_user(db_session: AsyncSession) -> User:
    """Create and return an analyst user."""
    user = User(
        email="analyst@crece.mx",
        hashed_password=hash_password("analyst123"),
        full_name="Analyst User",
        role=Role.ANALYST,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
async def viewer_user(db_session: AsyncSession) -> User:
    """Create and return a viewer user."""
    user = User(
        email="viewer@crece.mx",
        hashed_password=hash_password("viewer123"),
        full_name="Viewer User",
        role=Role.VIEWER,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
def admin_token(admin_user: User) -> str:
    """JWT token for admin user."""
    return create_access_token(data={"sub": str(admin_user.id), "role": admin_user.role.value})


@pytest.fixture
def analyst_token(analyst_user: User) -> str:
    return create_access_token(data={"sub": str(analyst_user.id), "role": analyst_user.role.value})


@pytest.fixture
def viewer_token(viewer_user: User) -> str:
    return create_access_token(data={"sub": str(viewer_user.id), "role": viewer_user.role.value})


def auth_headers(token: str) -> dict[str, str]:
    """Helper to build Authorization headers."""
    return {"Authorization": f"Bearer {token}"}
