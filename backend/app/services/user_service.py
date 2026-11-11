from __future__ import annotations

from app.extensions import db
from app.models import User, UserRole
from app.repositories import CounterRepository, UserRepository
from app.schemas.user import UserCreate, UserListQuery, UserUpdate
from app.services.audit_service import AuditService
from app.utils.db import paginate, run_in_transaction
from app.utils.errors import BusinessRuleError, ConflictError, NotFoundError, ValidationError


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

    @classmethod
    def create(cls, data: UserCreate, *, actor: User) -> User:
        if UserRepository.get_by_email(data.email):
            raise ConflictError("Já existe um usuário com este e-mail.", code="EMAIL_IN_USE")

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

        return run_in_transaction(tx)

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
        if user.role == UserRole.ADMIN and demoting:
            if user.id == actor.id:
                raise BusinessRuleError("Você não pode desativar nem rebaixar o próprio usuário.", code="SELF_LOCKOUT")
            if UserRepository.count_active_admins() <= 1:
                raise BusinessRuleError("O sistema precisa de pelo menos um administrador ativo.", code="LAST_ADMIN")

        def tx() -> User:
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

        return run_in_transaction(tx)

    @classmethod
    def assign_counters(cls, user_id: int, counter_ids: list[int], *, actor: User) -> User:
        user = cls.get(user_id)

        def tx() -> User:
            user.counters = cls._resolve_counters(counter_ids)
            AuditService.record(
                "USER_COUNTERS_ASSIGNED", "user", user.id, user_id=actor.id,
                details={"counter_ids": [c.id for c in user.counters]},
            )
            return user

        return run_in_transaction(tx)
