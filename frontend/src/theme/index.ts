import type { TicketStatus, TicketType } from '@/types/api';

export const colors = {
  primary: '#0B5C8C',
  primaryDark: '#073F61',
  primarySoft: '#E3F0F8',
  accent: '#12A37A',
  bg: '#F3F6F9',
  surface: '#FFFFFF',
  border: '#DCE3EA',
  text: '#102331',
  textMuted: '#5B6B7A',
  danger: '#C6372F',
  dangerSoft: '#FCEBEA',
  warning: '#C77C02',
  warningSoft: '#FFF4DB',
  success: '#12805C',
  successSoft: '#E2F5EE',
  panelBg: '#06243A',
  panelCard: '#0C3654',
  panelText: '#F4FAFF',
  panelMuted: '#9EC3DD',
  white: '#FFFFFF',
};

export const typeColors: Record<TicketType, { bg: string; fg: string; soft: string }> = {
  SP: { bg: '#C2410C', fg: '#FFFFFF', soft: '#FFEDE3' },
  SE: { bg: '#0F766E', fg: '#FFFFFF', soft: '#DDF5F2' },
  SG: { bg: '#1D4ED8', fg: '#FFFFFF', soft: '#E3EBFD' },
};

export const statusColors: Record<TicketStatus, { bg: string; fg: string }> = {
  EMITIDA: { bg: '#EEF1F4', fg: '#41505E' },
  AGUARDANDO: { bg: '#EEF1F4', fg: '#41505E' },
  CHAMADA: { bg: colors.warningSoft, fg: colors.warning },
  CHAMADA_NOVAMENTE: { bg: '#FDE7D3', fg: '#B45309' },
  EM_ATENDIMENTO: { bg: colors.primarySoft, fg: colors.primary },
  ATENDIDA: { bg: colors.successSoft, fg: colors.success },
  NAO_COMPARECEU: { bg: colors.dangerSoft, fg: colors.danger },
  DESCARTADA: { bg: '#EEF1F4', fg: '#6B7785' },
};

export const spacing = { xs: 4, sm: 8, md: 12, lg: 16, xl: 24, xxl: 32 };
export const radius = { sm: 6, md: 10, lg: 16, xl: 24 };
export const font = {
  small: 13,
  body: 15,
  title: 20,
  h1: 28,
};
