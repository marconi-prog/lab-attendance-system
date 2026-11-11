/** Formatação de datas/horas (as datas da API já vêm no fuso America/Recife). */

const pad = (n: number) => String(n).padStart(2, '0');

/** "2026-11-10T09:05:12-03:00" -> "09:05" (lê o horário da própria string, sem depender do fuso do dispositivo). */
export function formatTime(iso: string | null | undefined, withSeconds = false): string {
  if (!iso) return '—';
  const match = iso.match(/T(\d{2}):(\d{2}):(\d{2})/);
  if (!match) return '—';
  return withSeconds ? `${match[1]}:${match[2]}:${match[3]}` : `${match[1]}:${match[2]}`;
}

export function formatDate(iso: string | null | undefined): string {
  if (!iso) return '—';
  const [y, m, d] = iso.slice(0, 10).split('-');
  return `${d}/${m}/${y}`;
}

export function formatDateTime(iso: string | null | undefined): string {
  return iso ? `${formatDate(iso)} ${formatTime(iso)}` : '—';
}

export function formatDuration(seconds: number | null | undefined): string {
  if (seconds === null || seconds === undefined) return '—';
  const total = Math.round(seconds);
  const h = Math.floor(total / 3600);
  const m = Math.floor((total % 3600) / 60);
  const s = total % 60;
  return h > 0 ? `${h}h ${pad(m)}min` : `${m}min ${pad(s)}s`;
}

/** Data local no formato YYYY-MM-DD no fuso America/Recife. */
export function todayISO(): string {
  return new Intl.DateTimeFormat('en-CA', { timeZone: 'America/Recife' }).format(new Date());
}

export function currentMonthISO(): string {
  return todayISO().slice(0, 7);
}

export function isValidISODate(value: string): boolean {
  return /^\d{4}-\d{2}-\d{2}$/.test(value) && !Number.isNaN(Date.parse(value));
}
