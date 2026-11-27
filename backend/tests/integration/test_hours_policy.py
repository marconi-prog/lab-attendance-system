"""Edital 5.1: nenhuma emissão antes das 07h, inclusive com configuração antiga."""
from datetime import time

import pytest
from sqlalchemy import func, select

from app.extensions import db
from app.models import Ticket
from app.services.business_hours import BusinessHours


@pytest.mark.parametrize('hhmm,allowed', [('06:00',False),('06:59',False),('07:00',True),('16:59',True),('17:00',False)])
def test_issue_and_call_share_business_window(app, client, clock, hhmm, allowed):
    clock.set(f'2026-11-10 {hhmm}')
    response = client.post('/api/tickets', json={'type':'SG'})
    assert response.status_code == (201 if allowed else 422)
    if not allowed:
        assert response.json['error']['code'] == 'OUTSIDE_BUSINESS_HOURS'
        with app.app_context():
            assert db.session.scalar(select(func.count(Ticket.id))) == 0


def test_legacy_issuance_setting_cannot_open_before_business_hours(app, client, clock, monkeypatch):
    monkeypatch.setitem(app.config, 'TICKET_ISSUE_OPEN_TIME', time(6))
    clock.set('2026-11-10 06:59')
    assert client.post('/api/tickets', json={'type':'SP'}).status_code == 422
    with app.app_context():
        assert BusinessHours.describe()['issue_open'] == '07:00'
