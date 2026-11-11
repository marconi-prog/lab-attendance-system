import type { PanelSnapshot } from '@/types/api';

import { api } from './api';

export const panelService = {
  async snapshot(): Promise<PanelSnapshot> {
    const { data } = await api.get<PanelSnapshot>('/panel');
    return data;
  },
};
