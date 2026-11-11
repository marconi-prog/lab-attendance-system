"""QueueService — regras de prioridade e reserva atômica da próxima senha.

Ciclo de atendimento: SP → (SE ou SG) → SP → (SE ou SG) → ...

  * Depois de uma SP, chama-se SE; sem SE, chama-se SG; sem ambas, SP de novo.
  * Depois de SE/SG (ou no início do dia), chama-se SP; sem SP, SE; sem SE, SG.
  * Categorias vazias são puladas — a fila nunca bloqueia.
  * Qualquer guichê atende qualquer categoria.

O "último tipo chamado" é global (compartilhado entre guichês) e fica em
queue_states. A linha do dia é bloqueada com FOR UPDATE durante a seleção,
serializando "chamar próxima" entre guichês: dois atendentes nunca recebem
a mesma senha e o ciclo é respeitado mesmo sob concorrência.
"""
from __future__ import annotations

from flask import current_app

from app.extensions import db
from app.models import Call, CounterSession, Ticket, TicketStatus, TicketType
from app.repositories import TicketRepository
from app.services.audit_service import AuditService
from app.services.business_hours import BusinessHours
from app.services.state_machine import TicketStateMachine
from app.utils.clock import local_today, utcnow
from app.utils.db import run_in_transaction
from app.utils.errors import BusinessRuleError, ConflictError

AFTER_PRIORITY = (TicketType.SE, TicketType.SG, TicketType.SP)
AFTER_REGULAR = (TicketType.SP, TicketType.SE, TicketType.SG)


class QueueService:
    # ------------------------------------------------------------------ regra
    @staticmethod
    def select_next_type(last_called: TicketType | None, waiting: dict[TicketType, int]) -> TicketType | None:
        """Função pura: decide a categoria da próxima chamada."""
        order = AFTER_PRIORITY if last_called == TicketType.SP else AFTER_REGULAR
        for ticket_type in order:
            if waiting.get(ticket_type, 0) > 0:
                return ticket_type
        return None

    # ------------------------------------------------------------- consultas
    @classmethod
    def summary(cls) -> dict:
        today = local_today()
        waiting = TicketRepository.waiting_counts(today)
        state = TicketRepository.get_queue_state(today)
        last = state.last_called_type if state else None
        next_type = cls.select_next_type(last, waiting)
        return {
            "waiting": {t.value: n for t, n in waiting.items()},
            "total_waiting": sum(waiting.values()),
            "next_type": next_type.value if next_type else None,
            "last_called_type": last.value if last else None,
            "calling_allowed": BusinessHours.is_calling_allowed(),
        }

    # -------------------------------------------------------------- comando
    @classmethod
    def call_next(cls, *, user_id: int, session: CounterSession) -> tuple[Ticket, Call]:
        BusinessHours.ensure_calling_allowed()
        today = local_today()
        TicketRepository.ensure_queue_state(today)
        counter_id = session.counter_id

        def tx() -> tuple[Ticket, Call]:
            state = TicketRepository.lock_queue_state(today)
            # Verificado após o bloqueio: um duplo clique não reserva duas senhas.
            active = TicketRepository.active_ticket_for_counter(counter_id)
            if active:
                raise ConflictError(
                    f"O guichê já possui a senha {active.short_code} em andamento. Finalize-a antes de chamar outra.",
                    code="COUNTER_BUSY",
                )
            waiting = TicketRepository.waiting_counts(today)
            next_type = cls.select_next_type(state.last_called_type, waiting)
            if next_type is None:
                raise BusinessRuleError("Não há senhas aguardando atendimento.", code="QUEUE_EMPTY")
            ticket = TicketRepository.lock_next_waiting(today, next_type)
            if ticket is None:  # proteção extra; não deve ocorrer com o bloqueio da fila
                raise ConflictError("A senha foi reservada por outro guichê. Tente novamente.", code="QUEUE_RACE")

            now = utcnow()
            TicketStateMachine.transition(ticket, TicketStatus.CHAMADA, user_id=user_id, counter_id=counter_id)
            call = Call(ticket_id=ticket.id, user_id=user_id, counter_id=counter_id, attempt_number=1, called_at=now)
            db.session.add(call)
            state.last_called_type = next_type
            AuditService.record(
                "TICKET_CALLED", "ticket", ticket.id, user_id=user_id,
                details={"code": ticket.code, "counter_id": counter_id, "attempt": 1},
            )
            db.session.flush()
            return ticket, call

        ticket, call = run_in_transaction(tx)
        db.session.refresh(call)
        cls._publish_call(ticket, call)
        return ticket, call

    @classmethod
    def recall(cls, *, user_id: int, session: CounterSession, ticket_id: int) -> tuple[Ticket, Call]:
        """Repete a chamada (2ª e última tentativa)."""
        max_attempts = current_app.config["MAX_CALL_ATTEMPTS"]

        def tx() -> tuple[Ticket, Call]:
            from app.services.attendance_service import AttendanceService

            ticket, last_call = AttendanceService.lock_owned_ticket(ticket_id, session)
            if last_call.attempt_number >= max_attempts:
                raise BusinessRuleError("Limite de chamadas atingido para esta senha.", code="MAX_CALLS_REACHED")
            TicketStateMachine.transition(ticket, TicketStatus.CHAMADA_NOVAMENTE, user_id=user_id, counter_id=session.counter_id)
            call = Call(
                ticket_id=ticket.id, user_id=user_id, counter_id=session.counter_id,
                attempt_number=last_call.attempt_number + 1, called_at=utcnow(),
            )
            db.session.add(call)
            AuditService.record(
                "TICKET_RECALLED", "ticket", ticket.id, user_id=user_id,
                details={"code": ticket.code, "counter_id": session.counter_id, "attempt": call.attempt_number},
            )
            db.session.flush()
            return ticket, call

        ticket, call = run_in_transaction(tx)
        db.session.refresh(call)
        cls._publish_call(ticket, call)
        return ticket, call

    @classmethod
    def _publish_call(cls, ticket: Ticket, call: Call) -> None:
        from app.services.panel_service import PanelService
        from app.services.presenters import call_payload
        from app.services.realtime import Events, RealtimeNotifier

        event = Events.TICKET_RECALLED if call.attempt_number > 1 else Events.TICKET_CALLED
        RealtimeNotifier.broadcast(event, call_payload(ticket, call))
        PanelService.publish()
        RealtimeNotifier.to_staff(Events.QUEUE_UPDATED, cls.summary())
