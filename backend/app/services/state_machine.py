"""Máquina de estados do ciclo de vida das senhas.

Toda mudança de status passa por `TicketStateMachine.transition`, que valida
a transição, atualiza a senha e grava um registro imutável em
ticket_status_history (data/hora, usuário e guichê responsáveis).
"""
from __future__ import annotations

from app.extensions import db
from app.models import Ticket, TicketStatus, TicketStatusHistory
from app.utils.clock import utcnow
from app.utils.errors import InvalidTransitionError

S = TicketStatus

ALLOWED_TRANSITIONS: dict[TicketStatus, frozenset[TicketStatus]] = {
    S.EMITIDA: frozenset({S.AGUARDANDO}),
    S.AGUARDANDO: frozenset({S.CHAMADA, S.DESCARTADA}),
    S.CHAMADA: frozenset({S.EM_ATENDIMENTO, S.CHAMADA_NOVAMENTE}),
    S.CHAMADA_NOVAMENTE: frozenset({S.EM_ATENDIMENTO, S.NAO_COMPARECEU}),
    S.EM_ATENDIMENTO: frozenset({S.ATENDIDA}),
    S.ATENDIDA: frozenset(),
    S.NAO_COMPARECEU: frozenset(),
    S.DESCARTADA: frozenset(),
}

STATUS_LABELS = {
    S.EMITIDA: "Emitida",
    S.AGUARDANDO: "Aguardando",
    S.CHAMADA: "Chamada",
    S.EM_ATENDIMENTO: "Em atendimento",
    S.ATENDIDA: "Atendida",
    S.CHAMADA_NOVAMENTE: "Chamada novamente",
    S.NAO_COMPARECEU: "Não compareceu",
    S.DESCARTADA: "Descartada",
}


class TicketStateMachine:
    @staticmethod
    def can_transition(current: TicketStatus, target: TicketStatus) -> bool:
        return target in ALLOWED_TRANSITIONS.get(current, frozenset())

    @classmethod
    def ensure_transition(cls, current: TicketStatus, target: TicketStatus) -> None:
        if not cls.can_transition(current, target):
            raise InvalidTransitionError(
                f"Transição inválida: {STATUS_LABELS[current]} → {STATUS_LABELS[target]}.",
                details={"from": current.value, "to": target.value},
            )

    @classmethod
    def transition(
        cls,
        ticket: Ticket,
        target: TicketStatus,
        *,
        user_id: int | None = None,
        counter_id: int | None = None,
    ) -> TicketStatusHistory:
        """Aplica a transição na sessão atual (o commit é do chamador)."""
        cls.ensure_transition(ticket.status, target)
        now = utcnow()
        entry = TicketStatusHistory(
            ticket_id=ticket.id,
            from_status=ticket.status,
            to_status=target,
            user_id=user_id,
            counter_id=counter_id,
            created_at=now,
        )
        ticket.status = target
        ticket.updated_at = now
        db.session.add(entry)
        return entry
