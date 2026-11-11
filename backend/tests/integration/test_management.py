"""Gestão de usuários, guichês e auditoria."""
from tests.conftest import login


def test_create_and_list_users(client, admin_headers, make_counter):
    counter = make_counter()
    response = client.post(
        "/api/users",
        json={"name": "Maria Souza", "email": "Maria@Lab.test", "password": "Segura123", "role": "ATTENDANT", "counter_ids": [counter]},
        headers=admin_headers,
    )
    assert response.status_code == 201
    assert response.json["email"] == "maria@lab.test"
    assert [c["id"] for c in response.json["counters"]] == [counter]
    listing = client.get("/api/users?search=maria", headers=admin_headers).json
    assert listing["meta"]["total"] == 1
    assert client.post("/api/auth/login", json={"email": "maria@lab.test", "password": "Segura123"}).status_code == 200


def test_duplicate_email_and_weak_password(client, admin_headers):
    payload = {"name": "João", "email": "joao@lab.test", "password": "Segura123", "role": "ATTENDANT"}
    assert client.post("/api/users", json=payload, headers=admin_headers).status_code == 201
    dup = client.post("/api/users", json=payload, headers=admin_headers)
    assert dup.status_code == 409 and dup.json["error"]["code"] == "EMAIL_IN_USE"
    weak = client.post("/api/users", json={**payload, "email": "x@lab.test", "password": "123"}, headers=admin_headers)
    assert weak.status_code == 422


def test_unknown_counter_is_rejected(client, admin_headers):
    response = client.post(
        "/api/users",
        json={"name": "Ana", "email": "ana@lab.test", "password": "Segura123", "role": "ATTENDANT", "counter_ids": [999]},
        headers=admin_headers,
    )
    assert response.status_code == 422


def test_admin_cannot_lock_himself_out(client, admin_headers):
    me = client.get("/api/auth/me", headers=admin_headers).json
    response = client.patch(f"/api/users/{me['id']}", json={"active": False}, headers=admin_headers)
    assert response.status_code == 422
    assert response.json["error"]["code"] in {"SELF_LOCKOUT", "LAST_ADMIN"}


def test_assign_counters(client, admin_headers, make_user, make_counter):
    user = make_user()
    c1, c2 = make_counter(), make_counter()
    response = client.put(f"/api/users/{user['id']}/counters", json={"counter_ids": [c2, c1, c1]}, headers=admin_headers)
    assert response.status_code == 200
    assert sorted(c["id"] for c in response.json["counters"]) == sorted([c1, c2])
    available = client.get("/api/attendant/counters", headers=login(client, user)).json["items"]
    assert len(available) == 2


def test_counters_crud(client, admin_headers):
    created = client.post("/api/counters", json={"name": "Guichê Coleta", "number": 7}, headers=admin_headers)
    assert created.status_code == 201
    dup = client.post("/api/counters", json={"name": "Outro", "number": 7}, headers=admin_headers)
    assert dup.status_code == 409
    updated = client.patch(f"/api/counters/{created.json['id']}", json={"active": False}, headers=admin_headers)
    assert updated.status_code == 200 and updated.json["active"] is False
    assert len(client.get("/api/counters", headers=admin_headers).json["items"]) == 1


def test_cannot_deactivate_counter_in_use(client, admin_headers, attendant):
    response = client.patch(f"/api/counters/{attendant['counter_id']}", json={"active": False}, headers=admin_headers)
    assert response.status_code == 422


def test_force_close_session(client, admin_headers, attendant):
    sessions = client.get("/api/counters/sessions", headers=admin_headers).json["items"]
    assert len(sessions) == 1
    assert client.delete(f"/api/counters/sessions/{sessions[0]['id']}", headers=admin_headers).status_code == 204
    assert client.get("/api/attendant/state", headers=attendant["headers"]).json["session"] is None


def test_audit_log(client, admin_headers, attendant, issue):
    issue("SP")
    client.post("/api/attendant/call-next", headers=attendant["headers"])
    body = client.get("/api/admin/audit-logs?action=TICKET_CALLED", headers=admin_headers).json
    assert body["meta"]["total"] == 1
    entry = body["items"][0]
    assert entry["user"]["id"] == attendant["user"]["id"]
    assert entry["entity"] == "ticket" and entry["details"]["code"] == "261110-SP001"


def test_system_info_and_openapi(client, admin_headers):
    info = client.get("/api/admin/system", headers=admin_headers).json
    assert info["database"]["engine"] == "MySQL"
    spec = client.get("/api/docs/openapi.json").json
    assert spec["openapi"].startswith("3.")
    assert "/api/attendant/call-next" in spec["paths"]
    assert "LoginRequest" in spec["components"]["schemas"]
