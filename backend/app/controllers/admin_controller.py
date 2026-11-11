"""Gestão: usuários, guichês, auditoria, painel do gestor e sistema."""
from __future__ import annotations

from flask_jwt_extended import current_user

from app.repositories import AuditRepository
from app.schemas.counter import CounterCreate, CounterOut, CounterSessionOut, CounterUpdate
from app.schemas.common import serialize_local
from app.schemas.report import AuditQuery
from app.schemas.user import AssignCountersRequest, UserCreate, UserListQuery, UserOut, UserUpdate
from app.services.attendance_service import AttendanceService
from app.services.counter_service import CounterService
from app.services.dashboard_service import DashboardService
from app.services.day_closing_service import DayClosingService
from app.services.user_service import UserService
from app.utils.clock import local_day_bounds_utc
from app.utils.db import page_meta, paginate


# ------------------------------------------------------------------ usuários
def list_users(query: UserListQuery):
    items, total = UserService.list(query)
    return {"items": [UserOut.model_validate(u).model_dump(mode="json") for u in items], "meta": page_meta(query.page, query.per_page, total)}


def get_user(user_id: int):
    return UserOut.model_validate(UserService.get(user_id))


def create_user(body: UserCreate):
    return UserOut.model_validate(UserService.create(body, actor=current_user)), 201


def update_user(user_id: int, body: UserUpdate):
    return UserOut.model_validate(UserService.update(user_id, body, actor=current_user))


def assign_counters(user_id: int, body: AssignCountersRequest):
    return UserOut.model_validate(UserService.assign_counters(user_id, body.counter_ids, actor=current_user))


# ------------------------------------------------------------------ guichês
def list_counters():
    return {"items": [CounterOut.model_validate(c).model_dump(mode="json") for c in CounterService.list()]}


def create_counter(body: CounterCreate):
    return CounterOut.model_validate(CounterService.create(body, actor=current_user)), 201


def update_counter(counter_id: int, body: CounterUpdate):
    return CounterOut.model_validate(CounterService.update(counter_id, body, actor=current_user))


def list_sessions():
    return {"items": [CounterSessionOut.model_validate(s).model_dump(mode="json") for s in CounterService.open_sessions()]}


def force_close_session(session_id: int):
    AttendanceService.force_close_session(current_user, session_id)
    return None


# ----------------------------------------------------------------- auditoria
def list_audit_logs(query: AuditQuery):
    start = local_day_bounds_utc(query.start_date)[0] if query.start_date else None
    end = local_day_bounds_utc(query.end_date)[1] if query.end_date else None
    stmt = AuditRepository.list(user_id=query.user_id, action=query.action, entity=query.entity, start_utc=start, end_utc=end)
    items, total = paginate(stmt, query.page, query.per_page)
    return {
        "items": [
            {
                "id": log.id,
                "user": {"id": log.user.id, "name": log.user.name} if log.user else None,
                "action": log.action,
                "entity": log.entity,
                "entity_id": log.entity_id,
                "details": log.details,
                "ip_address": log.ip_address,
                "created_at": serialize_local(log.created_at),
            }
            for log in items
        ],
        "meta": page_meta(query.page, query.per_page, total),
    }


# ----------------------------------------------------------- painel/sistema
def dashboard():
    return DashboardService.overview()


def system_info():
    return DashboardService.system_info()


def close_day():
    discarded = DayClosingService.close_today(user_id=current_user.id)
    return {"discarded": discarded}
