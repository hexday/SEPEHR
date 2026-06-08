"""
SEPEHR Backend — Test Suite: Authentication & Messenger
"""

import asyncio
import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.main import app
from app.domain.models.all import Base
from app.infrastructure.database.session import get_db

# ── Test Database ─────────────────────────────────────────────────────────────

TEST_DB_URL = "postgresql+asyncpg://sepehr_test:testpassword@localhost:5432/sepehr_test"

test_engine = create_async_engine(TEST_DB_URL, echo=False)
TestSessionFactory = async_sessionmaker(test_engine, expire_on_commit=False)


async def override_get_db():
    async with TestSessionFactory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session", autouse=True)
async def create_tables():
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
async def client():
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac


# ── Auth Tests ────────────────────────────────────────────────────────────────

class TestAuthRegister:
    async def test_register_success(self, client: AsyncClient):
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "username": "testuser1",
                "password": "securepassword123",
                "display_name": "Test User",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"

    async def test_register_duplicate_username(self, client: AsyncClient):
        # First registration
        await client.post(
            "/api/v1/auth/register",
            json={
                "username": "duplicate_user",
                "password": "securepassword123",
                "display_name": "Duplicate User",
            },
        )
        # Second registration with same username
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "username": "duplicate_user",
                "password": "anotherpassword",
                "display_name": "Another User",
            },
        )
        assert response.status_code == 409
        assert response.json()["error"] == "USERNAME_EXISTS"

    async def test_register_short_password(self, client: AsyncClient):
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "username": "validuser",
                "password": "short",
                "display_name": "Valid User",
            },
        )
        assert response.status_code == 422

    async def test_register_invalid_username(self, client: AsyncClient):
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "username": "invalid user!",
                "password": "securepassword123",
                "display_name": "Invalid",
            },
        )
        assert response.status_code == 422


class TestAuthLogin:
    async def test_login_success(self, client: AsyncClient):
        # Register first
        await client.post(
            "/api/v1/auth/register",
            json={
                "username": "loginuser",
                "password": "mypassword123",
                "display_name": "Login User",
            },
        )
        # Login
        response = await client.post(
            "/api/v1/auth/login",
            json={"username": "loginuser", "password": "mypassword123"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data

    async def test_login_wrong_password(self, client: AsyncClient):
        await client.post(
            "/api/v1/auth/register",
            json={
                "username": "loginuser2",
                "password": "correct_password",
                "display_name": "Login User 2",
            },
        )
        response = await client.post(
            "/api/v1/auth/login",
            json={"username": "loginuser2", "password": "wrong_password"},
        )
        assert response.status_code == 401
        assert response.json()["error"] == "INVALID_CREDENTIALS"

    async def test_login_nonexistent_user(self, client: AsyncClient):
        response = await client.post(
            "/api/v1/auth/login",
            json={"username": "doesnotexist", "password": "anypassword"},
        )
        assert response.status_code == 401

    async def test_get_me_authenticated(self, client: AsyncClient):
        reg = await client.post(
            "/api/v1/auth/register",
            json={
                "username": "meuser",
                "password": "mypassword123",
                "display_name": "Me User",
            },
        )
        token = reg.json()["access_token"]
        response = await client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["username"] == "meuser"
        assert data["display_name"] == "Me User"

    async def test_get_me_unauthenticated(self, client: AsyncClient):
        response = await client.get("/api/v1/auth/me")
        assert response.status_code == 401

    async def test_token_refresh(self, client: AsyncClient):
        reg = await client.post(
            "/api/v1/auth/register",
            json={
                "username": "refreshuser",
                "password": "mypassword123",
                "display_name": "Refresh User",
            },
        )
        refresh_token = reg.json()["refresh_token"]
        response = await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": refresh_token},
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["access_token"] != reg.json()["access_token"]  # New token

    async def test_logout(self, client: AsyncClient):
        reg = await client.post(
            "/api/v1/auth/register",
            json={
                "username": "logoutuser",
                "password": "mypassword123",
                "display_name": "Logout User",
            },
        )
        tokens = reg.json()
        # Logout
        response = await client.post(
            "/api/v1/auth/logout",
            json={"refresh_token": tokens["refresh_token"]},
            headers={"Authorization": f"Bearer {tokens['access_token']}"},
        )
        assert response.status_code == 204
        # Refresh should fail now
        response = await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": tokens["refresh_token"]},
        )
        assert response.status_code == 401


# ── Messenger Tests ───────────────────────────────────────────────────────────

class TestMessenger:
    async def _register_and_get_token(
        self, client: AsyncClient, username: str, display_name: str
    ) -> str:
        reg = await client.post(
            "/api/v1/auth/register",
            json={
                "username": username,
                "password": "testpassword123",
                "display_name": display_name,
            },
        )
        return reg.json()["access_token"]

    async def test_create_direct_conversation(self, client: AsyncClient):
        token_a = await self._register_and_get_token(client, "conv_user_a", "User A")
        await self._register_and_get_token(client, "conv_user_b", "User B")

        response = await client.post(
            "/api/v1/messenger/conversations/direct",
            json={"recipient_username": "conv_user_b"},
            headers={"Authorization": f"Bearer {token_a}"},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["type"] == "direct"

    async def test_create_group_conversation(self, client: AsyncClient):
        token = await self._register_and_get_token(client, "group_admin", "Group Admin")
        await self._register_and_get_token(client, "group_member_1", "Member 1")
        await self._register_and_get_token(client, "group_member_2", "Member 2")

        response = await client.post(
            "/api/v1/messenger/conversations/group",
            json={
                "name": "Emergency Team",
                "member_usernames": ["group_member_1", "group_member_2"],
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["type"] == "group"
        assert data["name"] == "Emergency Team"

    async def test_send_message_and_retrieve(self, client: AsyncClient):
        token_a = await self._register_and_get_token(client, "msg_sender_a", "Sender A")
        await self._register_and_get_token(client, "msg_receiver_b", "Receiver B")

        # Create conversation
        conv_resp = await client.post(
            "/api/v1/messenger/conversations/direct",
            json={"recipient_username": "msg_receiver_b"},
            headers={"Authorization": f"Bearer {token_a}"},
        )
        conv_id = conv_resp.json()["id"]

        # Send message
        send_resp = await client.post(
            f"/api/v1/messenger/conversations/{conv_id}/messages/text",
            json={
                "content_encrypted": "dGVzdCBtZXNzYWdl",  # base64 "test message"
                "iv": "a" * 32,
                "content_preview": "test message",
            },
            headers={"Authorization": f"Bearer {token_a}"},
        )
        assert send_resp.status_code == 201

        # Retrieve messages
        msgs_resp = await client.get(
            f"/api/v1/messenger/conversations/{conv_id}/messages",
            headers={"Authorization": f"Bearer {token_a}"},
        )
        assert msgs_resp.status_code == 200
        msgs = msgs_resp.json()["messages"]
        assert len(msgs) >= 1
        assert msgs[-1]["content_preview"] == "test message"

    async def test_cannot_send_to_non_member_conversation(self, client: AsyncClient):
        token_a = await self._register_and_get_token(client, "member_aa", "Member AA")
        await self._register_and_get_token(client, "member_bb", "Member BB")
        token_outsider = await self._register_and_get_token(client, "outsider_cc", "Outsider CC")

        conv_resp = await client.post(
            "/api/v1/messenger/conversations/direct",
            json={"recipient_username": "member_bb"},
            headers={"Authorization": f"Bearer {token_a}"},
        )
        conv_id = conv_resp.json()["id"]

        response = await client.post(
            f"/api/v1/messenger/conversations/{conv_id}/messages/text",
            json={
                "content_encrypted": "dGVzdA==",
                "iv": "b" * 32,
                "content_preview": "intruder",
            },
            headers={"Authorization": f"Bearer {token_outsider}"},
        )
        assert response.status_code == 403


# ── Health Check ─────────────────────────────────────────────────────────────

class TestHealth:
    async def test_health_check(self, client: AsyncClient):
        response = await client.get("/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["service"] == "SEPEHR"
