"""Regras de prioridade (função pura do QueueService)."""
import pytest

from app.models import TicketType as T
from app.services.queue_service import QueueService


def waiting(sp=0, se=0, sg=0):
    return {T.SP: sp, T.SE: se, T.SG: sg}


@pytest.mark.parametrize(
    "last, queue, expected",
    [
        (None, waiting(sp=1, se=1, sg=1), T.SP),  # início do dia: SP primeiro
        (T.SP, waiting(sp=1, se=1, sg=1), T.SE),  # após SP vem SE
        (T.SP, waiting(sp=1, sg=1), T.SG),  # sem SE, vem SG
        (T.SP, waiting(sp=3), T.SP),  # só há SP: continua SP
        (T.SE, waiting(sp=1, se=1, sg=1), T.SP),  # após SE volta SP
        (T.SG, waiting(sp=1, se=1, sg=1), T.SP),  # após SG volta SP
        (T.SE, waiting(se=1, sg=1), T.SE),  # sem SP: SE antes de SG
        (T.SG, waiting(sg=2), T.SG),  # só há SG
        (None, waiting(se=1), T.SE),
        (None, waiting(), None),  # fila vazia
        (T.SP, waiting(), None),
    ],
)
def test_select_next_type(last, queue, expected):
    assert QueueService.select_next_type(last, queue) == expected


def test_full_cycle_simulation():
    """Simula o ciclo completo consumindo a fila."""
    queue = waiting(sp=3, se=2, sg=2)
    last, order = None, []
    while (nxt := QueueService.select_next_type(last, queue)) is not None:
        order.append(nxt.value)
        queue[nxt] -= 1
        last = nxt
    assert order == ["SP", "SE", "SP", "SE", "SP", "SG", "SG"]
