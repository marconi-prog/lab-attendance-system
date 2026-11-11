from __future__ import annotations

from app.extensions import db
from app.models import Counter, User
from app.repositories import CounterRepository, TicketRepository
from app.schemas.counter import CounterCreate, CounterUpdate
from app.services.audit_service import AuditService
from app.utils.db import run_in_transaction
from app.utils.errors import BusinessRuleError, ConflictError, NotFoundError


class CounterService:
    @staticmethod
    def list(active: bool | None = None) -> list[Counter]:
        return CounterRepository.list(active=active)

    @staticmethod
    def get(counter_id: int) -> Counter:
        counter = CounterRepository.get(counter_id)
        if not counter:
            raise NotFoundError("Guichê não encontrado.")
        return counter

    @staticmethod
    def create(data: CounterCreate, *, actor: User) -> Counter:
        if CounterRepository.get_by_number(data.number):
            raise ConflictError(f"Já existe o guichê número {data.number:02d}.", code="COUNTER_NUMBER_IN_USE")

        def tx() -> Counter:
            counter = Counter(name=data.name, number=data.number, active=True)
            db.session.add(counter)
            db.session.flush()
            AuditService.record("COUNTER_CREATED", "counter", counter.id, user_id=actor.id, details=data.model_dump())
            return counter

        return run_in_transaction(tx)

    @classmethod
    def update(cls, counter_id: int, data: CounterUpdate, *, actor: User) -> Counter:
        counter = cls.get(counter_id)
        changes = data.model_dump(exclude_unset=True, exclude_none=True)
        if "number" in changes and changes["number"] != counter.number:
            if CounterRepository.get_by_number(changes["number"]):
                raise ConflictError(f"Já existe o guichê número {changes['number']:02d}.", code="COUNTER_NUMBER_IN_USE")
        if changes.get("active") is False:
            if CounterRepository.open_session_for_counter(counter.id):
                raise BusinessRuleError("O guichê está em uso. Encerre a sessão antes de desativá-lo.", code="COUNTER_IN_USE")
            if TicketRepository.active_ticket_for_counter(counter.id):
                raise BusinessRuleError("O guichê possui atendimento em andamento.", code="COUNTER_IN_USE")

        def tx() -> Counter:
            for field, value in changes.items():
                setattr(counter, field, value)
            AuditService.record("COUNTER_UPDATED", "counter", counter.id, user_id=actor.id, details=changes)
            return counter

        return run_in_transaction(tx)

    @staticmethod
    def open_sessions():
        return CounterRepository.open_sessions()
