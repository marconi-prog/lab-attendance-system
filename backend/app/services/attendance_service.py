"""Operação do guichê: sessão, início/fim de atendimento e ausência."""
from __future__ import annotations

from app.extensions import db
from app.models import Attendance, AttendanceResult, Call, CounterSession, Ticket, TicketStatus, User
from app.repositories import CallRepository, CounterRepository, TicketRepository
from app.services.audit_service import AuditService
from app.services.realtime import Events, RealtimeNotifier
from app.services.state_machine import TicketStateMachine
from app.utils.clock import utcnow
from app.utils.db import run_in_transaction
from app.utils.errors import BusinessRuleError, ConflictError, NotFoundError, PermissionDenied


class AttendanceService:
    # ------------------------------------------------------------- sessões
    @staticmethod
    def available_counters(user: User) -> list[tuple]:
        result = []
        for counter in user.counters:
            if not counter.active:
                continue
            session = CounterRepository.open_session_for_counter(counter.id)
            occupied_by = session.user if session and session.user_id != user.id else None
            result.append((counter, occupied_by))
        return result

    @staticmethod
    def current_session(user: User) -> CounterSession | None:
        return CounterRepository.open_session_for_user(user.id)

    @classmethod
    def require_session(cls, user: User) -> CounterSession:
        session = cls.current_session(user)
        if not session:
            raise BusinessRuleError("Selecione um guichê antes de operar o atendimento.", code="NO_COUNTER_SESSION")
        return session

    @staticmethod
    def open_session(user: User, counter_id: int) -> CounterSession:
        if not any(c.id == counter_id for c in user.counters):
            raise PermissionDenied("Você não está autorizado a operar este guichê.", code="COUNTER_NOT_AUTHORIZED")

        def tx() -> CounterSession:
            counter = CounterRepository.get_for_update(counter_id)  # serializa abertura no guichê
            if not counter or not counter.active:
                raise NotFoundError("Guichê não encontrado ou inativo.")
            occupying = CounterRepository.open_session_for_counter(counter_id)
            if occupying and occupying.user_id == user.id:
                return occupying
            if occupying:
                raise ConflictError(f"O guichê {counter.label} está em uso por {occupying.user.name}.", code="COUNTER_OCCUPIED")
            previous = CounterRepository.open_session_for_user(user.id)
            if previous:
                if TicketRepository.active_ticket_for_counter(previous.counter_id):
                    raise ConflictError(
                        "Finalize o atendimento em andamento antes de trocar de guichê.", code="ACTIVE_TICKET_PENDING"
                    )
                previous.closed_at = utcnow()
            session = CounterSession(counter_id=counter_id, user_id=user.id, opened_at=utcnow())
            db.session.add(session)
            db.session.flush()
            AuditService.record("COUNTER_SESSION_OPENED", "counter", counter_id, user_id=user.id)
            return session

        return run_in_transaction(tx)

    @staticmethod
    def close_session(user: User) -> None:
        def tx() -> None:
            session = CounterRepository.open_session_for_user(user.id)
            if not session:
                raise BusinessRuleError("Nenhum guichê aberto.", code="NO_COUNTER_SESSION")
            if TicketRepository.active_ticket_for_counter(session.counter_id):
                raise ConflictError("Finalize o atendimento em andamento antes de sair do guichê.", code="ACTIVE_TICKET_PENDING")
            session.closed_at = utcnow()
            AuditService.record("COUNTER_SESSION_CLOSED", "counter", session.counter_id, user_id=user.id)

        run_in_transaction(tx)

    @staticmethod
    def force_close_session(admin: User, session_id: int) -> None:
        def tx() -> None:
            session = db.session.get(CounterSession, session_id, with_for_update=True)
            if not session or session.closed_at:
                raise NotFoundError("Sessão de guichê não encontrada ou já encerrada.")
            session.closed_at = utcnow()
            AuditService.record(
                "COUNTER_SESSION_FORCE_CLOSED", "counter", session.counter_id, user_id=admin.id,
                details={"session_id": session.id, "attendant_id": session.user_id},
            )

        run_in_transaction(tx)

    # --------------------------------------------------------- estado atual
    @staticmethod
    def current_ticket(session: CounterSession) -> tuple[Ticket, Call] | None:
        ticket = TicketRepository.active_ticket_for_counter(session.counter_id)
        if not ticket:
            return None
        return ticket, CallRepository.last_for_ticket(ticket.id)

    @staticmethod
    def lock_owned_ticket(ticket_id: int, session: CounterSession) -> tuple[Ticket, Call]:
        """Bloqueia a senha e garante que ela foi chamada por este guichê."""
        ticket = TicketRepository.get_for_update(ticket_id)
        if not ticket:
            raise NotFoundError("Senha não encontrada.")
        last_call = CallRepository.last_for_ticket(ticket.id)
        if not last_call or last_call.counter_id != session.counter_id:
            raise PermissionDenied("Esta senha não está vinculada ao seu guichê.", code="TICKET_NOT_OWNED")
        return ticket, last_call

    # ------------------------------------------------------------ comandos
    @classmethod
    def start(cls, *, user: User, session: CounterSession, ticket_id: int) -> Attendance:
        def tx() -> Attendance:
            ticket, _ = cls.lock_owned_ticket(ticket_id, session)
            TicketStateMachine.transition(ticket, TicketStatus.EM_ATENDIMENTO, user_id=user.id, counter_id=session.counter_id)
            attendance = Attendance(
                ticket_id=ticket.id, user_id=user.id, counter_id=session.counter_id,
                started_at=utcnow(), result=AttendanceResult.EM_ANDAMENTO,
            )
            db.session.add(attendance)
            db.session.flush()
            AuditService.record("ATTENDANCE_STARTED", "ticket", ticket.id, user_id=user.id, details={"code": ticket.code})
            return attendance

        attendance = run_in_transaction(tx)
        cls._publish(Events.ATTENDANCE_STARTED, attendance.ticket, session)
        return attendance

    @classmethod
    def finish(cls, *, user: User, session: CounterSession, ticket_id: int) -> Attendance:
        def tx() -> Attendance:
            ticket, _ = cls.lock_owned_ticket(ticket_id, session)
            TicketStateMachine.transition(ticket, TicketStatus.ATENDIDA, user_id=user.id, counter_id=session.counter_id)
            attendance = ticket.attendance
            now = utcnow()
            attendance.finished_at = now
            attendance.duration_seconds = max(0, int((now - attendance.started_at).total_seconds()))
            attendance.result = AttendanceResult.CONCLUIDO
            AuditService.record(
                "ATTENDANCE_FINISHED", "ticket", ticket.id, user_id=user.id,
                details={"code": ticket.code, "duration_seconds": attendance.duration_seconds},
            )
            return attendance

        attendance = run_in_transaction(tx)
        cls._publish(Events.ATTENDANCE_FINISHED, attendance.ticket, session)
        return attendance

    @classmethod
    def no_show(cls, *, user: User, session: CounterSession, ticket_id: int) -> Ticket:
        def tx() -> Ticket:
            ticket, _ = cls.lock_owned_ticket(ticket_id, session)
            if ticket.status == TicketStatus.CHAMADA:
                raise BusinessRuleError(
                    "Repita a chamada antes de registrar o não comparecimento (são necessárias duas chamadas).",
                    code="SECOND_CALL_REQUIRED",
                )
            TicketStateMachine.transition(ticket, TicketStatus.NAO_COMPARECEU, user_id=user.id, counter_id=session.counter_id)
            AuditService.record("TICKET_NO_SHOW", "ticket", ticket.id, user_id=user.id, details={"code": ticket.code})
            return ticket

        ticket = run_in_transaction(tx)
        cls._publish(Events.TICKET_UPDATED, ticket, session)
        return ticket

    @staticmethod
    def _publish(event: str, ticket: Ticket, session: CounterSession) -> None:
        from app.services.presenters import ticket_payload

        from app.services.panel_service import PanelService

        RealtimeNotifier.to_staff(event, {"ticket": ticket_payload(ticket), "counter_id": session.counter_id})
        PanelService.publish()  # atualiza "Em atendimento" no painel
