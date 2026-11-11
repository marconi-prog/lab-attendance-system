import type { TokenPair, User } from '@/types/api';
import { tokenStorage } from '@/utils/tokenStorage';

import { api } from './api';

export const authService = {
  async login(email: string, password: string): Promise<User> {
    const { data } = await api.post<TokenPair>('/auth/login', { email, password });
    await tokenStorage.save(data.access_token, data.refresh_token);
    return data.user;
  },

  async me(): Promise<User> {
    const { data } = await api.get<User>('/auth/me');
    return data;
  },

  async logout(): Promise<void> {
    try {
      await api.post('/auth/logout', { refresh_token: tokenStorage.getRefresh() });
    } finally {
      await tokenStorage.clear();
    }
  },

  async changePassword(current_password: string, new_password: string): Promise<void> {
    await api.put('/auth/password', { current_password, new_password });
  },
};
