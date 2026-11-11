export const API_URL = (process.env.EXPO_PUBLIC_API_URL ?? 'http://localhost:5000').replace(/\/$/, '');
export const LAB_NAME = process.env.EXPO_PUBLIC_LAB_NAME ?? 'Laboratório de Análises Clínicas';

/** Tempo que a senha emitida fica em destaque no totem antes de voltar à tela inicial. */
export const TOTEM_RESET_SECONDS = 12;
