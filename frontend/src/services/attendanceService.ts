import type { AttendantState, AvailableCounter, CallResult, CounterSession, Ticket, Attendance } from '@/types/api';

import { api } from './api';

type AttendanceResponse = { ticket: Ticket; attendance: Attendance };

export const attendanceService = {
  async state(): Promise<AttendantState> {
    const { data } = await api.get<AttendantState>('/attendant/state');
    return data;
  },

  async counters(): Promise<AvailableCounter[]> {
    const { data } = await api.get<{ items: AvailableCounter[] }>('/attendant/counters');
    return data.items;
  },

  async openSession(counterId: number): Promise<CounterSession> {
    const { data } = await api.post<CounterSession>('/attendant/session', { counter_id: counterId });
    return data;
  },

  async closeSession(): Promise<void> {
    await api.delete('/attendant/session');
  },

  async callNext(): Promise<CallResult> {
    const { data } = await api.post<CallResult>('/attendant/call-next');
    return data;
  },

  async recall(ticketId: number): Promise<CallResult> {
    const { data } = await api.post<CallResult>(`/attendant/tickets/${ticketId}/recall`);
    return data;
  },

  async start(ticketId: number): Promise<AttendanceResponse> {
    const { data } = await api.post<AttendanceResponse>(`/attendant/tickets/${ticketId}/start`);
    return data;
  },

  async finish(ticketId: number): Promise<AttendanceResponse> {
    const { data } = await api.post<AttendanceResponse>(`/attendant/tickets/${ticketId}/finish`);
    return data;
  },

  async noShow(ticketId: number): Promise<{ ticket: Ticket }> {
    const { data } = await api.post<{ ticket: Ticket }>(`/attendant/tickets/${ticketId}/no-show`);
    return data;
  },
};
