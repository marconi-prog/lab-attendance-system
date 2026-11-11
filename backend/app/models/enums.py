from __future__ import annotations

import enum


class UserRole(str, enum.Enum):
    ADMIN = "ADMIN"
    ATTENDANT = "ATTENDANT"


class TicketType(str, enum.Enum):
    SP = "SP"  # Senha prioritária
    SE = "SE"  # Retirada de exames
    SG = "SG"  # Senha geral

    @property
    def label(self) -> str:
        return TICKET_TYPE_LABELS[self]


TICKET_TYPE_LABELS = {
    TicketType.SP: "Prioritária",
    TicketType.SE: "Retirada de exames",
    TicketType.SG: "Geral",
}


class TicketStatus(str, enum.Enum):
    EMITIDA = "EMITIDA"
    AGUARDANDO = "AGUARDANDO"
    CHAMADA = "CHAMADA"
    EM_ATENDIMENTO = "EM_ATENDIMENTO"
    ATENDIDA = "ATENDIDA"
    CHAMADA_NOVAMENTE = "CHAMADA_NOVAMENTE"
    NAO_COMPARECEU = "NAO_COMPARECEU"
    DESCARTADA = "DESCARTADA"


# Estados em que a senha está "nas mãos" de um guichê.
ACTIVE_STATUSES = (TicketStatus.CHAMADA, TicketStatus.CHAMADA_NOVAMENTE, TicketStatus.EM_ATENDIMENTO)
FINAL_STATUSES = (TicketStatus.ATENDIDA, TicketStatus.NAO_COMPARECEU, TicketStatus.DESCARTADA)
NOT_ATTENDED_STATUSES = (TicketStatus.NAO_COMPARECEU, TicketStatus.DESCARTADA)


class AttendanceResult(str, enum.Enum):
    EM_ANDAMENTO = "EM_ANDAMENTO"
    CONCLUIDO = "CONCLUIDO"


def sa_enum(enum_cls: type[enum.Enum], name: str):
    """Tipo ENUM nativo do MySQL armazenando o *valor* do enum."""
    from sqlalchemy import Enum

    return Enum(enum_cls, name=name, values_callable=lambda e: [member.value for member in e], validate_strings=True)
