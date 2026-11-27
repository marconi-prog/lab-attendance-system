"""API v1 documentada e aliases legados com as mesmas regras de segurança."""
from openapi_spec_validator import validate

from app.models import UserRole
from tests.conftest import login


def test_versioned_health_and_documentation(client):
    assert client.get('/api/v1/health').status_code == 200
    spec = client.get('/api/v1/docs/openapi.json').json
    assert '/api/v1/tickets' in spec['paths']
    assert '/api/tickets' in spec['paths']
    ids = [operation['operationId'] for path in spec['paths'].values() for operation in path.values()]
    assert len(ids) == len(set(ids))
    validate(spec)


def test_versioned_emission_uses_same_daily_sequence_as_legacy(client):
    first = client.post('/api/v1/tickets',json={'type':'SG'})
    second = client.post('/api/tickets',json={'type':'SG'})
    assert first.status_code == second.status_code == 201
    assert first.json['ticket']['short_code'] == 'SG001'
    assert second.json['ticket']['short_code'] == 'SG002'


def test_versioned_routes_keep_authorization(client, make_user):
    assert client.get('/api/v1/attendant/state').status_code == 401
    ordinary = login(client, make_user(UserRole.ATTENDANT))
    assert client.get('/api/v1/admin/dashboard',headers=ordinary).status_code == 403
    manager = login(client, make_user(UserRole.ADMIN))
    assert client.get('/api/v1/admin/dashboard',headers=manager).status_code == 200
