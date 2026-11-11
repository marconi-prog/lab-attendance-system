import type { TicketStatus, TicketType } from '@/types/api';

export const TICKET_TYPE_LABEL: Record<TicketType, string> = {
  SP: 'Prioritária',
  SE: 'Retirada de exames',
  SG: 'Geral',
};

export const STATUS_LABEL: Record<TicketStatus, string> = {
  EMITIDA: 'Emitida',
  AGUARDANDO: 'Aguardando',
  CHAMADA: 'Chamada',
  EM_ATENDIMENTO: 'Em atendimento',
  ATENDIDA: 'Atendida',
  CHAMADA_NOVAMENTE: 'Chamada novamente',
  NAO_COMPARECEU: 'Não compareceu',
  DESCARTADA: 'Descartada',
};

export const TICKET_TYPES: TicketType[] = ['SP', 'SE', 'SG'];
