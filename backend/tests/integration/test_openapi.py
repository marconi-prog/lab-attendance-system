"""Contrato OpenAPI: o documento é válido e as respostas reais seguem os schemas publicados."""
import pytest
from jsonschema import Draft202012Validator
from openapi_spec_validator import validate as validate_spec
from referencing import Registry, Resource

from app.models import UserRole
from app.routes.registry import REGISTRY
from tests.conftest import PASSWORD, login


@pytest.fixture()
def spec(client):
    return client.get("/api/docs/openapi.json").json


def test_spec_is_valid_openapi(spec):
    validate_spec(spec)


def test_every_operation_documents_success_response(spec):
    for path, item in spec["paths"].items():
        for method, op in item.items():
            ok = [code for code in op["responses"] if code.startswith("2")]
            assert ok, f"{method} {path} sem resposta de sucesso"
            for code in ok:
                if code != "204":
                    assert "content" in op["responses"][code], f"{method} {path} sem schema de resposta"


def test_every_registered_route_is_documented(spec):
    for route in REGISTRY:
        for method in route.methods:
            assert method.lower() in spec["paths"][route.path]


def test_docs_page_is_served(client):
    html = client.get("/api/docs").get_data(as_text=True)
    assert "/api/docs/openapi.json" in html and "integrity=" in html


# ------------------------------------------------------------ contrato real
def _resolve(spec, schema):
    while "$ref" in schema:
        schema = spec["components"]["schemas"][schema["$ref"].rsplit("/", 1)[1]]
    return schema


def _undocumented_keys(spec, schema, data, where="$"):
    """Campos presentes na resposta e ausentes do schema (o JSON Schema por si só os aceitaria)."""
    schema = _resolve(spec, schema)
    problems = []
    if "anyOf" in schema:
        options = [o for o in schema["anyOf"] if _resolve(spec, o).get("type") != "null" or data is None]
        if data is None:
            return []
        return min((_undocumented_keys(spec, o, data, where) for o in options), key=len, default=[])
    if isinstance(data, dict) and "properties" in schema:
        for key, value in data.items():
            if key not in schema["properties"]:
                problems.append(f"{where}.{key}")
            else:
                problems += _undocumented_keys(spec, schema["properties"][key], value, f"{where}.{key}")
    elif isinstance(data, list) and "items" in schema:
        for i, value in enumerate(data[:3]):
            problems += _undocumented_keys(spec, schema["items"], value, f"{where}[{i}]")
    return problems


def assert_contract(spec, response, path, method="get"):
    op = spec["paths"][path][method]
    status = str(response.status_code)
    assert status in op["responses"], f"{method.upper()} {path}: status {status} não documentado ({response.json})"
    if status == "204":
        return
    schema = op["responses"][status]["content"]["application/json"]["schema"]
    registry = Registry().with_resource("urn:spec", Resource.opaque(spec))
    validator = Draft202012Validator(
        {"$ref": "urn:spec#" + schema["$ref"][1:]} if "$ref" in schema else schema, registry=registry
    )
    errors = sorted(validator.iter_errors(response.json), key=lambda e: e.path)
    assert not errors, f"{method.upper()} {path}: " + "; ".join(f"{list(e.path)}: {e.message}" for e in errors[:5])
    extra = _undocumented_keys(spec, schema, response.json)
    assert not extra, f"{method.upper()} {path}: campos não documentados {extra}"


def test_responses_match_documented_schemas(client, spec, make_user, make_counter, issue, clock):
    admin = login(client, make_user(UserRole.ADMIN))
    counter_id = make_counter()
    attendant_user = make_user(UserRole.ATTENDANT, [counter_id])
    att = login(client, attendant_user)

    c = lambda r, p, m="get": assert_contract(spec, r, p, m)  # noqa: E731

    c(client.get("/api/health"), "/api/health")
    c(client.get("/api/tickets/types"), "/api/tickets/types")
    c(client.post("/api/tickets", json={"type": "SP"}), "/api/tickets", "post")
    c(client.post("/api/tickets", json={"type": "XX"}), "/api/tickets", "post")  # 422
    for t in ["SG", "SE", "SG"]:
        issue(t)

    c(client.post("/api/auth/login", json={"email": attendant_user["email"], "password": PASSWORD}), "/api/auth/login", "post")
    c(client.post("/api/auth/login", json={"email": attendant_user["email"], "password": "errada"}), "/api/auth/login", "post")
    c(client.get("/api/auth/me", headers=att), "/api/auth/me")
    c(client.get("/api/attendant/counters", headers=att), "/api/attendant/counters")
    c(client.get("/api/attendant/state", headers=att), "/api/attendant/state")  # sem sessão
    c(client.post("/api/attendant/session", json={"counter_id": counter_id}, headers=att), "/api/attendant/session", "post")

    first = client.post("/api/attendant/call-next", headers=att)
    c(first, "/api/attendant/call-next", "post")
    tid = first.json["ticket"]["id"]
    c(client.post("/api/attendant/call-next", headers=att), "/api/attendant/call-next", "post")  # 409
    c(client.get("/api/attendant/state", headers=att), "/api/attendant/state")  # com senha atual
    c(client.post(f"/api/attendant/tickets/{tid}/start", headers=att), "/api/attendant/tickets/{ticket_id}/start", "post")
    clock.advance(minutes=3)
    c(client.post(f"/api/attendant/tickets/{tid}/finish", headers=att), "/api/attendant/tickets/{ticket_id}/finish", "post")

    second = client.post("/api/attendant/call-next", headers=att).json["ticket"]["id"]
    c(client.post(f"/api/attendant/tickets/{second}/no-show", headers=att), "/api/attendant/tickets/{ticket_id}/no-show", "post")  # 422
    c(client.post(f"/api/attendant/tickets/{second}/recall", headers=att), "/api/attendant/tickets/{ticket_id}/recall", "post")
    c(client.post(f"/api/attendant/tickets/{second}/no-show", headers=att), "/api/attendant/tickets/{ticket_id}/no-show", "post")
    c(client.get("/api/attendant/state", headers=att), "/api/attendant/state")

    c(client.get("/api/panel"), "/api/panel")
    c(client.get("/api/tickets", headers=admin), "/api/tickets")
    c(client.get(f"/api/tickets/{tid}", headers=admin), "/api/tickets/{ticket_id}")
    c(client.get("/api/users", headers=admin), "/api/users")
    c(client.get("/api/users", headers=att), "/api/users")  # 403
    c(client.get("/api/users"), "/api/users")  # 401
    c(client.get("/api/counters", headers=admin), "/api/counters")
    c(client.get("/api/counters/sessions", headers=admin), "/api/counters/sessions")
    c(client.get("/api/reports/summary", headers=admin), "/api/reports/summary")
    c(client.get("/api/reports/daily", headers=admin), "/api/reports/daily")
    c(client.get("/api/reports/monthly", headers=admin), "/api/reports/monthly")
    c(client.get("/api/reports/attendances", headers=admin), "/api/reports/attendances")
    c(client.get("/api/admin/dashboard", headers=admin), "/api/admin/dashboard")
    c(client.get("/api/admin/system", headers=admin), "/api/admin/system")
    c(client.get("/api/admin/audit-logs", headers=admin), "/api/admin/audit-logs")
    c(client.post("/api/admin/close-day", headers=admin), "/api/admin/close-day", "post")
