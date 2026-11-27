"""Uma requisição já autenticada deve revalidar a sessão ao reservar a senha."""
import pytest
from sqlalchemy import func, select

from app.extensions import db
from app.models import Call, Ticket, TicketStatus, User, UserRole
from app.schemas.user import UserUpdate
from app.services.attendance_service import AttendanceService
from app.services.queue_service import QueueService
from app.services.user_service import UserService
from app.utils.errors import PermissionDenied


@pytest.mark.parametrize('change', ['revoke', 'deactivate', 'close'])
def test_call_rejects_session_validated_before_access_was_removed(app, make_user, make_counter, issue, change):
    counter_id = make_counter()
    operator = make_user(counter_ids=[counter_id])
    manager = make_user(UserRole.ADMIN)
    ticket = issue('SP')

    with app.app_context():
        user = db.session.get(User, operator['id'])
        AttendanceService.open_session(user, counter_id)
        stale_session = AttendanceService.require_session(user)
        # A requisição mantém os dados validados antes de uma alteração concorrente.
        db.session.expunge(stale_session)

    with app.app_context():
        actor = db.session.get(User, manager['id'])
        if change == 'revoke':
            UserService.assign_counters(operator['id'], [], actor=actor)
        elif change == 'deactivate':
            UserService.update(operator['id'], UserUpdate(active=False), actor=actor)
        else:
            AttendanceService.close_session(db.session.get(User, operator['id']))

    with app.app_context():
        with pytest.raises(PermissionDenied):
            QueueService.call_next(user_id=operator['id'], session=stale_session)
        assert db.session.get(Ticket, ticket['id']).status == TicketStatus.AGUARDANDO
        assert db.session.scalar(select(func.count(Call.id))) == 0
