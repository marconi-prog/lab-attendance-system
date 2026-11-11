import itertools

import pytest

from app.models import TicketStatus as S
from app.services.state_machine import ALLOWED_TRANSITIONS, TicketStateMachine
from app.utils.errors import InvalidTransitionError

EXPECTED = {
    (S.EMITIDA, S.AGUARDANDO),
    (S.AGUARDANDO, S.CHAMADA),
    (S.CHAMADA, S.EM_ATENDIMENTO),
    (S.CHAMADA, S.CHAMADA_NOVAMENTE),
    (S.CHAMADA_NOVAMENTE, S.EM_ATENDIMENTO),
    (S.CHAMADA_NOVAMENTE, S.NAO_COMPARECEU),
    (S.EM_ATENDIMENTO, S.ATENDIDA),
    (S.AGUARDANDO, S.DESCARTADA),
}


def test_transition_table_matches_specification():
    actual = {(src, dst) for src, targets in ALLOWED_TRANSITIONS.items() for dst in targets}
    assert actual == EXPECTED


@pytest.mark.parametrize("src, dst", list(itertools.product(S, S)))
def test_every_pair(src, dst):
    allowed = (src, dst) in EXPECTED
    assert TicketStateMachine.can_transition(src, dst) is allowed
    if allowed:
        TicketStateMachine.ensure_transition(src, dst)
    else:
        with pytest.raises(InvalidTransitionError):
            TicketStateMachine.ensure_transition(src, dst)


@pytest.mark.parametrize("final", [S.ATENDIDA, S.NAO_COMPARECEU, S.DESCARTADA])
def test_final_states_have_no_exit(final):
    assert ALLOWED_TRANSITIONS[final] == frozenset()
