"""SIMULAÇÃO estatística de um dia de atendimento: ``flask simulate-attendance``.

Somente para demonstração/estudo dos tempos exigidos no edital — NÃO faz parte
do atendimento real:

* tempos de atendimento simulados: SP = 15 min ± 5 (uniforme), SG = 5 min ± 3
  (uniforme), SE = 60 s (95%) ou 300 s (5%);
* ~5% das senhas emitidas não comparecem (sorteio sem reposição,
  arredondamento half-up). Na operação real ninguém é descartado ao acaso:
  o "não compareceu" só existe após duas chamadas feitas pelo atendente;
* função PURA: não lê nem grava no banco, não usa rede, não dorme, não altera
  o relógio da aplicação (``Clock``) nem os tempos dos atendimentos reais;
  todos os dados (senhas, guichês, atendentes, auditoria) são sintéticos;
* PRNG próprio com semente (``random.Random(seed)``): mesma semente, mesma
  data e mesma quantidade => mesmo resultado;
* reaproveita as regras reais: ``QueueService.select_next_type`` (ciclo
  SP -> SE/SG) e ``format_ticket_code`` (YYMMDD-PPSQ), sem duplicá-las;
* 5 guichês a partir das 07h (min-heap: o guichê livre há mais tempo chama a
  próxima senha); nenhuma nova chamada começa às 17h ou depois. Atendimentos
  já chamados podem terminar após o fechamento; a fila restante é DESCARTADA
  às 17h, contada separadamente.

O comando exige ``FLASK_ENV`` exatamente ``development``, configuração de
desenvolvimento carregada e ``--confirm-demo``; imprime JSON apenas no stdout.
"""
from __future__ import annotations

import heapq
import json
import os
import random
import re
from collections import deque
from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

import click
from flask import current_app
from flask.cli import with_appcontext

from app.models.enums import TICKET_TYPE_LABELS, TicketStatus, TicketType
from app.services.queue_service import QueueService
from app.services.state_machine import TicketStateMachine
from app.services.ticket_service import format_ticket_code
from app.utils.clock import DEFAULT_TZ, local_today

ALLOWED_ENV = "development"
NOTHING_DONE = "Nada foi simulado; nenhum dado foi lido ou gravado."

MIN_TICKETS, MAX_TICKETS, DEFAULT_TICKETS = 20, 300, 100
DEFAULT_SEED = 42
COUNTERS = 5
OPEN_TIME = time(7, 0)
CLOSE_TIME = time(17, 0)
# Emissões simuladas concentradas na 1ª hora (07h-08h, pico de abertura): forma-se
# fila e o ciclo SP -> SE/SG é de fato exercitado; até 300 senhas cabem antes das 17h.
LAST_ARRIVAL_TIME = time(8, 0)

SP_SECONDS = (10 * 60, 20 * 60)  # 15 min ± 5, uniforme
SG_SECONDS = (2 * 60, 8 * 60)  # 5 min ± 3, uniforme
SE_SHORT_SECONDS, SE_LONG_SECONDS, SE_SHORT_PROBABILITY = 60, 300, 0.95
ABSENCE_PERCENT = 5

CALL_TO_START_SECONDS = 30  # cliente chega ao guichê após a chamada
RECALL_INTERVAL_SECONDS = 60  # ausente: 2ª (última) chamada 1 min após a 1ª
NO_SHOW_AFTER_SECONDS = 60  # ausente: não comparecimento 1 min após a 2ª chamada
MAX_CALL_ATTEMPTS = 2

S = TicketStatus


# ======================================================================= regras
def service_seconds(ticket_type: TicketType, rng) -> int:
    """Duração simulada do atendimento (segundos inteiros)."""
    if ticket_type == TicketType.SP:
        return rng.randint(*SP_SECONDS)
    if ticket_type == TicketType.SG:
        return rng.randint(*SG_SECONDS)
    return SE_SHORT_SECONDS if rng.random() < SE_SHORT_PROBABILITY else SE_LONG_SECONDS


def absent_count(total: int) -> int:
    """5% do total, arredondado half-up em aritmética inteira (100 -> 5, 50 -> 3)."""
    return (total * ABSENCE_PERCENT + 50) // 100


def balanced_type_counts(total: int) -> dict[TicketType, int]:
    """Divide igualmente entre SP, SE e SG; a sobra vai para as primeiras categorias."""
    base, extra = divmod(total, len(TicketType))
    return {t: base + (1 if i < extra else 0) for i, t in enumerate(TicketType)}


# ======================================================================= modelo
@dataclass
class _SimTicket:
    index: int
    type: TicketType
    sequence: int
    code: str
    issued: int  # segundos desde 00:00 do dia
    absent: bool
    service: int | None
    status: TicketStatus = S.AGUARDANDO
    counter: int | None = None
    calls: list[int] = field(default_factory=list)
    started: int | None = None
    finished: int | None = None
    released: int | None = None
    history: list[tuple[TicketStatus | None, TicketStatus, int, int | None]] = field(default_factory=list)
    audit: list[tuple[str, int, int | None, dict]] = field(default_factory=list)

    def move(self, target: TicketStatus, at: int, counter: int | None = None) -> None:
        TicketStateMachine.ensure_transition(self.status, target)  # mesma máquina de estados da API
        self.history.append((self.status, target, at, counter))
        self.status = target


def _seconds(value: time) -> int:
    return value.hour * 3600 + value.minute * 60 + value.second


def _round(value: float | None) -> float | None:
    return round(value, 1) if value is not None else None


def _mean(values: list[int]) -> float | None:
    return _round(sum(values) / len(values)) if values else None


def _attendant(number: int) -> str:
    return f"Atendente simulado {number:02d}"


def _counter_name(number: int) -> str:
    return f"Guichê {number:02d}"


# ======================================================================= simulação
def simulate_day(
    *,
    tickets: int = DEFAULT_TICKETS,
    seed: int = DEFAULT_SEED,
    day: date,
    timezone: str = DEFAULT_TZ,
    counters: int = COUNTERS,
    open_time: time = OPEN_TIME,
    close_time: time = CLOSE_TIME,
    last_arrival_time: time = LAST_ARRIVAL_TIME,
    date_source: str = "option",
) -> dict:
    """Simula um dia completo e devolve o relatório (dict serializável em JSON)."""
    if isinstance(tickets, bool) or not isinstance(tickets, int) or not MIN_TICKETS <= tickets <= MAX_TICKETS:
        raise ValueError(f"tickets deve estar entre {MIN_TICKETS} e {MAX_TICKETS}.")
    if isinstance(counters, bool) or not isinstance(counters, int) or counters < 1:
        raise ValueError("counters deve ser >= 1.")
    open_s, close_s, last_arrival_s = _seconds(open_time), _seconds(close_time), _seconds(last_arrival_time)
    if not open_s < last_arrival_s <= close_s:
        raise ValueError("Exige abertura < última emissão <= fechamento.")
    tz = ZoneInfo(timezone)
    rng = random.Random(seed)

    # --- sorteios (ordem fixa de consumo do PRNG => reprodutível)
    types = [t for t, n in balanced_type_counts(tickets).items() for _ in range(n)]
    rng.shuffle(types)
    offsets = sorted(rng.randrange(last_arrival_s - open_s) for _ in range(tickets))
    absent = set(rng.sample(range(tickets), absent_count(tickets)))
    sequences = dict.fromkeys(TicketType, 0)
    sim_tickets: list[_SimTicket] = []
    for index, (ticket_type, offset) in enumerate(zip(types, offsets)):
        sequences[ticket_type] += 1
        is_absent = index in absent
        ticket = _SimTicket(
            index=index, type=ticket_type, sequence=sequences[ticket_type],
            code=format_ticket_code(day, ticket_type, sequences[ticket_type]),
            issued=open_s + offset, absent=is_absent,
            service=None if is_absent else service_seconds(ticket_type, rng),
            status=S.EMITIDA,
        )
        ticket.history.append((None, S.EMITIDA, ticket.issued, None))
        ticket.move(S.AGUARDANDO, ticket.issued)
        ticket.audit.append(("TICKET_ISSUED", ticket.issued, None, {"code": ticket.code, "type": ticket_type.value}))
        sim_tickets.append(ticket)

    # --- fila: min-heap de guichês (livre em, número); relógio global monotônico
    pending = deque(sim_tickets)  # já ordenadas por emissão
    waiting: dict[TicketType, deque[_SimTicket]] = {t: deque() for t in TicketType}
    heap = [(open_s, number) for number in range(1, counters + 1)]
    heapq.heapify(heap)
    clock = open_s
    last_type: TicketType | None = None
    call_sequence: list[str] = []

    def admit(until: int) -> None:
        while pending and pending[0].issued <= until:
            item = pending.popleft()
            waiting[item.type].append(item)

    while heap:
        free_at, number = heapq.heappop(heap)
        now = max(free_at, clock)
        admit(now)
        if not any(waiting.values()):
            if not pending:
                continue  # nada mais a chamar hoje
            now = pending[0].issued
            admit(now)
        if now >= close_s:
            continue  # nunca inicia chamada a partir do fechamento
        next_type = QueueService.select_next_type(last_type, {t: len(q) for t, q in waiting.items()})
        ticket = waiting[next_type][0]
        waiting[next_type].popleft()
        clock = now
        last_type = next_type
        call_sequence.append(ticket.code)
        _run_flow(ticket, number, now)
        heapq.heappush(heap, (ticket.released, number))

    # --- fechamento: o que não foi chamado é descartado às 17h
    discarded = [t for t in sim_tickets if t.status == S.AGUARDANDO]
    for ticket in discarded:
        ticket.move(S.DESCARTADA, close_s)

    def stamp(seconds: int | None) -> str | None:
        if seconds is None:
            return None
        moment = datetime.combine(day, time.min, tzinfo=tz) + timedelta(seconds=seconds)
        return moment.isoformat(timespec="seconds")

    return _build_report(
        tickets_requested=tickets, seed=seed, day=day, timezone=timezone, counters=counters,
        open_s=open_s, close_s=close_s, last_arrival_s=last_arrival_s, date_source=date_source,
        sim_tickets=sim_tickets, call_sequence=call_sequence, discarded=len(discarded),
        absent_selected=len(absent), stamp=stamp,
    )


def _run_flow(ticket: _SimTicket, counter: int, now: int) -> None:
    """Chamada(s) e desfecho no guichê ``counter`` (um atendente sintético por guichê)."""
    ticket.counter = counter  # guichê que chamou; só vira "guichê do atendimento" se ATENDIDA
    ticket.calls.append(now)
    ticket.move(S.CHAMADA, now, counter)
    ticket.audit.append(("TICKET_CALLED", now, counter, {"code": ticket.code, "counter": counter, "attempt": 1}))
    if ticket.absent:
        second = now + RECALL_INTERVAL_SECONDS
        ticket.calls.append(second)
        ticket.move(S.CHAMADA_NOVAMENTE, second, counter)
        ticket.audit.append(("TICKET_RECALLED", second, counter, {"code": ticket.code, "counter": counter, "attempt": 2}))
        no_show = second + NO_SHOW_AFTER_SECONDS
        ticket.move(S.NAO_COMPARECEU, no_show, counter)
        ticket.audit.append(("TICKET_NO_SHOW", no_show, counter, {"code": ticket.code}))
        ticket.released = no_show
        return
    ticket.started = now + CALL_TO_START_SECONDS
    ticket.move(S.EM_ATENDIMENTO, ticket.started, counter)
    ticket.audit.append(("ATTENDANCE_STARTED", ticket.started, counter, {"code": ticket.code}))
    ticket.finished = ticket.started + ticket.service
    ticket.move(S.ATENDIDA, ticket.finished, counter)
    ticket.audit.append(
        ("ATTENDANCE_FINISHED", ticket.finished, counter, {"code": ticket.code, "duration_seconds": ticket.service})
    )
    ticket.released = ticket.finished


# ======================================================================= relatório
def _ticket_out(ticket: _SimTicket, stamp) -> dict:
    attended = ticket.status == S.ATENDIDA
    called_counter = ticket.counter if ticket.calls else None
    return {
        "code": ticket.code,
        "short_code": ticket.code.split("-", 1)[1],
        "type": ticket.type.value,
        "type_label": TICKET_TYPE_LABELS[ticket.type],
        "daily_sequence": ticket.sequence,
        "status": ticket.status.value,
        "absent_selected": ticket.absent,
        "issued_at": stamp(ticket.issued),
        "first_called_at": stamp(ticket.calls[0]) if ticket.calls else None,
        "second_called_at": stamp(ticket.calls[1]) if len(ticket.calls) > 1 else None,
        "call_count": len(ticket.calls),
        "calls": [
            {"attempt": i, "called_at": stamp(moment), "counter": called_counter, "attendant": _attendant(called_counter)}
            for i, moment in enumerate(ticket.calls, start=1)
        ],
        "wait_seconds": ticket.calls[0] - ticket.issued if ticket.calls else None,
        # Campos de ATENDIMENTO: nulos quando a senha não foi atendida.
        "started_at": stamp(ticket.started) if attended else None,
        "finished_at": stamp(ticket.finished) if attended else None,
        "duration_seconds": ticket.finished - ticket.started if attended else None,
        "counter": {"number": ticket.counter, "name": _counter_name(ticket.counter)} if attended else None,
        "attendant": _attendant(ticket.counter) if attended else None,
        "status_history": [
            {
                "from": source.value if source else None,
                "to": target.value,
                "at": stamp(moment),
                "counter": counter,
                "attendant": _attendant(counter) if counter else None,
            }
            for source, target, moment, counter in ticket.history
        ],
        "audit": [
            {
                "action": action,
                "at": stamp(moment),
                "counter": counter,
                "attendant": _attendant(counter) if counter else None,
                "details": details,
            }
            for action, moment, counter, details in ticket.audit
        ],
    }


def _build_report(
    *, tickets_requested, seed, day, timezone, counters, open_s, close_s, last_arrival_s, date_source,
    sim_tickets, call_sequence, discarded, absent_selected, stamp,
) -> dict:
    def hhmm(seconds: int) -> str:
        return f"{seconds // 3600:02d}:{seconds % 3600 // 60:02d}"

    attended = [t for t in sim_tickets if t.status == S.ATENDIDA]
    no_show = [t for t in sim_tickets if t.status == S.NAO_COMPARECEU]
    called = [t for t in sim_tickets if t.calls]
    issued = len(sim_tickets)

    by_type = []
    for ticket_type in TicketType:
        mine = [t for t in sim_tickets if t.type == ticket_type]
        durations = [t.service for t in mine if t.status == S.ATENDIDA]
        by_type.append(
            {
                "type": ticket_type.value,
                "label": TICKET_TYPE_LABELS[ticket_type],
                "issued": len(mine),
                "attended": len(durations),
                "no_show": sum(t.status == S.NAO_COMPARECEU for t in mine),
                "discarded": sum(t.status == S.DESCARTADA for t in mine),
                "avg_attendance_seconds": _mean(durations),
                "min_attendance_seconds": min(durations) if durations else None,
                "max_attendance_seconds": max(durations) if durations else None,
                "avg_wait_seconds": _mean([t.calls[0] - t.issued for t in mine if t.calls]),
            }
        )

    # Base da ocupação: da abertura até o fechamento OU até o fim do último atendimento já
    # chamado (pode passar das 17h). Assim a ocupação nunca excede 100%; o tempo após o
    # fechamento também aparece à parte em overtime_seconds.
    span = max([close_s, *(t.released for t in called)]) - open_s
    by_counter = []
    for number in range(1, counters + 1):
        mine = [t for t in called if t.counter == number]
        durations = [t.service for t in mine if t.status == S.ATENDIDA]
        busy = sum(t.released - t.calls[0] for t in mine)
        in_hours = sum(max(0, min(t.released, close_s) - t.calls[0]) for t in mine)
        by_counter.append(
            {
                "number": number,
                "name": _counter_name(number),
                "attendant": _attendant(number),
                "tickets_called": len(mine),
                "call_attempts": sum(len(t.calls) for t in mine),
                "attended": len(durations),
                "no_show": sum(t.status == S.NAO_COMPARECEU for t in mine),
                "avg_attendance_seconds": _mean(durations),
                "busy_seconds": busy,
                "busy_during_business_seconds": in_hours,
                "overtime_seconds": busy - in_hours,
                "utilization_percentage": _round(busy / span * 100),
                "first_call_at": stamp(min(t.calls[0] for t in mine)) if mine else None,
                "last_release_at": stamp(max(t.released for t in mine)) if mine else None,
            }
        )

    return {
        "simulated": True,
        "synthetic_data_only": True,
        "database_reads": False,
        "database_writes": False,
        "notice": (
            "SIMULAÇÃO estatística para demonstração: senhas, guichês, atendentes e auditoria são sintéticos; "
            "nenhum dado foi lido ou gravado no banco e o atendimento real não foi alterado."
        ),
        "seed": seed,
        "date": day.isoformat(),
        "date_source": date_source,
        "requested": {
            "tickets": tickets_requested,
            "seed": seed,
            "date": day.isoformat() if date_source == "option" else None,
        },
        "timezone": timezone,
        "parameters": {
            "counters": counters,
            "business_hours": {"open": hhmm(open_s), "close": hhmm(close_s)},
            "issue_window": {"start": hhmm(open_s), "end": hhmm(last_arrival_s)},
            "service_time_seconds": {
                "SP": {"distribution": "uniform", "min": SP_SECONDS[0], "max": SP_SECONDS[1]},
                "SG": {"distribution": "uniform", "min": SG_SECONDS[0], "max": SG_SECONDS[1]},
                "SE": {
                    "distribution": "discrete",
                    "values": [
                        {"seconds": SE_SHORT_SECONDS, "probability": SE_SHORT_PROBABILITY},
                        {"seconds": SE_LONG_SECONDS, "probability": round(1 - SE_SHORT_PROBABILITY, 2)},
                    ],
                },
            },
            "absence": {
                "percent": ABSENCE_PERCENT,
                "count": absent_selected,
                "selection": "sorteio sem reposição; arredondamento half-up",
            },
            "call_to_start_seconds": CALL_TO_START_SECONDS,
            "recall_interval_seconds": RECALL_INTERVAL_SECONDS,
            "no_show_after_seconds": NO_SHOW_AFTER_SECONDS,
            "max_call_attempts": MAX_CALL_ATTEMPTS,
            "priority_rule": "QueueService.select_next_type",
            "ticket_code_format": "format_ticket_code (YYMMDD-PPSQ)",
            "end_of_day": "senhas ainda aguardando no fechamento são descartadas",
        },
        "totals": {
            "issued": issued,
            "attended": len(attended),
            "no_show": len(no_show),
            "discarded": discarded,
            "not_attended": len(no_show) + discarded,
            "absent_selected": absent_selected,
            "no_show_percentage": _round(len(no_show) / issued * 100),
            "not_attended_percentage": _round((len(no_show) + discarded) / issued * 100),
            "avg_attendance_seconds": _mean([t.service for t in attended]),
            "avg_wait_seconds": _mean([t.calls[0] - t.issued for t in called]),
            "utilization_basis_seconds": span,
        },
        "by_type": by_type,
        "by_counter": by_counter,
        "call_sequence": call_sequence,
        "day_audit": [{"action": "DAY_CLOSED", "at": stamp(close_s), "details": {"discarded": discarded}}],
        "tickets": [_ticket_out(t, stamp) for t in sim_tickets],
    }


# ======================================================================= CLI
def ensure_simulation_environment() -> None:
    """Recusa fora de desenvolvimento ANTES de qualquer trabalho (FLASK_ENV exato, sem normalização)."""
    raw = os.environ.get("FLASK_ENV")
    configured = current_app.config.get("ENV_NAME")
    state = f"FLASK_ENV={raw!r}, configuração carregada={configured!r}"
    if (raw or "").strip().lower() == "production" or str(configured or "").strip().lower() == "production":
        raise click.ClickException(
            f"simulate-attendance é recusado em produção ({state}); só roda com FLASK_ENV=development. {NOTHING_DONE}"
        )
    if raw != ALLOWED_ENV or configured != ALLOWED_ENV:
        raise click.ClickException(
            f"simulate-attendance exige FLASK_ENV=development exatamente e configuração de desenvolvimento ({state}). "
            f"{NOTHING_DONE}"
        )


_ISO_DATE = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}")


class IsoDate(click.ParamType):
    name = "AAAA-MM-DD"

    def convert(self, value, param, ctx):
        if isinstance(value, date):
            return value
        text = str(value)
        if _ISO_DATE.fullmatch(text):
            try:
                return date.fromisoformat(text)
            except ValueError:
                pass
        self.fail(f"data inválida {text!r}: use AAAA-MM-DD (ex.: 2026-11-27).", param, ctx)


@click.command("simulate-attendance")
@click.option("--confirm-demo", is_flag=True, help="Obrigatório: confirma que é uma SIMULAÇÃO de demonstração.")
@click.option(
    "--tickets", type=click.IntRange(MIN_TICKETS, MAX_TICKETS), default=DEFAULT_TICKETS, show_default=True,
    help="Quantidade de senhas simuladas (SP/SE/SG equilibradas).",
)
@click.option("--seed", type=click.IntRange(min=0), default=DEFAULT_SEED, show_default=True, help="Semente do PRNG.")
@click.option("--date", "day", type=IsoDate(), default=None, help="Data simulada (AAAA-MM-DD). Padrão: hoje.")
@with_appcontext
def simulate_attendance_command(confirm_demo: bool, tickets: int, seed: int, day: date | None) -> None:
    """[SIMULAÇÃO] Gera um dia sintético de atendimento e imprime o relatório JSON no stdout.

    Não lê nem grava no banco. Recusado fora de FLASK_ENV=development. Exige --confirm-demo.
    """
    ensure_simulation_environment()
    if not confirm_demo:
        raise click.ClickException(f"Simulação de demonstração: informe --confirm-demo para executar. {NOTHING_DONE}")
    report = simulate_day(
        tickets=tickets,
        seed=seed,
        day=day or local_today(),
        timezone=current_app.config.get("TIMEZONE") or DEFAULT_TZ,
        date_source="option" if day else "local_today",
    )
    click.echo(json.dumps(report, ensure_ascii=True, indent=2))
