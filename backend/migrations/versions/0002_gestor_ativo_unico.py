"""gestor ativo único

Adiciona a coluna calculada ``users.active_manager_slot`` (1 para ADMIN ativo,
NULL para os demais) com índice único: o banco passa a recusar um segundo
gestor ativo, inclusive em escritas diretas e operações concorrentes.

Nenhum dado é alterado. Se já houver mais de um gestor ativo, a migração é
abortada ANTES de qualquer DDL — a escolha de quem continua gestor é manual.

Revision ID: 0002_gestor_ativo_unico
Revises: 0001_schema_inicial
Create Date: 2026-11-27 10:00:00

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '0002_gestor_ativo_unico'
down_revision = '0001_schema_inicial'
branch_labels = None
depends_on = None

# Mesma expressão de app.models.user.ACTIVE_MANAGER_SLOT_SQL (congelada aqui, como toda migração).
SLOT_SQL = "CASE WHEN role = 'ADMIN' AND active THEN 1 ELSE NULL END"
INDEX = 'uq_users_active_manager_slot'


def _abort_if_multiple_active_managers(bind) -> None:
    ids = [row[0] for row in bind.execute(
        sa.text("SELECT id FROM users WHERE role = 'ADMIN' AND active <> 0 ORDER BY id")
    )]
    if len(ids) > 1:
        raise RuntimeError(
            f"Migração {revision} abortada antes de qualquer alteração de esquema: existem {len(ids)} gestores "
            f"(ADMIN) ativos (ids: {', '.join(map(str, ids))}), mas o sistema passa a permitir apenas um. "
            "Nenhum dado foi alterado. Decida qual gestor permanece ativo, desative ou altere o perfil dos "
            "demais pela área de gestão e execute 'flask db upgrade' novamente."
        )


def upgrade():
    bind = op.get_bind()
    _abort_if_multiple_active_managers(bind)
    if bind.dialect.name == 'mysql':
        # Um único ALTER (DDL atômica no MySQL 8): coluna e índice entram juntos ou nenhum dos dois.
        op.execute(
            f"ALTER TABLE users ADD COLUMN active_manager_slot SMALLINT GENERATED ALWAYS AS ({SLOT_SQL}) VIRTUAL NULL, "
            f"ADD UNIQUE INDEX {INDEX} (active_manager_slot)"
        )
    else:
        op.add_column('users', sa.Column('active_manager_slot', sa.SmallInteger(),
                                         sa.Computed(SLOT_SQL, persisted=False), nullable=True))
        op.create_index(INDEX, 'users', ['active_manager_slot'], unique=True)


def downgrade():
    op.drop_index(INDEX, table_name='users')
    op.drop_column('users', 'active_manager_slot')
