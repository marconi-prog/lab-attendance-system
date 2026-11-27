from __future__ import annotations

from sqlalchemy.exc import IntegrityError

from app.extensions import db
from app.models import User, UserRole
from app.models.user import is_active_manager_conflict
from app.repositories import CounterRepository, TicketRepository, UserRepository
from app.schemas.user import UserCreate, UserListQuery, UserUpdate
from app.services.audit_service import AuditService
from app.utils.clock import utcnow
from app.utils.db import paginate, run_in_transaction
from app.utils.errors import BusinessRuleError, ConflictError, NotFoundError, ValidationError

ACTIVE_MANAGER_EXISTS_MESSAGE = (
    "Já existe um gestor ativo: o sistema permite apenas um gestor ativo por vez. Nenhum dado foi alterado."
)


def _active_manager_conflict() -> ConflictError:
    return ConflictError(ACTIVE_MANAGER_EXISTS_MESSAGE, code="ACTIVE_MANAGER_EXISTS")


class UserService:
    @staticmethod
    def list(query: UserListQuery):
        stmt = UserRepository.list(search=query.search, role=query.role, active=query.active)
        return paginate(stmt, query.page, query.per_page)

    @staticmethod
    def get(user_id: int) -> User:
        user = UserRepository.get(user_id)
        if not user:
            raise NotFoundError("Usuário não encontrado.")
        return user

    @staticmethod
    def _resolve_counters(counter_ids: list[int]):
        unique_ids = sorted(set(counter_ids))
        counters = CounterRepository.get_many(unique_ids) if unique_ids else []
        if len(counters) != len(unique_ids):
            missing = set(unique_ids) - {c.id for c in counters}
            raise ValidationError("Guichê(s) inexistente(s).", details={"counter_ids": sorted(missing)})
        return counters

    @staticmethod
    def _ensure_no_other_active_manager(user_id: int | None = None) -> None:
        if UserRepository.active_manager(exclude_id=user_id):
            raise _active_manager_conflict()

    @staticmethod
    def _commit(tx):
        """run_in_transaction + tradução do índice de gestor único (corrida entre requisições) em 409."""
        try:
            return run_in_transaction(tx)
        except IntegrityError as exc:  # run_in_transaction já fez o rollback
            if is_active_manager_conflict(exc):
                raise _active_manager_conflict() from exc
            raise

    @staticmethod
    def _release_counter_session(user: User, *, actor: User, reason: str, keep_counter_ids: frozenset[int] | set[int] = frozenset()) -> None:
        """Encerra (na transação do chamador) a sessão de guichê que o usuário deixará de poder operar.

        Recusado se houver senha chamada/em atendimento naquele guichê.
        """
        session = CounterRepository.open_session_for_user(user.id)
        if not session or session.counter_id in keep_counter_ids:
            return
        CounterRepository.get_for_update(session.counter_id)  # serializa com a abertura do guichê
        if TicketRepository.active_ticket_for_counter(session.counter_id):
            raise ConflictError(
                f"{user.name} tem senha em andamento no guichê {session.counter.label}. "
                "Finalize o atendimento antes desta alteração.",
                code="ACTIVE_TICKET_PENDING",
            )
        session.closed_at = utcnow()
        AuditService.record(
            "COUNTER_SESSION_FORCE_CLOSED", "counter", session.counter_id, user_id=actor.id,
            details={"session_id": session.id, "attendant_id": user.id, "reason": reason},
        )

    @classmethod
    def create(cls, data: UserCreate, *, actor: User) -> User:
        if UserRepository.get_by_email(data.email):
            raise ConflictError("Já existe um usuário com este e-mail.", code="EMAIL_IN_USE")
        if data.role == UserRole.ADMIN:
            cls._ensure_no_other_active_manager()

        def tx() -> User:
            user = User(name=data.name, email=data.email.lower(), role=data.role, active=True)
            user.set_password(data.password)
            user.counters = cls._resolve_counters(data.counter_ids)
            db.session.add(user)
            db.session.flush()
            AuditService.record(
                "USER_CREATED", "user", user.id, user_id=actor.id,
                details={"email": user.email, "role": user.role.value, "counter_ids": [c.id for c in user.counters]},
            )
            return user

        return cls._commit(tx)

    @classmethod
    def update(cls, user_id: int, data: UserUpdate, *, actor: User) -> User:
        user = cls.get(user_id)
        changes = data.model_dump(exclude_unset=True)
        if not changes:
            return user
        if "email" in changes and changes["email"]:
            other = UserRepository.get_by_email(changes["email"])
            if other and other.id != user.id:
                raise ConflictError("Já existe um usuário com este e-mail.", code="EMAIL_IN_USE")
        demoting = changes.get("role") not in (None, UserRole.ADMIN) or changes.get("active") is False
        # Protege o gestor ATIVO; um ADMIN já inativo pode voltar, p.ex., como atendente.
        if user.role == UserRole.ADMIN and user.active and demoting:
            if user.id == actor.id:
                raise BusinessRuleError("Você não pode desativar nem rebaixar o próprio usuário.", code="SELF_LOCKOUT")
            if UserRepository.count_active_admins() <= 1:
                raise BusinessRuleError("O sistema precisa de pelo menos um administrador ativo.", code="LAST_ADMIN")
        new_role = changes.get("role") or user.role
        new_active = user.active if changes.get("active") is None else changes["active"]
        if new_role == UserRole.ADMIN and new_active:  # criação de gestor por promoção ou reativação
            cls._ensure_no_other_active_manager(user.id)
        deactivating = user.active and not new_active

        def tx() -> User:
            if deactivating:  # conta inativa não autentica: não pode manter o guichê ocupado
                cls._release_counter_session(user, actor=actor, reason="USER_DEACTIVATED")
            for field in ("name", "role", "active"):
                if changes.get(field) is not None:
                    setattr(user, field, changes[field])
            if changes.get("email"):
                user.email = changes["email"].lower()
            if changes.get("password"):
                user.set_password(changes["password"])
            audit_details = {k: (v.value if hasattr(v, "value") else v) for k, v in changes.items()}
            AuditService.record("USER_UPDATED", "user", user.id, user_id=actor.id, details=audit_details)
            return user

        return cls._commit(tx)

    @classmethod
    def assign_counters(cls, user_id: int, counter_ids: list[int], *, actor: User) -> User:
        user = cls.get(user_id)

        def tx() -> User:
            counters = cls._resolve_counters(counter_ids)
            # Revogar o guichê em uso encerra a sessão: a autorização nunca é contornada.
            cls._release_counter_session(
                user, actor=actor, reason="COUNTER_AUTHORIZATION_REMOVED", keep_counter_ids={c.id for c in counters}
            )
            user.counters = counters
            AuditService.record(
                "USER_COUNTERS_ASSIGNED", "user", user.id, user_id=actor.id,
                details={"counter_ids": [c.id for c in user.counters]},
            )
            return user

        return run_in_transaction(tx)
