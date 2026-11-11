import type { Paginated, User, UserRole } from '@/types/api';

import { api } from './api';

export interface UserInput {
  name: string;
  email: string;
  password?: string;
  role: UserRole;
  counter_ids?: number[];
}

export const userService = {
  async list(params: { search?: string; role?: UserRole; page?: number; per_page?: number }) {
    const { data } = await api.get<Paginated<User>>('/users', { params });
    return data;
  },

  async create(input: UserInput & { password: string }): Promise<User> {
    const { data } = await api.post<User>('/users', input);
    return data;
  },

  async update(id: number, input: Partial<Omit<UserInput, 'counter_ids'>> & { active?: boolean }): Promise<User> {
    const { data } = await api.patch<User>(`/users/${id}`, input);
    return data;
  },

  async assignCounters(id: number, counterIds: number[]): Promise<User> {
    const { data } = await api.put<User>(`/users/${id}/counters`, { counter_ids: counterIds });
    return data;
  },
};
