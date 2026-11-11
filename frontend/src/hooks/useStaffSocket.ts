import { useQueryClient } from '@tanstack/react-query';
import { useEffect, useState } from 'react';

import { createStaffSocket, SocketEvents } from '@/services/socket';

/**
 * Mantém a conexão /staff e invalida o cache do TanStack Query quando o
 * servidor notifica mudanças — as telas se atualizam sem recarregar.
 */
export function useStaffSocket(queryKeys: readonly (readonly unknown[])[]) {
  const queryClient = useQueryClient();
  const [connected, setConnected] = useState(false);
  const keysSignature = JSON.stringify(queryKeys);

  useEffect(() => {
    const keys = JSON.parse(keysSignature) as unknown[][];
    const socket = createStaffSocket();
    const invalidate = () => keys.forEach((queryKey) => void queryClient.invalidateQueries({ queryKey }));
    socket.on('connect', () => setConnected(true));
    socket.on('disconnect', () => setConnected(false));
    Object.values(SocketEvents).forEach((event) => socket.on(event, invalidate));
    return () => {
      socket.removeAllListeners();
      socket.disconnect();
    };
  }, [queryClient, keysSignature]);

  return connected;
}
