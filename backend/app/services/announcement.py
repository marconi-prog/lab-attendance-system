"""Textos dos anúncios do painel."""
from __future__ import annotations

from app.models import Ticket, TicketType

_SPOKEN_TYPE = {
    TicketType.SP: "prioritária",
    TicketType.SE: "de retirada de exames",
    TicketType.SG: "geral",
}


def _spell(code: str) -> str:
    """'SP001' -> 'S P 0 0 1' (sintetizadores leem letra a letra)."""
    return " ".join(code)


def build_announcement(ticket: Ticket, counter_number: int, *, repeat: bool) -> dict[str, str]:
    kind = _SPOKEN_TYPE[ticket.type]
    counter = f"{counter_number:02d}"
    code = ticket.short_code
    if repeat:
        text = f"Última chamada, senha {kind} {code}, guichê {counter}."
        speech = f"Última chamada, senha {kind} {_spell(code)}, guichê {counter}."
    else:
        text = f"Senha {kind} {code}, dirigir-se ao guichê {counter}."
        speech = f"Senha {kind} {_spell(code)}, dirigir-se ao guichê {counter}."
    return {"text": text, "speech": speech}
