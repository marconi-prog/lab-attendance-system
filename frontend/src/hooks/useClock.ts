import { useEffect, useState } from 'react';

/** Relógio em tempo real no fuso America/Recife. */
export function useClock(intervalMs = 1000) {
  const [now, setNow] = useState(() => new Date());
  useEffect(() => {
    const id = setInterval(() => setNow(new Date()), intervalMs);
    return () => clearInterval(id);
  }, [intervalMs]);

  const time = new Intl.DateTimeFormat('pt-BR', {
    timeZone: 'America/Recife',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  }).format(now);
  const date = new Intl.DateTimeFormat('pt-BR', {
    timeZone: 'America/Recife',
    weekday: 'long',
    day: '2-digit',
    month: 'long',
  }).format(now);
  return { now, time, date };
}
