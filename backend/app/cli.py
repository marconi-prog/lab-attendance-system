"""Comandos de linha de comando (flask <comando>)."""
from __future__ import annotations

import getpass
import os

import click
from flask import Flask

from app.extensions import db
from app.models import Counter, User, UserRole
from app.repositories import UserRepository
from app.schemas.user import validate_password_strength


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
        """Cria um administrador. A senha é lida de ADMIN_PASSWORD ou solicitada no terminal."""
        if UserRepository.get_by_email(email):
            raise click.ClickException("Já existe um usuário com este e-mail.")
        password = _read_password("ADMIN_PASSWORD")
        try:
            validate_password_strength(password)
        except ValueError as exc:
            raise click.ClickException(str(exc)) from exc
        user = User(name=name, email=email.lower(), role=UserRole.ADMIN, active=True)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
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
