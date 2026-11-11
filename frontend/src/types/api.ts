// Tipos espelhando os contratos da API (ver docs/api.md e /api/docs).

export type UserRole = 'ADMIN' | 'ATTENDANT';
export type TicketType = 'SP' | 'SE' | 'SG';
export type TicketStatus =
  | 'EMITIDA'
  | 'AGUARDANDO'
  | 'CHAMADA'
  | 'EM_ATENDIMENTO'
  | 'ATENDIDA'
  | 'CHAMADA_NOVAMENTE'
  | 'NAO_COMPARECEU'
  | 'DESCARTADA';

export interface PageMeta {
  page: number;
  per_page: number;
  total: number;
  pages: number;
}

export interface Paginated<T> {
  items: T[];
  meta: PageMeta;
}

export interface CounterBrief {
  id: number;
  name: string;
  number: number;
}

export interface Counter extends CounterBrief {
  active: boolean;
  created_at: string;
}

export interface UserBrief {
  id: number;
  name: string;
}

export interface User {
  id: number;
  name: string;
  email: string;
  role: UserRole;
  active: boolean;
  counters: CounterBrief[];
  created_at: string;
  updated_at: string;
}

export interface TokenPair {
  access_token: string;
  refresh_token: string;
  token_type: 'Bearer';
  user: User;
}

export interface Ticket {
  id: number;
  code: string;
  short_code: string;
  type: TicketType;
  type_label: string;
  status: TicketStatus;
  status_label: string;
  daily_sequence: number;
  reference_date: string;
  issued_at: string;
  updated_at: string;
}

export interface Attendance {
  id: number;
  started_at: string;
  finished_at: string | null;
  duration_seconds: number | null;
  result: 'EM_ANDAMENTO' | 'CONCLUIDO';
  user: UserBrief;
}

export interface Announcement {
  text: string;
  speech: string;
}

export interface CallResult {
  ticket: Ticket;
  counter: Counter;
  attempt_number: number;
  is_repeat: boolean;
  called_at: string;
  announcement: Announcement;
}

export interface QueueSummary {
  waiting: Record<TicketType, number>;
  total_waiting: number;
  next_type: TicketType | null;
  last_called_type: TicketType | null;
  calling_allowed: boolean;
}

export interface CounterSession {
  id: number;
  counter: Counter;
  user: UserBrief;
  opened_at: string;
  closed_at: string | null;
}

export interface AttendantState {
  user: UserBrief;
  session: CounterSession | null;
  current: {
    ticket: Ticket;
    attempt_number: number;
    called_at: string;
    attendance: Attendance | null;
  } | null;
  queue: QueueSummary;
}

export interface AvailableCounter {
  counter: Counter;
  occupied_by: UserBrief | null;
}

export interface IssuedTicket {
  ticket: Ticket;
  waiting_ahead: number;
}

export interface TicketTypesInfo {
  types: { type: TicketType; label: string }[];
  issuing_allowed: boolean;
  business_hours: BusinessHours;
}

export interface BusinessHours {
  open: string;
  close: string;
  issue_open: string;
  enforced: boolean;
  timezone: string;
  calling_allowed_now: boolean;
  issuing_allowed_now: boolean;
}

export interface PanelItem {
  call_id: number;
  ticket_id: number;
  code: string;
  short_code: string;
  type: TicketType;
  type_label: string;
  counter_number: number;
  counter_label: string;
  counter_name: string;
  attempt_number: number;
  is_repeat: boolean;
  called_at: string;
  announcement: Announcement;
}

export interface WaitingTicket {
  ticket_id: number;
  short_code: string;
  position: number;
  issued_at: string;
}

export interface WaitingQueue {
  type: TicketType;
  label: string;
  total: number;
  tickets: WaitingTicket[];
}

export interface PanelSnapshot {
  lab_name: string;
  server_time: string;
  latest: PanelItem[];
  total_waiting: number;
  queues: WaitingQueue[];
  next_up: { ticket_id: number; short_code: string; type: TicketType }[];
  in_service: { ticket_id: number; short_code: string; type: TicketType; counter_label: string }[];
}

export interface TypeStats {
  type: TicketType;
  label: string;
  issued: number;
  attended: number;
  no_show: number;
  discarded: number;
  pending: number;
  not_attended: number;
  avg_attendance_seconds: number | null;
  avg_wait_seconds: number | null;
}

export interface ReportTotals {
  issued: number;
  attended: number;
  no_show: number;
  discarded: number;
  pending: number;
  not_attended: number;
  avg_attendance_seconds: number | null;
  avg_wait_seconds: number | null;
}

export interface SummaryReport {
  period: { start_date: string; end_date: string };
  type: TicketType | null;
  totals: ReportTotals;
  by_type: TypeStats[];
  by_status: Record<TicketStatus, number>;
  by_attendant: { user_id: number; name: string; attended: number; avg_attendance_seconds: number | null }[];
  by_counter: { counter_id: number; number: number; name: string; attended: number; avg_attendance_seconds: number | null }[];
}

export interface DailyReport extends SummaryReport {
  date: string;
  by_hour: { hour: number; issued: number }[];
}

export interface MonthlyReport extends SummaryReport {
  month: string;
  by_day: { date: string; issued: number; attended: number; not_attended: number; avg_attendance_seconds: number | null }[];
}

export interface HistoryRow {
  ticket_id: number;
  code: string;
  type: TicketType;
  type_label: string;
  status: TicketStatus;
  issued_at: string;
  first_called_at: string | null;
  last_called_at: string | null;
  call_count: number;
  started_at: string | null;
  finished_at: string | null;
  duration_seconds: number | null;
  attendant: UserBrief | null;
  counter: CounterBrief | null;
}

export interface OpenSessionInfo {
  session_id: number;
  counter: CounterBrief;
  attendant: UserBrief;
  opened_at: string;
  current_ticket: { id: number; code: string; status: TicketStatus } | null;
}

export interface Dashboard {
  date: string;
  issued: number;
  attended: number;
  waiting: number;
  in_progress: number;
  no_show: number;
  discarded: number;
  by_status: Record<TicketStatus, number>;
  avg_attendance_seconds: number | null;
  avg_wait_seconds: number | null;
  by_type: TypeStats[];
  queue: QueueSummary;
  open_sessions: OpenSessionInfo[];
  recent_calls: PanelItem[];
  business_hours: BusinessHours;
}

export interface AuditLogEntry {
  id: number;
  user: UserBrief | null;
  action: string;
  entity: string;
  entity_id: string | null;
  details: Record<string, unknown> | null;
  ip_address: string | null;
  created_at: string;
}

export interface SystemInfo {
  app_name: string;
  version: string;
  lab_name: string;
  environment: string;
  server_time: string;
  database: { engine: string; version: string };
  business_hours: BusinessHours;
  counts: Record<string, number>;
}

export interface ApiErrorBody {
  error: { code: string; message: string; details?: unknown };
}
