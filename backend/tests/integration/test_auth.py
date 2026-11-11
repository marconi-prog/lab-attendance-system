"""Autenticação e autorização."""
import pytest
from sqlalchemy import select

from app.extensions import db
from app.models import AuditLog, User, UserRole
from tests.conftest import PASSWORD, login


def test_login_returns_token_pair(client, make_user):
    user = make_user(UserRole.ADMIN)
    response = client.post("/api/auth/login", json={"email": user["email"], "password": PASSWORD})
    assert response.status_code == 200
    body = response.json
    assert body["access_token"] and body["refresh_token"] and body["token_type"] == "Bearer"
    assert body["user"]["role"] == "ADMIN"
    assert "password_hash" not in body["user"]


def test_login_email_is_case_insensitive(client, make_user):
    user = make_user()
    assert client.post("/api/auth/login", json={"email": user["email"].upper(), "password": PASSWORD}).status_code == 200


@pytest.mark.parametrize("email, password", [("user@lab.test", "errada123"), ("naoexiste@lab.test", PASSWORD)])
def test_invalid_credentials(client, make_user, email, password):
    make_user()
    response = client.post("/api/auth/login", json={"email": email, "password": password})
    assert response.status_code == 401
    assert response.json["error"]["code"] == "INVALID_CREDENTIALS"


def test_inactive_user_cannot_login(client, make_user):
    user = make_user(active=False)
    assert client.post("/api/auth/login", json={"email": user["email"], "password": PASSWORD}).status_code == 401


def test_password_is_hashed(app, make_user):
    user = make_user()
    with app.app_context():
        stored = db.session.get(User, user["id"]).password_hash
        assert PASSWORD not in stored
        assert stored.startswith(("scrypt:", "pbkdf2:"))


def test_me_and_missing_token(client, make_user):
    headers = login(client, make_user())
    assert client.get("/api/auth/me", headers=headers).json["role"] == "ATTENDANT"
    response = client.get("/api/auth/me")
    assert response.status_code == 401
    assert response.json["error"]["code"] == "UNAUTHORIZED"


def test_invalid_token(client):
    response = client.get("/api/auth/me", headers={"Authorization": "Bearer abc.def.ghi"})
    assert response.status_code in (401, 422)
    assert "error" in response.json


def test_refresh_flow(client, make_user):
    user = make_user()
    tokens = client.post("/api/auth/login", json={"email": user["email"], "password": PASSWORD}).json
    refreshed = client.post("/api/auth/refresh", headers={"Authorization": f"Bearer {tokens['refresh_token']}"})
    assert refreshed.status_code == 200
    new_headers = {"Authorization": f"Bearer {refreshed.json['access_token']}"}
    assert client.get("/api/auth/me", headers=new_headers).status_code == 200
    # access token não serve como refresh token
    wrong = client.post("/api/auth/refresh", headers={"Authorization": f"Bearer {tokens['access_token']}"})
    assert wrong.status_code in (401, 422)


def test_logout_revokes_tokens(client, make_user):
    user = make_user()
    tokens = client.post("/api/auth/login", json={"email": user["email"], "password": PASSWORD}).json
    headers = {"Authorization": f"Bearer {tokens['access_token']}"}
    assert client.post("/api/auth/logout", json={"refresh_token": tokens["refresh_token"]}, headers=headers).status_code == 204
    revoked = client.get("/api/auth/me", headers=headers)
    assert revoked.status_code == 401 and revoked.json["error"]["code"] == "TOKEN_REVOKED"
    assert client.post("/api/auth/refresh", headers={"Authorization": f"Bearer {tokens['refresh_token']}"}).status_code == 401


def test_deactivated_user_loses_access_immediately(client, make_user, admin_headers):
    user = make_user()
    headers = login(client, user)
    client.patch(f"/api/users/{user['id']}", json={"active": False}, headers=admin_headers)
    response = client.get("/api/auth/me", headers=headers)
    assert response.status_code == 401


def test_change_password(client, make_user):
    user = make_user()
    headers = login(client, user)
    weak = client.put("/api/auth/password", json={"current_password": PASSWORD, "new_password": "abcdefgh"}, headers=headers)
    assert weak.status_code == 422
    ok = client.put("/api/auth/password", json={"current_password": PASSWORD, "new_password": "NovaSenha99"}, headers=headers)
    assert ok.status_code == 204
    assert client.post("/api/auth/login", json={"email": user["email"], "password": "NovaSenha99"}).status_code == 200


def test_login_is_audited_without_password(client, make_user, app):
    user = make_user()
    login(client, user)
    with app.app_context():
        log = db.session.scalar(select(AuditLog).where(AuditLog.action == "LOGIN"))
        assert log.user_id == user["id"]
        assert PASSWORD not in str(log.details)


# ----------------------------------------------------------------- perfis
ADMIN_ONLY = [
    ("get", "/api/users"),
    ("post", "/api/users"),
    ("get", "/api/reports/summary"),
    ("get", "/api/reports/attendances"),
    ("get", "/api/admin/dashboard"),
    ("get", "/api/admin/audit-logs"),
    ("get", "/api/admin/system"),
    ("post", "/api/counters"),
    ("post", "/api/admin/close-day"),
]
ATTENDANT_ONLY = [
    ("post", "/api/attendant/call-next"),
    ("get", "/api/attendant/state"),
    ("post", "/api/attendant/session"),
]


@pytest.mark.parametrize("method, url", ADMIN_ONLY + ATTENDANT_ONLY)
def test_anonymous_is_rejected(client, method, url):
    assert getattr(client, method)(url, json={}).status_code == 401


@pytest.mark.parametrize("method, url", ADMIN_ONLY)
def test_attendant_cannot_access_admin(client, make_user, method, url):
    headers = login(client, make_user(UserRole.ATTENDANT))
    response = getattr(client, method)(url, json={}, headers=headers)
    assert response.status_code == 403
    assert response.json["error"]["code"] == "FORBIDDEN"


@pytest.mark.parametrize("method, url", ATTENDANT_ONLY)
def test_admin_cannot_operate_counter(client, admin_headers, method, url):
    assert getattr(client, method)(url, json={}, headers=admin_headers).status_code == 403


def test_public_endpoints(client):
    assert client.get("/api/health").status_code == 200
    assert client.get("/api/panel").status_code == 200
    assert client.get("/api/tickets/types").status_code == 200
    assert client.get("/api/docs/openapi.json").status_code == 200
