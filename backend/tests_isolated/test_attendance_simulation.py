"""Simulador estatístico ``flask simulate-attendance`` (somente demonstração).

Nenhum teste usa banco: o app de teste aponta para um arquivo SQLite que NUNCA
deve ser criado, e conexões de banco, rede e ``time.sleep`` são bloqueadas.
"""
from __future__ import annotations

import json
import os
import random
import socket
import subprocess
import sys
import time as time_module
from collections import Counter as Tally
from datetime import date, datetime, time
from pathlib import Path

import pytest
from flask import Flask
from sqlalchemy.engine import Engine

import app.attendance_simulation as sim
from app.attendance_simulation import (
    DEFAULT_SEED,
    DEFAULT_TICKETS,
    MAX_TICKETS,
    MIN_TICKETS,
    absent_count,
    balanced_type_counts,
    service_seconds,
    simulate_attendance_command,
    simulate_day,
)
from app.extensions import db
from app.models import TicketStatus, TicketType
from app.services.queue_service import QueueService
from app.services.state_machine import TicketStateMachine
from app.services.ticket_service import format_ticket_code
from app.utils.clock import Clock

DAY = date(2026, 11, 27)
BACKEND_DIR = Path(__file__).resolve().parents[1]
S = TicketStatus


# ======================================================================= apoio
class StubRng:
    """PRNG determinístico: registra as chamadas e devolve valores escolhidos pelo teste."""

    def __init__(self, *, pick: str = "low", random_value: float = 0.0):
        self.pick = pick
        self.random_value = random_value
        self.calls: list[tuple] = []

    def randint(self, a: int, b: int) -> int:
        self.calls.append(("randint", a, b))
        return {"low": a, "high": b, "mid": (a + b) // 2}[self.pick]

    def random(self) -> float:
        self.calls.append(("random",))
        return self.random_value


def at(value: str | None) -> datetime | None:
    return datetime.fromisoformat(value) if value else None


def all_timestamps(report: dict) -> list[datetime]:
    stamps = []
    for ticket in report["tickets"]:
        for key in ("issued_at", "first_called_at", "second_called_at", "started_at", "finished_at"):
            if ticket[key]:
                stamps.append(at(ticket[key]))
        stamps += [at(call["called_at"]) for call in ticket["calls"]]
        stamps += [at(entry["at"]) for entry in ticket["status_history"]]
        stamps += [at(entry["at"]) for entry in ticket["audit"]]
    stamps += [at(entry["at"]) for entry in report["day_audit"]]
    return stamps


def released_at(ticket: dict) -> datetime:
    return at(ticket["status_history"][-1]["at"])


def assert_priority_replay(report: dict) -> None:
    """Revalida cada chamada com a regra REAL (QueueService.select_next_type)."""
    by_code = {t["code"]: t for t in report["tickets"]}
    order = report["call_sequence"]
    called = [t["code"] for t in report["tickets"] if t["calls"]]
    assert sorted(order) == sorted(called) and len(order) == len(set(order))
    taken: set[str] = set()
    last = None
    previous_time = None
    for code in order:
        ticket = by_code[code]
        now = at(ticket["first_called_at"])
        assert previous_time is None or now >= previous_time, "chamadas fora de ordem cronológica"
        previous_time = now
        waiting = [t for t in report["tickets"] if t["code"] not in taken and at(t["issued_at"]) <= now]
        counts = Tally(TicketType(t["type"]) for t in waiting)
        expected = QueueService.select_next_type(last, dict(counts))
        assert ticket["type"] == expected.value, f"{code} violou o ciclo SP -> SE/SG"
        oldest = min((t for t in waiting if t["type"] == expected.value), key=lambda t: (at(t["issued_at"]), t["daily_sequence"]))
        assert oldest["code"] == code, "deve ser chamada a senha mais antiga da categoria"
        taken.add(code)
        last = expected


@pytest.fixture(scope="module")
def default_report() -> dict:
    return simulate_day(tickets=DEFAULT_TICKETS, seed=DEFAULT_SEED, day=DAY)


@pytest.fixture(scope="module")
def overloaded_report() -> dict:
    # expediente artificialmente curto: a carga não cabe e o restante é descartado no fechamento
    return simulate_day(
        tickets=300, seed=7, day=DAY, open_time=time(7, 0), close_time=time(9, 0), last_arrival_time=time(8, 0)
    )


# ============================================================ distribuições de tempo
@pytest.mark.parametrize(
    ("ticket_type", "low", "high"),
    [(TicketType.SP, 600, 1200), (TicketType.SG, 120, 480)],  # SP 15min ± 5; SG 5min ± 3
)
def test_uniform_service_time_bounds_with_deterministic_samples(ticket_type, low, high):
    for pick, expected in (("low", low), ("high", high), ("mid", (low + high) // 2)):
        rng = StubRng(pick=pick)
        assert service_seconds(ticket_type, rng) == expected
        assert rng.calls == [("randint", low, high)]  # uniforme inteira, limites inclusivos


@pytest.mark.parametrize(
    ("random_value", "expected"), [(0.0, 60), (0.5, 60), (0.9499, 60), (0.95, 300), (0.999999, 300)]
)
def test_se_service_time_is_60s_95pct_or_300s_5pct_with_deterministic_samples(random_value, expected):
    rng = StubRng(random_value=random_value)
    assert service_seconds(TicketType.SE, rng) == expected
    assert rng.calls == [("random",)]


@pytest.mark.parametrize(
    ("ticket_type", "low", "high", "mean"),
    [(TicketType.SP, 600, 1200, 900), (TicketType.SG, 120, 480, 300)],
)
def test_uniform_distribution_with_seeded_samples(ticket_type, low, high, mean):
    rng = random.Random(2026)
    samples = [service_seconds(ticket_type, rng) for _ in range(20_000)]
    assert min(samples) >= low and max(samples) <= high
    assert abs(sum(samples) / len(samples) - mean) < (high - low) * 0.01
    # uniforme: cada quarto do intervalo recebe ~25% das amostras
    width = (high - low) / 4
    quarters = Tally(min(int((s - low) / width), 3) for s in samples)
    assert all(0.23 < quarters[q] / len(samples) < 0.27 for q in range(4))


def test_se_distribution_with_seeded_samples():
    rng = random.Random(2026)
    samples = [service_seconds(TicketType.SE, rng) for _ in range(20_000)]
    tally = Tally(samples)
    assert set(tally) == {60, 300}
    assert 0.045 < tally[300] / len(samples) < 0.055


# ============================================================ quantidades
@pytest.mark.parametrize(("total", "expected"), [(20, 1), (30, 2), (50, 3), (100, 5), (110, 6), (299, 15), (300, 15)])
def test_absent_count_is_five_percent_rounded_half_up(total, expected):
    assert absent_count(total) == expected


@pytest.mark.parametrize(("total", "expected"), [(20, (7, 7, 6)), (100, (34, 33, 33)), (101, (34, 34, 33)), (300, (100, 100, 100))])
def test_three_categories_are_balanced(total, expected):
    counts = balanced_type_counts(total)
    assert list(counts) == [TicketType.SP, TicketType.SE, TicketType.SG]
    assert tuple(counts.values()) == expected


# ============================================================ simulação (função pura)
def test_seeded_reproducibility_in_process():
    first = simulate_day(tickets=120, seed=99, day=DAY)
    assert simulate_day(tickets=120, seed=99, day=DAY) == first
    other = simulate_day(tickets=120, seed=100, day=DAY)
    assert other["tickets"] != first["tickets"]


def test_seeded_reproducibility_across_processes_and_hash_seeds(default_report):
    script = (
        "import json, datetime\n"
        "from app.attendance_simulation import simulate_day\n"
        "print(json.dumps(simulate_day(tickets=100, seed=42, day=datetime.date(2026, 11, 27)), sort_keys=True))\n"
    )
    outputs = []
    for hash_seed in ("1", "987"):
        env = {**os.environ, "PYTHONHASHSEED": hash_seed, "FLASK_ENV": "development"}
        done = subprocess.run(
            [sys.executable, "-c", script], cwd=BACKEND_DIR, env=env, capture_output=True, text=True, timeout=120, check=True
        )
        outputs.append(done.stdout)
    assert outputs[0] == outputs[1] == json.dumps(default_report, sort_keys=True) + "\n"


def test_report_is_marked_simulated_and_json_serializable(default_report):
    report = default_report
    assert report["simulated"] is True
    assert report["database_reads"] is False and report["database_writes"] is False
    assert report["synthetic_data_only"] is True
    assert report["seed"] == 42 and report["date"] == "2026-11-27"
    assert report["requested"] == {"tickets": 100, "seed": 42, "date": "2026-11-27"}
    assert report["parameters"]["counters"] == 5
    assert report["parameters"]["priority_rule"] == "QueueService.select_next_type"
    json.dumps(report)


def test_exactly_five_percent_no_show_on_100_tickets(default_report):
    totals = default_report["totals"]
    assert totals["issued"] == 100
    assert totals["absent_selected"] == 5
    assert totals["no_show"] == 5
    assert totals["no_show_percentage"] == 5.0
    assert totals["discarded"] == 0
    assert totals["attended"] == 95
    assert totals["not_attended"] == 5
    statuses = Tally(t["status"] for t in default_report["tickets"])
    assert statuses == {"ATENDIDA": 95, "NAO_COMPARECEU": 5}
    assert sum(t["absent_selected"] for t in default_report["tickets"]) == 5


def test_balanced_categories_and_real_ticket_codes(default_report):
    tickets = default_report["tickets"]
    assert Tally(t["type"] for t in tickets) == {"SP": 34, "SE": 33, "SG": 33}
    for ticket_type in TicketType:
        same = [t for t in tickets if t["type"] == ticket_type.value]
        assert [t["daily_sequence"] for t in same] == list(range(1, len(same) + 1))  # ordem de emissão
        for t in same:
            assert t["code"] == format_ticket_code(DAY, ticket_type, t["daily_sequence"])
            assert t["short_code"] == t["code"].split("-", 1)[1]
    issued = [at(t["issued_at"]) for t in tickets]
    assert issued == sorted(issued)


def test_attended_tickets_history_and_duration(default_report):
    attended = [t for t in default_report["tickets"] if t["status"] == "ATENDIDA"]
    limits = {"SP": (600, 1200), "SG": (120, 480)}
    for t in attended:
        assert t["absent_selected"] is False
        assert t["call_count"] == 1 and len(t["calls"]) == 1 and t["second_called_at"] is None
        assert [(h["from"], h["to"]) for h in t["status_history"]] == [
            (None, "EMITIDA"), ("EMITIDA", "AGUARDANDO"), ("AGUARDANDO", "CHAMADA"),
            ("CHAMADA", "EM_ATENDIMENTO"), ("EM_ATENDIMENTO", "ATENDIDA"),
        ]
        assert [a["action"] for a in t["audit"]] == ["TICKET_ISSUED", "TICKET_CALLED", "ATTENDANCE_STARTED", "ATTENDANCE_FINISHED"]
        started, finished = at(t["started_at"]), at(t["finished_at"])
        assert at(t["first_called_at"]) < started < finished
        assert t["duration_seconds"] == int((finished - started).total_seconds())
        if t["type"] in limits:
            low, high = limits[t["type"]]
            assert low <= t["duration_seconds"] <= high
        else:
            assert t["duration_seconds"] in (60, 300)
        assert t["counter"]["number"] == t["calls"][0]["counter"]
        assert t["attendant"] == t["calls"][0]["attendant"]
        assert t["wait_seconds"] == int((at(t["first_called_at"]) - at(t["issued_at"])).total_seconds())


def test_absent_tickets_need_two_calls_and_have_no_attendance(default_report):
    absent = [t for t in default_report["tickets"] if t["status"] == "NAO_COMPARECEU"]
    assert len(absent) == 5
    for t in absent:
        assert t["absent_selected"] is True
        assert t["call_count"] == 2 and [c["attempt"] for c in t["calls"]] == [1, 2]
        assert t["calls"][0]["counter"] == t["calls"][1]["counter"]
        first, second = at(t["first_called_at"]), at(t["second_called_at"])
        assert first < second < released_at(t)  # não comparecimento só depois da 2ª chamada
        assert [(h["from"], h["to"]) for h in t["status_history"]] == [
            (None, "EMITIDA"), ("EMITIDA", "AGUARDANDO"), ("AGUARDANDO", "CHAMADA"),
            ("CHAMADA", "CHAMADA_NOVAMENTE"), ("CHAMADA_NOVAMENTE", "NAO_COMPARECEU"),
        ]
        assert [a["action"] for a in t["audit"]] == ["TICKET_ISSUED", "TICKET_CALLED", "TICKET_RECALLED", "TICKET_NO_SHOW"]
        for field in ("started_at", "finished_at", "duration_seconds", "counter", "attendant"):
            assert t[field] is None, field


@pytest.mark.parametrize("report_name", ["default_report", "overloaded_report"])
def test_every_transition_is_valid_and_chronological(request, report_name):
    for t in request.getfixturevalue(report_name)["tickets"]:
        history = t["status_history"]
        assert history[0]["from"] is None and history[0]["to"] == "EMITIDA"
        for entry in history[1:]:
            assert TicketStateMachine.can_transition(S(entry["from"]), S(entry["to"])), entry
        assert [h["from"] for h in history[1:]] == [h["to"] for h in history[:-1]]
        stamps = [at(h["at"]) for h in history]
        assert stamps == sorted(stamps)
        assert history[-1]["to"] == t["status"]


@pytest.mark.parametrize("report_name", ["default_report", "overloaded_report"])
def test_queue_priority_replays_with_real_rule(request, report_name):
    assert_priority_replay(request.getfixturevalue(report_name))


def test_simulator_uses_real_queue_rule(monkeypatch):
    calls = []
    real = QueueService.select_next_type

    def spy(last_called, waiting):
        calls.append(dict(waiting))
        return real(last_called, waiting)

    monkeypatch.setattr(QueueService, "select_next_type", staticmethod(spy))
    report = simulate_day(tickets=40, seed=3, day=DAY)
    assert len(calls) >= len(report["call_sequence"]) == 40
    assert all(set(c) == set(TicketType) for c in calls)


def test_schedule_five_counters_from_7h_without_overlap(default_report):
    tickets = default_report["tickets"]
    opening = datetime.fromisoformat("2026-11-27T07:00:00-03:00")
    closing = datetime.fromisoformat("2026-11-27T17:00:00-03:00")
    for stamp in all_timestamps(default_report):
        assert opening <= stamp <= closing and stamp.date() == DAY
    per_counter: dict[int, list[tuple[datetime, datetime]]] = {}
    for t in tickets:
        per_counter.setdefault(t["calls"][0]["counter"], []).append((at(t["first_called_at"]), released_at(t)))
    assert set(per_counter) <= {1, 2, 3, 4, 5} and len(per_counter) == 5
    for intervals in per_counter.values():
        intervals.sort()
        for (_, end), (start, _) in zip(intervals, intervals[1:]):
            assert start >= end, "guichê com dois atendimentos sobrepostos"
    first_calls = sorted(at(t["first_called_at"]) for t in tickets)
    assert first_calls[0] >= at(tickets[0]["issued_at"]) >= opening


def test_counter_and_type_indicators_are_consistent(default_report):
    report = default_report
    tickets = report["tickets"]
    by_counter = report["by_counter"]
    assert [c["number"] for c in by_counter] == [1, 2, 3, 4, 5]
    assert sum(c["attended"] for c in by_counter) == report["totals"]["attended"]
    assert sum(c["no_show"] for c in by_counter) == report["totals"]["no_show"]
    assert sum(c["tickets_called"] for c in by_counter) == len(report["call_sequence"])
    assert report["totals"]["utilization_basis_seconds"] == 36_000  # 07h-17h
    for c in by_counter:
        mine = [t for t in tickets if t["calls"] and t["calls"][0]["counter"] == c["number"]]
        busy = sum(int((released_at(t) - at(t["first_called_at"])).total_seconds()) for t in mine)
        assert c["busy_seconds"] == c["busy_during_business_seconds"] == busy  # tudo terminou antes das 17h
        assert c["overtime_seconds"] == 0
        assert c["utilization_percentage"] == round(busy / 36_000 * 100, 1)
        durations = [t["duration_seconds"] for t in mine if t["status"] == "ATENDIDA"]
        assert c["avg_attendance_seconds"] == (round(sum(durations) / len(durations), 1) if durations else None)
    durations = [t["duration_seconds"] for t in tickets if t["status"] == "ATENDIDA"]
    assert report["totals"]["avg_attendance_seconds"] == round(sum(durations) / len(durations), 1)
    by_type = {row["type"]: row for row in report["by_type"]}
    assert list(by_type) == ["SP", "SE", "SG"]
    assert sum(row["issued"] for row in by_type.values()) == 100
    for key in ("attended", "no_show", "discarded"):
        assert sum(row[key] for row in by_type.values()) == report["totals"][key]
    assert by_type["SP"]["min_attendance_seconds"] >= 600 and by_type["SP"]["max_attendance_seconds"] <= 1200


def test_workload_that_does_not_fit_is_discarded_at_closing(overloaded_report):
    report = overloaded_report
    totals = report["totals"]
    discarded = [t for t in report["tickets"] if t["status"] == "DESCARTADA"]
    assert totals["discarded"] == len(discarded) > 0
    assert totals["issued"] == totals["attended"] + totals["no_show"] + totals["discarded"] == 300
    assert totals["not_attended"] == totals["no_show"] + totals["discarded"]
    closing = datetime.fromisoformat("2026-11-27T09:00:00-03:00")
    for t in discarded:
        assert t["calls"] == [] and t["call_count"] == 0 and t["first_called_at"] is None
        for field in ("started_at", "finished_at", "duration_seconds", "counter", "attendant", "wait_seconds"):
            assert t[field] is None, field
        assert (t["status_history"][-1]["from"], t["status_history"][-1]["to"]) == ("AGUARDANDO", "DESCARTADA")
        assert at(t["status_history"][-1]["at"]) == closing
        assert [a["action"] for a in t["audit"]] == ["TICKET_ISSUED"]
    assert report["day_audit"] == [
        {"action": "DAY_CLOSED", "at": "2026-11-27T09:00:00-03:00", "details": {"discarded": len(discarded)}}
    ]
    # Só aguardando é descartada no fechamento; serviços já chamados podem terminar depois.
    assert all(at(t["issued_at"]) < closing for t in report["tickets"])
    assert all(at(t["first_called_at"]) < closing for t in report["tickets"] if t["calls"])


def test_overtime_is_split_and_utilization_never_exceeds_100(overloaded_report):
    opening = datetime.fromisoformat("2026-11-27T07:00:00-03:00")
    closing = datetime.fromisoformat("2026-11-27T09:00:00-03:00")
    tickets = overloaded_report["tickets"]
    last_release = max(released_at(t) for t in tickets if t["calls"])
    assert last_release > closing  # cenário realmente atravessa o fechamento
    basis = int((last_release - opening).total_seconds())
    assert overloaded_report["totals"]["utilization_basis_seconds"] == basis
    assert sum(c["overtime_seconds"] for c in overloaded_report["by_counter"]) > 0
    for c in overloaded_report["by_counter"]:
        mine = [t for t in tickets if t["calls"] and t["calls"][0]["counter"] == c["number"]]
        overtime = sum(max(0, int((released_at(t) - closing).total_seconds())) for t in mine)
        assert c["overtime_seconds"] == overtime
        assert c["busy_seconds"] == c["busy_during_business_seconds"] + c["overtime_seconds"]
        assert c["busy_during_business_seconds"] <= 7_200  # 07h-09h
        assert 0 < c["utilization_percentage"] <= 100
        assert c["utilization_percentage"] == round(c["busy_seconds"] / basis * 100, 1)


@pytest.mark.parametrize("tickets", [MIN_TICKETS - 1, MAX_TICKETS + 1, 0, -5])
def test_simulate_day_rejects_ticket_count_outside_bounds(tickets):
    with pytest.raises(ValueError):
        simulate_day(tickets=tickets, seed=1, day=DAY)


@pytest.mark.parametrize("tickets", [MIN_TICKETS, MAX_TICKETS])
def test_simulate_day_accepts_ticket_count_bounds(tickets):
    report = simulate_day(tickets=tickets, seed=1, day=DAY)
    assert report["totals"]["issued"] == tickets
    assert report["totals"]["absent_selected"] == absent_count(tickets)


@pytest.mark.parametrize(
    "kwargs",
    [
        {"counters": 0},
        {"open_time": time(17, 0), "close_time": time(7, 0)},
        {"last_arrival_time": time(18, 0)},
        {"last_arrival_time": time(7, 0)},
    ],
)
def test_simulate_day_rejects_invalid_schedule(kwargs):
    with pytest.raises(ValueError):
        simulate_day(tickets=50, seed=1, day=DAY, **kwargs)


# ============================================================ CLI
@pytest.fixture()
def sandbox(monkeypatch, tmp_path):
    """Bloqueia banco, rede e sleep; o arquivo SQLite configurado nunca pode ser criado."""

    def _forbidden(*_args, **_kwargs):
        raise AssertionError("o simulador não pode acessar banco, rede nem dormir")

    monkeypatch.setattr(Engine, "connect", _forbidden)
    monkeypatch.setattr(Engine, "raw_connection", _forbidden)
    monkeypatch.setattr(socket.socket, "connect", _forbidden)
    monkeypatch.setattr(socket, "create_connection", _forbidden)
    monkeypatch.setattr(time_module, "sleep", _forbidden)
    return tmp_path


@pytest.fixture()
def sim_app(sandbox, monkeypatch):
    monkeypatch.setenv("FLASK_ENV", "development")
    db_file = sandbox / "nunca_criado.sqlite"
    app = Flask("simulation_isolated")
    app.config.update(SQLALCHEMY_DATABASE_URI=f"sqlite:///{db_file.as_posix()}", ENV_NAME="development",
                      TIMEZONE="America/Recife", TESTING=True)
    db.init_app(app)  # banco configurado, mas jamais acessado
    app.cli.add_command(simulate_attendance_command)
    app.extensions["db_file"] = db_file
    return app


@pytest.fixture()
def run_sim(sim_app):
    def _run(*args: str):
        return sim_app.test_cli_runner().invoke(args=["simulate-attendance", *args])

    return _run


@pytest.fixture()
def no_simulation(monkeypatch):
    def _fail(**_kwargs):
        raise AssertionError("nenhuma simulação deveria ter sido executada")

    monkeypatch.setattr(sim, "simulate_day", _fail)


def test_cli_outputs_json_only_to_stdout_without_db_network_or_clock_patch(sim_app, run_sim, sandbox):
    clock_before = Clock.now_utc
    files_before = sorted(p.name for p in sandbox.iterdir())
    result = run_sim("--confirm-demo", "--date", "2026-11-27")
    assert result.exit_code == 0, result.output
    assert result.stderr == ""
    report = json.loads(result.stdout)
    assert report == simulate_day(tickets=100, seed=42, day=DAY)
    assert report["simulated"] is True and report["database_writes"] is False
    assert report["requested"] == {"tickets": 100, "seed": 42, "date": "2026-11-27"}
    assert not sim_app.extensions["db_file"].exists()  # SQLite cria o arquivo na 1ª conexão
    assert sorted(p.name for p in sandbox.iterdir()) == files_before  # nenhum arquivo gravado
    assert Clock.now_utc is clock_before


def test_cli_options_and_default_date(run_sim, monkeypatch):
    result = run_sim("--confirm-demo", "--tickets", "60", "--seed", "7", "--date", "2027-01-05")
    assert result.exit_code == 0, result.output
    report = json.loads(result.stdout)
    assert (report["seed"], report["date"], report["totals"]["issued"]) == (7, "2027-01-05", 60)
    assert report["tickets"][0]["code"].startswith("270105-")

    monkeypatch.setattr(sim, "local_today", lambda: date(2026, 12, 1))  # só a data padrão do comando
    result = run_sim("--confirm-demo")
    assert result.exit_code == 0, result.output
    report = json.loads(result.stdout)
    assert report["date"] == "2026-12-01" and report["date_source"] == "local_today"
    assert report["requested"] == {"tickets": 100, "seed": 42, "date": None}


@pytest.mark.parametrize("tickets", [str(MIN_TICKETS), str(MAX_TICKETS)])
def test_cli_accepts_ticket_bounds(run_sim, tickets):
    result = run_sim("--confirm-demo", "--date", "2026-11-27", "--tickets", tickets)
    assert result.exit_code == 0, result.output
    assert json.loads(result.stdout)["totals"]["issued"] == int(tickets)


@pytest.mark.parametrize(
    "args",
    [
        ("--tickets", str(MIN_TICKETS - 1)),
        ("--tickets", str(MAX_TICKETS + 1)),
        ("--tickets", "cem"),
        ("--seed", "-1"),
        ("--seed", "1.5"),
        ("--date", "2026-02-30"),
        ("--date", "27/11/2026"),
        ("--date", "20261127"),
        ("--date", "2026-11-27T10:00"),
        ("--date", "2026-W48-5"),
        ("--date", ""),
    ],
)
def test_cli_rejects_invalid_arguments(run_sim, no_simulation, args):
    result = run_sim("--confirm-demo", *args)
    assert result.exit_code != 0
    assert result.stdout == ""


@pytest.mark.parametrize(
    ("flask_env", "env_name"),
    [
        ("production", "production"),
        ("production", "development"),
        ("development", "production"),
        ("development", None),
        (None, "development"),
        ("", "development"),
        ("staging", "development"),
        ("testing", "testing"),
        ("Development", "development"),
        ("DEVELOPMENT", "development"),
        (" development", "development"),
        ("development ", "development"),
    ],
)
def test_cli_refused_outside_exact_development(sim_app, run_sim, no_simulation, monkeypatch, flask_env, env_name):
    if flask_env is None:
        monkeypatch.delenv("FLASK_ENV", raising=False)
    else:
        monkeypatch.setenv("FLASK_ENV", flask_env)
    sim_app.config["ENV_NAME"] = env_name
    result = run_sim("--confirm-demo", "--date", "2026-11-27")
    assert result.exit_code != 0
    assert result.stdout == ""
    assert "FLASK_ENV=development" in result.stderr
    if "production" in (flask_env, env_name):
        assert "recusado em produção" in result.stderr
    assert not sim_app.extensions["db_file"].exists()


def test_cli_requires_explicit_opt_in(sim_app, run_sim, no_simulation):
    result = run_sim("--date", "2026-11-27")
    assert result.exit_code != 0
    assert result.stdout == ""
    assert "--confirm-demo" in result.stderr
    assert not sim_app.extensions["db_file"].exists()


def test_cli_production_refusal_comes_before_opt_in_check(run_sim, no_simulation, monkeypatch):
    monkeypatch.setenv("FLASK_ENV", "production")
    result = run_sim()
    assert result.exit_code != 0 and "recusado em produção" in result.stderr


def test_command_is_registered_with_existing_commands():
    from app.cli import register_cli

    bare = Flask("cli_registration_only")
    register_cli(bare)
    assert {"create-admin", "seed", "close-day", "seed-demo", "simulate-attendance"} <= set(bare.cli.commands)


def test_cli_in_normal_app_context_never_touches_configured_database(sandbox, monkeypatch):
    from app import create_app

    monkeypatch.setenv("FLASK_ENV", "development")
    app = create_app(
        "development",
        overrides={
            # MySQL inexistente: qualquer acesso falharia (e Engine.connect está bloqueado).
            "SQLALCHEMY_DATABASE_URI": "mysql+pymysql://simulacao:simulacao@127.0.0.1:9/nao_existe",
            "SECRET_KEY": "isolated-test-secret-key-not-real-000000",
            "JWT_SECRET_KEY": "isolated-test-jwt-secret-key-not-real-0000",
            "SCHEDULER_ENABLED": False,
        },
    )
    assert app.config["ENV_NAME"] == "development"
    result = app.test_cli_runner().invoke(args=["simulate-attendance", "--confirm-demo", "--tickets", "20", "--date", "2026-11-27"])
    assert result.exit_code == 0, result.output
    assert json.loads(result.stdout)["totals"]["issued"] == 20
