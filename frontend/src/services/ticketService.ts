import type { IssuedTicket, Paginated, Ticket, TicketStatus, TicketType, TicketTypesInfo } from '@/types/api';

import { api } from './api';

export const ticketService = {
  async issue(type: TicketType): Promise<IssuedTicket> {
    const { data } = await api.post<IssuedTicket>('/tickets', { type });
    return data;
  },

  async types(): Promise<TicketTypesInfo> {
    const { data } = await api.get<TicketTypesInfo>('/tickets/types');
    return data;
  },

  async list(params: { date?: string; status?: TicketStatus; type?: TicketType; page?: number; per_page?: number }) {
    const { data } = await api.get<Paginated<Ticket>>('/tickets', { params });
    return data;
  },
};
