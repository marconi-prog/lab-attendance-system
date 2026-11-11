import type {
  AuditLogEntry,
  DailyReport,
  Dashboard,
  HistoryRow,
  MonthlyReport,
  Paginated,
  SummaryReport,
  SystemInfo,
  TicketStatus,
  TicketType,
} from '@/types/api';

import { api } from './api';

export interface PeriodFilter {
  start_date?: string;
  end_date?: string;
  type?: TicketType;
}

/** Remove filtros vazios para não enviar parâmetros em branco à API. */
function clean<T extends object>(params: T): Partial<T> {
  return Object.fromEntries(Object.entries(params).filter(([, v]) => v !== undefined && v !== '' && v !== null)) as Partial<T>;
}

export const reportService = {
  async summary(filter: PeriodFilter): Promise<SummaryReport> {
    const { data } = await api.get<SummaryReport>('/reports/summary', { params: clean(filter) });
    return data;
  },

  async daily(date?: string, type?: TicketType): Promise<DailyReport> {
    const { data } = await api.get<DailyReport>('/reports/daily', { params: clean({ date, type }) });
    return data;
  },

  async monthly(month?: string, type?: TicketType): Promise<MonthlyReport> {
    const { data } = await api.get<MonthlyReport>('/reports/monthly', { params: clean({ month, type }) });
    return data;
  },

  async history(filter: PeriodFilter & { status?: TicketStatus; page?: number; per_page?: number }) {
    const { data } = await api.get<Paginated<HistoryRow>>('/reports/attendances', { params: clean(filter) });
    return data;
  },

  async dashboard(): Promise<Dashboard> {
    const { data } = await api.get<Dashboard>('/admin/dashboard');
    return data;
  },

  async systemInfo(): Promise<SystemInfo> {
    const { data } = await api.get<SystemInfo>('/admin/system');
    return data;
  },

  async auditLogs(filter: { action?: string; entity?: string; user_id?: number; start_date?: string; end_date?: string; page?: number; per_page?: number }) {
    const { data } = await api.get<Paginated<AuditLogEntry>>('/admin/audit-logs', { params: clean(filter) });
    return data;
  },

  async closeDay(): Promise<{ discarded: number }> {
    const { data } = await api.post<{ discarded: number }>('/admin/close-day');
    return data;
  },
};
