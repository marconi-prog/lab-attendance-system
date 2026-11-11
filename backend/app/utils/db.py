"""Utilitários de transação e paginação."""
from __future__ import annotations

import logging
import random
import time
from typing import Callable, TypeVar

from sqlalchemy import Select, func, select
from sqlalchemy.exc import OperationalError

from app.extensions import db

T = TypeVar("T")
logger = logging.getLogger(__name__)

# 1213 = deadlock detectado; 1205 = timeout aguardando bloqueio
RETRYABLE_MYSQL_ERRORS = {1213, 1205}


def _mysql_errno(exc: OperationalError) -> int | None:
    orig = getattr(exc, "orig", None)
    args = getattr(orig, "args", ())
    return args[0] if args and isinstance(args[0], int) else None


def run_in_transaction(fn: Callable[[], T], *, retries: int = 3) -> T:
    """Executa `fn` numa transação: commit ao final, rollback em erro.

    Deadlocks e timeouts de bloqueio do InnoDB são repetidos com backoff,
    pois são esperados sob alta concorrência e seguros de reexecutar.
    """
    for attempt in range(1, retries + 1):
        try:
            result = fn()
            db.session.commit()
            return result
        except OperationalError as exc:
            db.session.rollback()
            if _mysql_errno(exc) in RETRYABLE_MYSQL_ERRORS and attempt < retries:
                logger.warning("Transação reexecutada após conflito de bloqueio (tentativa %s)", attempt)
                time.sleep(0.02 * attempt + random.random() * 0.03)
                continue
            raise
        except Exception:
            db.session.rollback()
            raise
    raise RuntimeError("unreachable")


def paginate(stmt: Select, page: int, per_page: int) -> tuple[list, int]:
    total = db.session.scalar(select(func.count()).select_from(stmt.order_by(None).subquery())) or 0
    items = list(db.session.scalars(stmt.limit(per_page).offset((page - 1) * per_page)).unique())
    return items, total


def page_meta(page: int, per_page: int, total: int) -> dict:
    return {"page": page, "per_page": per_page, "total": total, "pages": (total + per_page - 1) // per_page}
