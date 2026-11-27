"""Comandos de linha de comando (flask <comando>)."""
from __future__ import annotations

import getpass
import os

import click
from flask import Flask
from sqlalchemy.exc import IntegrityError

from app.demo_seed import seed_demo_command
from app.extensions import db
from app.models import Counter, User, UserRole
from app.models.user import is_active_manager_conflict
from app.repositories import UserRepository
from app.schemas.user import validate_password_strength

NO_CHANGES = "Nenhum dado foi alterado."


def _manager_exists_error(manager: User | None = None) -> click.ClickException:
    who = f" (id={manager.id})" if manager else ""
    return click.ClickException(
        f"Já existe um gestor ativo{who}: o sistema permite apenas um gestor ativo. "
        f"Nenhuma conta existente é desativada ou rebaixada automaticamente. {NO_CHANGES}"
    )


def _read_password(env_var: str) -> str:
    password = os.getenv(env_var)
    if password:
        return password
    first = getpass.getpass("Senha: ")
    second = getpass.getpass("Confirme a senha: ")
    if first != second:
        raise click.ClickException("As senhas não conferem.")
    return first


def register_cli(app: Flask) -> None:
    @app.cli.command("create-admin")
    @click.option("--name", required=True, help="Nome do administrador")
    @click.option("--email", required=True, help="E-mail de login")
    def create_admin(name: str, email: str) -> None:
        """Cria o gestor (único ADMIN ativo). A senha é lida de ADMIN_PASSWORD ou solicitada no terminal."""
        if UserRepository.get_by_email(email):
            raise click.ClickException("Já existe um usuário com este e-mail.")
        manager = UserRepository.active_manager()
        if manager:  # antes de pedir a senha
            raise _manager_exists_error(manager)
        password = _read_password("ADMIN_PASSWORD")
        try:
            validate_password_strength(password)
        except ValueError as exc:
            raise click.ClickException(str(exc)) from exc
        user = User(name=name, email=email.lower(), role=UserRole.ADMIN, active=True)
        user.set_password(password)
        db.session.add(user)
        try:
            db.session.commit()
        except IntegrityError as exc:  # corrida com outro cadastro simultâneo
            db.session.rollback()
            if is_active_manager_conflict(exc):
                raise _manager_exists_error() from exc
            raise click.ClickException(f"Já existe um usuário com este e-mail. {NO_CHANGES}") from exc
        click.echo(f"Administrador criado: id={user.id} email={user.email}")

    @app.cli.command("seed")
    @click.option("--counters", default=5, show_default=True, help="Quantidade de guichês a criar")
    def seed(counters: int) -> None:
        """Cria os guichês iniciais (idempotente). Não cria usuários nem senhas."""
        created = 0
        for number in range(1, counters + 1):
            if not db.session.query(Counter.id).filter_by(number=number).first():
                db.session.add(Counter(name=f"Guichê {number:02d}", number=number, active=True))
                created += 1
        db.session.commit()
        click.echo(f"{created} guichê(s) criado(s).")

    @app.cli.command("close-day")
    def close_day() -> None:
        """Encerra o expediente de hoje, descartando senhas aguardando."""
        from app.services.day_closing_service import DayClosingService

        click.echo(f"{DayClosingService.close_today()} senha(s) descartada(s).")

    # Somente demonstração: opt-in explícito, recusado fora de FLASK_ENV=development.
    app.cli.add_command(seed_demo_command)
