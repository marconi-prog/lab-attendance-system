"""Dados do painel público (quadro "próximos / chamando / últimas chamadas").

* latest      — últimas senhas efetivamente chamadas (tabela calls).
* queue       — senhas aguardando, por fila, na ordem em que serão atendidas.
* next_up     — previsão das próximas chamadas pelo ciclo de prioridade do QueueService.
* in_service  — senhas em atendimento agora, com o guichê.

O painel mostra apenas o código curto (ex.: SP003) — nenhum dado pessoal.
"""
from __future__ import annotations

from flask import current_app

from app.models import TicketType
from app.repositories import CallRepository, TicketRepository
from app.schemas.common import serialize_local
from app.services.announcement import build_announcement
from app.utils.clock import local_day_bounds_utc, local_now, local_today

PANEL_SIZE = 5
QUEUE_PREVIEW = 8
NEXT_UP_SIZE = 6


class PanelService:
    @staticmethod
    def latest(limit: int = PANEL_SIZE) -> list[dict]:
        start, _ = local_day_bounds_utc(local_today())
        seen: set[int] = set()
        items: list[dict] = []
        # Busca chamadas recentes e mantém só a mais nova de cada senha:
        # uma repetição "sobe" a senha para o topo sem duplicá-la.
        for call in CallRepository.recent_since(start, limit * 4):
            if call.ticket_id in seen:
                continue
            seen.add(call.ticket_id)
            ticket = call.ticket
            items.append(
                {
                    "call_id": call.id,
                    "ticket_id": ticket.id,
                    "code": ticket.code,
                    "short_code": ticket.short_code,
                    "type": ticket.type.value,
                    "type_label": ticket.type.label,
                    "counter_number": call.counter.number,
                    "counter_label": call.counter.label,
                    "counter_name": call.counter.name,
                    "attempt_number": call.attempt_number,
                    "is_repeat": call.attempt_number > 1,
                    "called_at": serialize_local(call.called_at),
                    "announcement": build_announcement(ticket, call.counter.number, repeat=call.attempt_number > 1),
                }
            )
            if len(items) == limit:
                break
        return items

    @staticmethod
    def queue_board() -> dict:
        from app.services.queue_service import QueueService

        today = local_today()
        counts = TicketRepository.waiting_counts(today)
        waiting = TicketRepository.waiting_by_type(today, QUEUE_PREVIEW)
        state = TicketRepository.get_queue_state(today)

        queues = [
            {
                "type": t.value,
                "label": t.label,
                "total": counts[t],
                "tickets": [
                    {"ticket_id": tk.id, "short_code": tk.short_code, "position": i + 1, "issued_at": serialize_local(tk.issued_at)}
                    for i, tk in enumerate(waiting[t])
                ],
            }
            for t in TicketType
        ]

        # Simula o ciclo de prioridade sobre as filas atuais (mesma regra do "chamar próxima").
        remaining = {t: list(waiting[t]) for t in TicketType}
        last = state.last_called_type if state else None
        next_up = []
        while len(next_up) < NEXT_UP_SIZE:
            next_type = QueueService.select_next_type(last, {t: len(v) for t, v in remaining.items()})
            if next_type is None:
                break
            ticket = remaining[next_type].pop(0)
            next_up.append({"ticket_id": ticket.id, "short_code": ticket.short_code, "type": next_type.value})
            last = next_type

        in_service = [
            {"ticket_id": tk.id, "short_code": tk.short_code, "type": tk.type.value, "counter_label": f"{number:02d}"}
            for tk, number in TicketRepository.in_service(today)
        ]
        return {"total_waiting": sum(counts.values()), "queues": queues, "next_up": next_up, "in_service": in_service}

    @classmethod
    def snapshot(cls) -> dict:
        return {
            "lab_name": current_app.config["LAB_NAME"],
            "server_time": local_now().isoformat(timespec="seconds"),
            "latest": cls.latest(),
            **cls.queue_board(),
        }

    @classmethod
    def publish(cls) -> None:
        """Envia o estado completo ao painel (chamado após cada mudança confirmada)."""
        from app.services.realtime import Events, RealtimeNotifier

        RealtimeNotifier.to_panel(Events.PANEL_UPDATED, cls.snapshot())
