import type { Counter, CounterSession } from '@/types/api';

import { api } from './api';

export const counterService = {
  async list(): Promise<Counter[]> {
    const { data } = await api.get<{ items: Counter[] }>('/counters');
    return data.items;
  },

  async create(input: { name: string; number: number }): Promise<Counter> {
    const { data } = await api.post<Counter>('/counters', input);
    return data;
  },

  async update(id: number, input: { name?: string; number?: number; active?: boolean }): Promise<Counter> {
    const { data } = await api.patch<Counter>(`/counters/${id}`, input);
    return data;
  },

  async sessions(): Promise<CounterSession[]> {
    const { data } = await api.get<{ items: CounterSession[] }>('/counters/sessions');
    return data.items;
  },

  async forceCloseSession(sessionId: number): Promise<void> {
    await api.delete(`/counters/sessions/${sessionId}`);
  },
};
