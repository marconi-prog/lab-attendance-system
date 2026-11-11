import { io, type Socket } from 'socket.io-client';

import { API_URL } from '@/constants/config';
import { tokenStorage } from '@/utils/tokenStorage';

/** Eventos emitidos pelo servidor (o cliente nunca emite eventos de estado). */
export const SocketEvents = {
  TICKET_ISSUED: 'ticket:issued',
  TICKET_CALLED: 'ticket:called',
  TICKET_RECALLED: 'ticket:recalled',
  TICKET_UPDATED: 'ticket:updated',
  ATTENDANCE_STARTED: 'attendance:started',
  ATTENDANCE_FINISHED: 'attendance:finished',
  PANEL_UPDATED: 'panel:updated',
  QUEUE_UPDATED: 'queue:updated',
} as const;

const baseOptions = {
  transports: ['websocket', 'polling'],
  reconnection: true,
  reconnectionDelay: 1000,
  reconnectionDelayMax: 10000,
};

/** Namespace público do painel (somente leitura). */
export function createPanelSocket(): Socket {
  return io(`${API_URL}/panel`, baseOptions);
}

/** Namespace autenticado da equipe: o token é reavaliado a cada (re)conexão. */
export function createStaffSocket(): Socket {
  return io(`${API_URL}/staff`, {
    ...baseOptions,
    auth: (cb: (data: object) => void) => cb({ token: tokenStorage.getAccess() }),
  });
}
