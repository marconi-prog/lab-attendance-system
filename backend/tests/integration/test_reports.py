"""Relatórios calculados a partir do banco."""


def run_day(client, attendant, issue, clock):
    """Cenário: 3 SP, 2 SE, 2 SG emitidas; 4 atendidas, 1 não compareceu, 2 aguardando."""
    for t in ["SP", "SP", "SP", "SE", "SE", "SG", "SG"]:
        issue(t)
    h = attendant["headers"]
    durations = [60, 120, 180, 240]  # SP001, SE001, SP002, SE002
    for seconds in durations:
        ticket_id = client.post("/api/attendant/call-next", headers=h).json["ticket"]["id"]
        client.post(f"/api/attendant/tickets/{ticket_id}/start", headers=h)
        clock.advance(seconds=seconds)
        client.post(f"/api/attendant/tickets/{ticket_id}/finish", headers=h)
    # SP003: não compareceu
    ticket_id = client.post("/api/attendant/call-next", headers=h).json["ticket"]["id"]
    client.post(f"/api/attendant/tickets/{ticket_id}/recall", headers=h)
    client.post(f"/api/attendant/tickets/{ticket_id}/no-show", headers=h)


def test_summary(client, attendant, issue, clock, admin_headers):
    run_day(client, attendant, issue, clock)
    report = client.get("/api/reports/summary?start_date=2026-11-10&end_date=2026-11-10", headers=admin_headers).json
    totals = report["totals"]
    assert totals["issued"] == 7
    assert totals["attended"] == 4
    assert totals["no_show"] == 1
    assert totals["not_attended"] == 1
    assert totals["pending"] == 2
    assert totals["avg_attendance_seconds"] == 150.0
    by_type = {row["type"]: row for row in report["by_type"]}
    assert by_type["SP"]["issued"] == 3 and by_type["SP"]["attended"] == 2 and by_type["SP"]["no_show"] == 1
    assert by_type["SP"]["avg_attendance_seconds"] == 120.0  # (60 + 180) / 2
    assert by_type["SE"]["avg_attendance_seconds"] == 180.0  # (120 + 240) / 2
    assert by_type["SG"]["attended"] == 0 and by_type["SG"]["avg_attendance_seconds"] is None
    assert report["by_attendant"][0]["attended"] == 4
    assert report["by_counter"][0]["counter_id"] == attendant["counter_id"]


def test_summary_filtered_by_category(client, attendant, issue, clock, admin_headers):
    run_day(client, attendant, issue, clock)
    report = client.get("/api/reports/summary?start_date=2026-11-10&end_date=2026-11-10&type=SE", headers=admin_headers).json
    assert report["totals"]["issued"] == 2
    assert [row["type"] for row in report["by_type"]] == ["SE"]


def test_period_filter_excludes_other_days(client, attendant, issue, clock, admin_headers):
    run_day(client, attendant, issue, clock)
    report = client.get("/api/reports/summary?start_date=2026-11-11&end_date=2026-11-30", headers=admin_headers).json
    assert report["totals"]["issued"] == 0


def test_daily_and_monthly(client, attendant, issue, clock, admin_headers):
    run_day(client, attendant, issue, clock)
    daily = client.get("/api/reports/daily?date=2026-11-10", headers=admin_headers).json
    assert daily["totals"]["issued"] == 7
    assert daily["by_hour"] == [{"hour": 9, "issued": 7}]
    monthly = client.get("/api/reports/monthly?month=2026-11", headers=admin_headers).json
    assert monthly["month"] == "2026-11"
    assert len(monthly["by_day"]) == 30
    day10 = next(d for d in monthly["by_day"] if d["date"] == "2026-11-10")
    assert day10 == {"date": "2026-11-10", "issued": 7, "attended": 4, "not_attended": 1, "avg_attendance_seconds": 150.0}


def test_history(client, attendant, issue, clock, admin_headers):
    run_day(client, attendant, issue, clock)
    body = client.get("/api/reports/attendances?start_date=2026-11-10&end_date=2026-11-10&status=ATENDIDA", headers=admin_headers).json
    assert body["meta"]["total"] == 4
    row = body["items"][-1]
    assert row["code"] == "261110-SP001"
    assert row["attendant"]["id"] == attendant["user"]["id"]
    assert row["counter"]["id"] == attendant["counter_id"]
    for field in ("issued_at", "first_called_at", "started_at", "finished_at"):
        assert row[field].endswith("-03:00")
    assert row["duration_seconds"] == 60


def test_invalid_period(client, admin_headers):
    response = client.get("/api/reports/summary?start_date=2026-11-10&end_date=2026-11-01", headers=admin_headers)
    assert response.status_code == 422


def test_dashboard(client, attendant, issue, clock, admin_headers):
    run_day(client, attendant, issue, clock)
    body = client.get("/api/admin/dashboard", headers=admin_headers).json
    assert body["issued"] == 7 and body["attended"] == 4 and body["waiting"] == 2
    assert body["open_sessions"][0]["counter"]["id"] == attendant["counter_id"]
    assert len(body["recent_calls"]) == 5
