"""Mapa completo de URLs da API → controllers."""
from __future__ import annotations

from flask import Blueprint, Flask

from app.controllers import (
    admin_controller as admin,
    attendant_controller as attendant,
    auth_controller as auth,
    public_controller as public,
    report_controller as reports,
    ticket_controller as tickets,
)
from app.models import UserRole
from app.routes.registry import AUTHENTICATED, PUBLIC, api_route
from app.schemas.attendance import OpenSessionRequest
from app.schemas.auth import AccessTokenOut, ChangePasswordRequest, LoginRequest, LogoutRequest, TokenPairOut
from app.schemas.counter import CounterCreate, CounterOut, CounterSessionOut, CounterUpdate
from app.schemas.report import AuditQuery, DailyReportQuery, HistoryQuery, MonthlyReportQuery, ReportQuery
from app.schemas.ticket import IssuedTicketOut, TicketCreate, TicketDetailOut, TicketListQuery
from app.schemas.responses import (
    AttendanceResultOut,
    AttendantStateOut,
    AuditPageOut,
    AvailableCountersOut,
    CallResultOut,
    CloseDayOut,
    CounterListOut,
    CounterSessionListOut,
    DailyReportOut,
    DashboardOut,
    HealthOut,
    HistoryPageOut,
    MonthlyReportOut,
    PanelSnapshotOut,
    SummaryReportOut,
    SystemInfoOut,
    TicketPageOut,
    TicketResultOut,
    TicketTypesOut,
    UserPageOut,
)
from app.schemas.user import AssignCountersRequest, UserCreate, UserListQuery, UserOut, UserUpdate

ADMIN = (UserRole.ADMIN,)
ATTENDANT = (UserRole.ATTENDANT,)
STAFF = (UserRole.ADMIN, UserRole.ATTENDANT)

# ---------------------------------------------------------------- público
system_bp = Blueprint("system", __name__, url_prefix="/api")
api_route(system_bp, "/health", summary="Health check (aplicação + MySQL)", roles=PUBLIC, response=HealthOut)(public.health)
api_route(system_bp, "/panel", summary="Últimas 5 senhas chamadas (painel público)", roles=PUBLIC, response=PanelSnapshotOut)(public.panel)

# ------------------------------------------------------------------- auth
auth_bp = Blueprint("auth", __name__, url_prefix="/api/auth")
api_route(auth_bp, "/login", methods=["POST"], summary="Login (access + refresh token)", roles=PUBLIC,
          body=LoginRequest, response=TokenPairOut, errors=[401, 422])(auth.login)
api_route(auth_bp, "/refresh", methods=["POST"], summary="Novo access token a partir do refresh token",
          refresh=True, response=AccessTokenOut, errors=[401])(auth.refresh)
api_route(auth_bp, "/logout", methods=["POST"], summary="Revoga o access token (e o refresh token, se enviado)",
          body=LogoutRequest, status=204, errors=[401])(auth.logout)
api_route(auth_bp, "/me", summary="Usuário autenticado", response=UserOut, errors=[401])(auth.me)
api_route(auth_bp, "/password", methods=["PUT"], summary="Alterar a própria senha",
          body=ChangePasswordRequest, status=204, errors=[401, 422])(auth.change_password)

# ---------------------------------------------------------------- senhas
tickets_bp = Blueprint("tickets", __name__, url_prefix="/api/tickets")
api_route(tickets_bp, "", methods=["POST"], summary="Emitir senha (totem — sem autenticação)", roles=PUBLIC,
          body=TicketCreate, response=IssuedTicketOut, status=201, errors=[422])(tickets.issue)
api_route(tickets_bp, "/types", summary="Categorias de senha e disponibilidade de emissão", roles=PUBLIC, response=TicketTypesOut)(tickets.types)
api_route(tickets_bp, "", summary="Listar senhas (filtros: date, status, type)", roles=STAFF,
          query=TicketListQuery, response=TicketPageOut)(tickets.list_tickets)
api_route(tickets_bp, "/<int:ticket_id>", summary="Detalhe da senha com chamadas e histórico de estados",
          roles=STAFF, response=TicketDetailOut, errors=[404])(tickets.get_ticket)

# ----------------------------------------------------------- atendimento
attendant_bp = Blueprint("attendant", __name__, url_prefix="/api/attendant")
api_route(attendant_bp, "/state", summary="Estado do atendente: guichê, senha atual e fila", roles=ATTENDANT,
          response=AttendantStateOut)(attendant.state)
api_route(attendant_bp, "/counters", summary="Guichês autorizados e ocupação", roles=ATTENDANT,
          response=AvailableCountersOut)(attendant.counters)
api_route(attendant_bp, "/session", methods=["POST"], summary="Assumir um guichê autorizado", roles=ATTENDANT,
          body=OpenSessionRequest, response=CounterSessionOut, status=201, errors=[403, 404, 409])(attendant.open_session)
api_route(attendant_bp, "/session", methods=["DELETE"], summary="Sair do guichê", roles=ATTENDANT,
          status=204, errors=[409, 422])(attendant.close_session)
api_route(attendant_bp, "/call-next", methods=["POST"], summary="Chamar a próxima senha (QueueService)", roles=ATTENDANT,
          response=CallResultOut, errors=[409, 422])(attendant.call_next)
api_route(attendant_bp, "/tickets/<int:ticket_id>/recall", methods=["POST"], summary="Repetir chamada (última chamada)",
          roles=ATTENDANT, response=CallResultOut, errors=[403, 404, 422])(attendant.recall)
api_route(attendant_bp, "/tickets/<int:ticket_id>/start", methods=["POST"], summary="Iniciar atendimento",
          roles=ATTENDANT, response=AttendanceResultOut, errors=[403, 404, 422])(attendant.start)
api_route(attendant_bp, "/tickets/<int:ticket_id>/finish", methods=["POST"], summary="Finalizar atendimento",
          roles=ATTENDANT, response=AttendanceResultOut, errors=[403, 404, 422])(attendant.finish)
api_route(attendant_bp, "/tickets/<int:ticket_id>/no-show", methods=["POST"],
          summary="Registrar não comparecimento (após a 2ª chamada)", roles=ATTENDANT, response=TicketResultOut,
          errors=[403, 404, 422])(attendant.no_show)

# ------------------------------------------------------------------ gestão
users_bp = Blueprint("users", __name__, url_prefix="/api/users")
api_route(users_bp, "", summary="Listar usuários", roles=ADMIN, query=UserListQuery, response=UserPageOut)(admin.list_users)
api_route(users_bp, "", methods=["POST"], summary="Criar usuário", roles=ADMIN, body=UserCreate,
          response=UserOut, status=201, errors=[409, 422])(admin.create_user)
api_route(users_bp, "/<int:user_id>", summary="Detalhar usuário", roles=ADMIN, response=UserOut, errors=[404])(admin.get_user)
api_route(users_bp, "/<int:user_id>", methods=["PATCH"], summary="Atualizar usuário (inclui ativar/desativar e redefinir senha)",
          roles=ADMIN, body=UserUpdate, response=UserOut, errors=[404, 409, 422])(admin.update_user)
api_route(users_bp, "/<int:user_id>/counters", methods=["PUT"], summary="Definir guichês autorizados do usuário",
          roles=ADMIN, body=AssignCountersRequest, response=UserOut, errors=[404, 422])(admin.assign_counters)

counters_bp = Blueprint("counters", __name__, url_prefix="/api/counters")
api_route(counters_bp, "", summary="Listar guichês", roles=STAFF, response=CounterListOut)(admin.list_counters)
api_route(counters_bp, "", methods=["POST"], summary="Criar guichê", roles=ADMIN, body=CounterCreate,
          response=CounterOut, status=201, errors=[409, 422])(admin.create_counter)
api_route(counters_bp, "/<int:counter_id>", methods=["PATCH"], summary="Atualizar guichê", roles=ADMIN,
          body=CounterUpdate, response=CounterOut, errors=[404, 409, 422])(admin.update_counter)
api_route(counters_bp, "/sessions", summary="Sessões de guichê abertas", roles=ADMIN,
          response=CounterSessionListOut)(admin.list_sessions)
api_route(counters_bp, "/sessions/<int:session_id>", methods=["DELETE"], summary="Encerrar sessão de guichê (forçado)",
          roles=ADMIN, status=204, errors=[404])(admin.force_close_session)

reports_bp = Blueprint("reports", __name__, url_prefix="/api/reports")
api_route(reports_bp, "/summary", summary="Resumo por período e categoria", roles=ADMIN, query=ReportQuery,
          response=SummaryReportOut)(reports.summary)
api_route(reports_bp, "/daily", summary="Relatório diário", roles=ADMIN, query=DailyReportQuery,
          response=DailyReportOut)(reports.daily)
api_route(reports_bp, "/monthly", summary="Relatório mensal (com detalhamento por dia)", roles=ADMIN,
          query=MonthlyReportQuery, response=MonthlyReportOut)(reports.monthly)
api_route(reports_bp, "/attendances", summary="Histórico de atendimentos (paginado)", roles=ADMIN,
          query=HistoryQuery, response=HistoryPageOut)(reports.history)

admin_bp = Blueprint("admin", __name__, url_prefix="/api/admin")
api_route(admin_bp, "/dashboard", summary="Indicadores do dia", roles=ADMIN, response=DashboardOut)(admin.dashboard)
api_route(admin_bp, "/system", summary="Informações gerais do sistema", roles=ADMIN, response=SystemInfoOut)(admin.system_info)
api_route(admin_bp, "/audit-logs", summary="Consultar auditoria", roles=ADMIN, query=AuditQuery,
          response=AuditPageOut)(admin.list_audit_logs)
api_route(admin_bp, "/close-day", methods=["POST"], summary="Encerrar expediente: descarta senhas aguardando",
          roles=ADMIN, response=CloseDayOut)(admin.close_day)

TAGS = {"system": "Sistema", "auth": "Autenticação", "tickets": "Senhas", "attendant": "Atendimento", "users": "Usuários", "counters": "Guichês", "reports": "Relatórios", "admin": "Administração"}

BLUEPRINTS = [system_bp, auth_bp, tickets_bp, attendant_bp, users_bp, counters_bp, reports_bp, admin_bp]


def register_routes(app: Flask) -> None:
    for bp in BLUEPRINTS:
        app.register_blueprint(bp)
    from app.docs import docs_bp

    app.register_blueprint(docs_bp)


__all__ = ["AUTHENTICATED", "register_routes"]
