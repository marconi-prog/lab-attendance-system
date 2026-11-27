"""O simulador respeita a mesma regra de concluir serviços iniciados antes das17h."""
from datetime import date, datetime, time

import app.attendance_simulation as sim
from app.models import TicketType


def test_simulated_service_started_before_closing_may_finish_after(monkeypatch):
    durations = {TicketType.SP:1200, TicketType.SG:480, TicketType.SE:300}
    monkeypatch.setattr(sim,'service_seconds',lambda kind,rng: durations[kind])
    report = sim.simulate_day(tickets=20,seed=42,day=date(2026,11,27),counters=1,
                              open_time=time(16,50),close_time=time(17),last_arrival_time=time(16,51))
    closing = datetime.fromisoformat('2026-11-27T17:00:00-03:00')
    completed = [t for t in report['tickets'] if t['status']=='ATENDIDA']
    assert any(datetime.fromisoformat(t['finished_at'])>closing for t in completed)
    assert all(datetime.fromisoformat(t['first_called_at'])<closing for t in report['tickets'] if t['calls'])
    assert report['totals']['discarded']>0
    counter = report['by_counter'][0]
    assert 0 <= counter['utilization_percentage'] <= 100
    assert report['totals']['utilization_basis_seconds'] > 10*60
