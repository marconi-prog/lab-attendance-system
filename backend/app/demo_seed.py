"""Carga de DEMONSTRAÇÃO: ``flask seed-demo``.

Cria, apenas para apresentações em ambiente de desenvolvimento, um gestor
(perfil ADMIN) e um atendente (perfil ATTENDANT) com permissão em guichê(s).

Garantias:

* **opt-in explícito**: exige ``--confirm-demo`` (``--dry-run`` só consulta);
* **recusado fora de desenvolvimento**: exige ``FLASK_ENV=development`` e a
  configuração carregada de desenvolvimento; ``production`` é sempre recusado;
* **idempotente**: contas e guichês já existentes e compatíveis são
  reaproveitados sem nenhuma alteração;
* **nunca apaga, sobrescreve nem redefine senhas**: uma conta existente
  incompatível (perfil, situação ou permissões diferentes) ou um guichê
  inativo abortam a execução antes de qualquer gravação;
* **senhas fora do código**: lidas de ``DEMO_MANAGER_PASSWORD`` /
  ``DEMO_ATTENDANT_PASSWORD`` ou digitadas (getpass, com confirmação), e
  pedidas somente para contas que serão criadas;
* **validação forte**: nomes, e-mails e senhas validados com as mesmas regras
  da API, mais restrições próprias da demonstração;
* **transação atômica**: guichês, contas, permissões e auditoria são gravados
  numa única transação — ou tudo, ou nada;
* **não emite senhas de atendimento**: a emissão é feita pelo totem, como no
  uso real; o comando apenas imprime o roteiro com os horários configurados.
"""
from __future__ import annotations

import getpass
import os
from dataclasses import dataclass, field
from datetime import time

import click
from flask import current_app
from flask.cli import with_appcontext
from pydantic import TypeAdapter
from pydantic import ValidationError as PydanticValidationError
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.extensions import db
from app.models import Counter, User, UserRole
from app.repositories import UserRepository
from app.schemas.common import Email
from app.schemas.user import validate_password_strength
from app.services.audit_service import AuditService
from app.utils.db import run_in_transaction

ALLOWED_ENV = "development"
MANAGER_PASSWORD_ENV = "DEMO_MANAGER_PASSWORD"
ATTENDANT_PASSWORD_ENV = "DEMO_ATTENDANT_PASSWORD"
PASSWORD_MAX_LENGTH = 128  # mesmo limite dos schemas da API
NAME_MIN_LENGTH, NAME_MAX_LENGTH = 2, 120  # mesmos limites de UserCreate

DEFAULT_MANAGER_NAME = "Gestor(a) de Demonstração"
DEFAULT_MANAGER_EMAIL = "gestor.demo@laboratorio.local"
DEFAULT_ATTENDANT_NAME = "Atendente de Demonstração"
DEFAULT_ATTENDANT_EMAIL = "atendente.demo@laboratorio.local"

NO_CHANGES = "Nenhum dado foi alterado."

_email_adapter = TypeAdapter(Email)


@dataclass(frozen=True)
class AccountSpec:
    key: str  # rótulo exibido: "gestor" | "atendente"
    name: str
    email: str
    role: UserRole
    password_env: str
    counter_numbers: tuple[int, ...] = ()


@dataclass
class Plan:
    counters_to_create: list[int] = field(default_factory=list)
    counters_reused: list[int] = field(default_factory=list)
    accounts_to_create: list[str] = field(default_factory=list)
    accounts_reused: dict[str, int] = field(default_factory=dict)
    problems: list[str] = field(default_factory=list)

    def signature(self) -> tuple:
        return (
            tuple(self.counters_to_create),
            tuple(self.counters_reused),
            tuple(self.accounts_to_create),
            tuple(sorted(self.accounts_reused.items())),
        )

    @property
    def has_work(self) -> bool:
        return bool(self.counters_to_create or self.accounts_to_create)


# --------------------------------------------------------------------- ambiente
def ensure_demo_environment() -> None:
    """Recusa a execução fora de desenvolvimento, antes de qualquer acesso ao banco."""
    raw = (os.getenv("FLASK_ENV") or "").strip().lower()
    configured = str(current_app.config.get("ENV_NAME") or "").strip().lower()
    state = f"FLASK_ENV={raw or 'não definido'}, configuração carregada={configured or 'desconhecida'}"
    if raw == "production" or configured == "production":
        raise click.ClickException(f"seed-demo é recusado em produção ({state}). {NO_CHANGES}")
    if raw != ALLOWED_ENV or configured != ALLOWED_ENV:
        raise click.ClickException(f"seed-demo só pode ser executado com FLASK_ENV=development ({state}). {NO_CHANGES}")


# --------------------------------------------------------------------- validação
def _validated_name(value: str, key: str) -> str:
    name = " ".join(value.split())
    if not NAME_MIN_LENGTH <= len(name) <= NAME_MAX_LENGTH:
        raise click.ClickException(
            f"Nome do {key} deve ter entre {NAME_MIN_LENGTH} e {NAME_MAX_LENGTH} caracteres. {NO_CHANGES}"
        )
    return name


def _validated_email(value: str, key: str) -> str:
    try:
        return _email_adapter.validate_python(value)
    except PydanticValidationError as exc:
        raise click.ClickException(f"E-mail do {key} inválido: {value!r}. {NO_CHANGES}") from exc


def validate_demo_password(password: str, spec: AccountSpec) -> str:
    """Política da API (>= 8 caracteres, letras e números, <= 128) + regras da demonstração."""
    prefix = f"Senha do {spec.key} rejeitada:"
    if len(password) > PASSWORD_MAX_LENGTH:
        raise click.ClickException(f"{prefix} máximo de {PASSWORD_MAX_LENGTH} caracteres. {NO_CHANGES}")
    if password != password.strip():
        # A API remove espaços das pontas no login; uma senha assim nunca autenticaria.
        raise click.ClickException(f"{prefix} não pode começar nem terminar com espaço. {NO_CHANGES}")
    try:
        validate_password_strength(password)
    except ValueError as exc:
        raise click.ClickException(f"{prefix} {exc}. {NO_CHANGES}") from exc
    local_part = spec.email.split("@", 1)[0].lower()
    if len(local_part) >= 3 and local_part in password.lower():
        raise click.ClickException(f"{prefix} não pode conter o identificador do e-mail. {NO_CHANGES}")
    return password


def _read_password(spec: AccountSpec) -> str:
    password = os.getenv(spec.password_env)
    if not password:
        password = getpass.getpass(f"Senha para o {spec.key} ({spec.email}): ")
        confirmation = getpass.getpass("Confirme a senha: ")
        if password != confirmation:
            raise click.ClickException(f"As senhas do {spec.key} não conferem. {NO_CHANGES}")
    return validate_demo_password(password, spec)


# --------------------------------------------------------------------- planejamento
def build_plan(specs: list[AccountSpec], counter_numbers: tuple[int, ...]) -> Plan:
    """Somente leitura: decide o que criar, o que reaproveitar e o que é incompatível."""
    plan = Plan()
    for number in counter_numbers:
        counter = db.session.scalars(select(Counter).where(Counter.number == number)).first()
        if counter is None:
            plan.counters_to_create.append(number)
        elif not counter.active:
            plan.problems.append(
                f"Guichê {number:02d} existe, mas está inativo (não será reativado automaticamente). "
                "Ative-o na área do gestor ou escolha outro com --counter."
            )
        else:
            plan.counters_reused.append(number)

    for spec in specs:
        user = UserRepository.get_by_email(spec.email)
        if user is None:
            plan.accounts_to_create.append(spec.key)
            continue
        issues = []
        if user.role != spec.role:
            issues.append(f"perfil {user.role.value} (esperado {spec.role.value})")
        if not user.active:
            issues.append("conta inativa")
        if spec.counter_numbers:
            authorized = {counter.number for counter in user.counters}
            missing = sorted(set(spec.counter_numbers) - authorized)
            if missing:
                issues.append("sem permissão no(s) guichê(s) " + ", ".join(f"{n:02d}" for n in missing))
        if issues:
            plan.problems.append(
                f"Conta existente {user.email} ({spec.key}) é incompatível: {'; '.join(issues)}. "
                "Ela não será alterada; ajuste-a na área do gestor ou use outro e-mail."
            )
        else:
            plan.accounts_reused[spec.key] = user.id
    return plan


def apply_plan(
    specs: list[AccountSpec],
    counter_numbers: tuple[int, ...],
    expected: tuple,
    passwords: dict[str, str],
) -> Plan:
    """Grava tudo numa única transação. Qualquer falha desfaz todas as gravações."""

    def tx() -> Plan:
        plan = build_plan(specs, counter_numbers)  # revalida dentro da transação de escrita
        if plan.problems or plan.signature() != expected:
            raise click.ClickException(
                f"O banco foi alterado durante a execução. {NO_CHANGES} Execute o comando novamente."
            )
        for number in plan.counters_to_create:
            counter = Counter(name=f"Guichê {number:02d}", number=number, active=True)
            db.session.add(counter)
            db.session.flush()
            AuditService.record("DEMO_SEED_COUNTER_CREATED", "counter", counter.id, details={"number": number})

        by_number = {
            counter.number: counter
            for counter in db.session.scalars(select(Counter).where(Counter.number.in_(counter_numbers)))
        }
        for spec in specs:
            if spec.key not in plan.accounts_to_create:
                continue
            user = User(name=spec.name, email=spec.email, role=spec.role, active=True)
            user.set_password(passwords[spec.key])
            user.counters = [by_number[number] for number in spec.counter_numbers]
            db.session.add(user)
            db.session.flush()
            AuditService.record(
                "DEMO_SEED_USER_CREATED", "user", user.id,
                details={"email": user.email, "role": user.role.value, "counter_numbers": list(spec.counter_numbers)},
            )
        return plan

    try:
        return run_in_transaction(tx)
    except IntegrityError as exc:  # corrida com outra execução/cadastro simultâneo
        raise click.ClickException(f"Conflito de unicidade (e-mail ou número de guichê). {NO_CHANGES}") from exc


# --------------------------------------------------------------------- saída
def _fmt_time(value, default: str) -> str:
    return value.strftime("%H:%M") if isinstance(value, time) else default


def _echo_plan(plan: Plan, specs: list[AccountSpec], *, dry_run: bool) -> None:
    verb = "seria(m) criado(s)" if dry_run else "criado(s)"
    if plan.counters_to_create:
        click.echo(f"Guichê(s) {verb}: " + ", ".join(f"{n:02d}" for n in plan.counters_to_create))
    if plan.counters_reused:
        click.echo("Guichê(s) já existente(s), sem alteração: " + ", ".join(f"{n:02d}" for n in plan.counters_reused))
    for spec in specs:
        counters = f" — guichê(s) {', '.join(f'{n:02d}' for n in spec.counter_numbers)}" if spec.counter_numbers else ""
        if spec.key in plan.accounts_to_create:
            click.echo(f"Conta {verb}: {spec.key} <{spec.email}> perfil {spec.role.value}{counters}")
        else:
            click.echo(f"Conta já existente, sem alteração (senha mantida): {spec.key} <{spec.email}>")


def _echo_script(specs: list[AccountSpec]) -> None:
    cfg = current_app.config
    issue_open = _fmt_time(cfg.get("TICKET_ISSUE_OPEN_TIME"), "06:00")
    call_open = _fmt_time(cfg.get("BUSINESS_OPEN_TIME"), "07:00")
    close = _fmt_time(cfg.get("BUSINESS_CLOSE_TIME"), "17:00")
    tz = cfg.get("TIMEZONE", "America/Recife")
    enforced = bool(cfg.get("ENFORCE_BUSINESS_HOURS", True))
    manager, attendant = specs
    counters = ", ".join(f"{n:02d}" for n in attendant.counter_numbers)
    click.echo("")
    click.echo("Nenhuma senha de atendimento foi emitida por este comando. Roteiro sugerido:")
    click.echo(f"  1. Totem (/totem): emita senhas SP, SE e SG — emissão das {issue_open} às {close} ({tz}).")
    click.echo(f"  2. Login (/login) como {attendant.email}: escolha o guichê {counters} e use \"Chamar próxima\""
               f" — chamadas das {call_open} às {close}.")
    click.echo("  3. Painel (/panel): clique uma vez para liberar o áudio e acompanhe as chamadas.")
    click.echo(f"  4. Login como {manager.email}: indicadores, relatórios, usuários, guichês e auditoria.")
    if enforced:
        click.echo("  Horário aplicado (ENFORCE_BUSINESS_HOURS=true). Fora dele, apenas em ambiente de demonstração,"
                   " use ENFORCE_BUSINESS_HOURS=false.")
    else:
        click.echo("  Atenção: ENFORCE_BUSINESS_HOURS=false — o horário de funcionamento NÃO está sendo aplicado.")


# --------------------------------------------------------------------- comando
@click.command("seed-demo")
@click.option("--confirm-demo", is_flag=True, help="Obrigatório: confirma que o banco é de DEMONSTRAÇÃO.")
@click.option("--dry-run", is_flag=True, help="Apenas mostra o que seria feito; não grava e não pede senhas.")
@click.option("--manager-name", default=DEFAULT_MANAGER_NAME, show_default=True, help="Nome do gestor (ADMIN).")
@click.option("--manager-email", default=DEFAULT_MANAGER_EMAIL, show_default=True, help="E-mail do gestor.")
@click.option("--attendant-name", default=DEFAULT_ATTENDANT_NAME, show_default=True, help="Nome do atendente.")
@click.option("--attendant-email", default=DEFAULT_ATTENDANT_EMAIL, show_default=True, help="E-mail do atendente.")
@click.option(
    "--counter", "counter_numbers", type=click.IntRange(1, 99), multiple=True, default=(1,), show_default=True,
    help="Número do guichê autorizado ao atendente (repita a opção para vários).",
)
@with_appcontext
def seed_demo_command(
    confirm_demo: bool,
    dry_run: bool,
    manager_name: str,
    manager_email: str,
    attendant_name: str,
    attendant_email: str,
    counter_numbers: tuple[int, ...],
) -> None:
    """[DEMONSTRAÇÃO] Cria gestor e atendente com guichê, sem apagar nem sobrescrever dados.

    Senhas: DEMO_MANAGER_PASSWORD / DEMO_ATTENDANT_PASSWORD ou digitadas no terminal.
    Recusado fora de FLASK_ENV=development. Não emite senhas de atendimento.
    """
    ensure_demo_environment()
    if not (confirm_demo or dry_run):
        raise click.ClickException(
            f"Comando de demonstração: informe --confirm-demo para executar (ou --dry-run para simular). {NO_CHANGES}"
        )

    counters = tuple(sorted(set(counter_numbers)))
    manager = AccountSpec(
        "gestor", _validated_name(manager_name, "gestor"), _validated_email(manager_email, "gestor"),
        UserRole.ADMIN, MANAGER_PASSWORD_ENV,
    )
    attendant = AccountSpec(
        "atendente", _validated_name(attendant_name, "atendente"), _validated_email(attendant_email, "atendente"),
        UserRole.ATTENDANT, ATTENDANT_PASSWORD_ENV, counters,
    )
    if manager.email == attendant.email:
        raise click.ClickException(f"Gestor e atendente precisam de e-mails diferentes. {NO_CHANGES}")
    specs = [manager, attendant]

    try:
        plan = build_plan(specs, counters)
    finally:
        db.session.rollback()  # encerra a leitura antes de qualquer interação com o terminal
    if plan.problems:
        raise click.ClickException("\n".join(["Execução abortada:", *plan.problems, NO_CHANGES]))

    click.echo("[DEMONSTRAÇÃO] seed-demo — nada é apagado e nenhuma senha existente é redefinida.")
    if dry_run:
        _echo_plan(plan, specs, dry_run=True)
        click.echo(f"--dry-run: {NO_CHANGES}")
        return

    for spec in specs:
        if spec.key in plan.accounts_reused and os.getenv(spec.password_env):
            click.echo(f"{spec.password_env} ignorada: a senha da conta existente NÃO foi alterada.")

    if not plan.has_work:
        _echo_plan(plan, specs, dry_run=False)
        click.echo(f"Tudo já estava preparado. {NO_CHANGES}")
        _echo_script(specs)
        return

    passwords = {spec.key: _read_password(spec) for spec in specs if spec.key in plan.accounts_to_create}
    if len(passwords) == 2 and passwords["gestor"] == passwords["atendente"]:
        raise click.ClickException(f"Use senhas diferentes para gestor e atendente. {NO_CHANGES}")

    applied = apply_plan(specs, counters, plan.signature(), passwords)
    _echo_plan(applied, specs, dry_run=False)
    _echo_script(specs)
