import axios, { AxiosError, type InternalAxiosRequestConfig } from 'axios';

import { API_URL } from '@/constants/config';
import type { ApiErrorBody } from '@/types/api';
import { tokenStorage } from '@/utils/tokenStorage';

/** Erro normalizado: toda falha de integração chega à UI com código e mensagem legíveis. */
export class ApiError extends Error {
  constructor(
    message: string,
    public readonly status: number,
    public readonly code: string,
    public readonly details?: unknown,
  ) {
    super(message);
    this.name = 'ApiError';
  }
}

export const api = axios.create({
  baseURL: `${API_URL}/api`,
  timeout: 15000,
  headers: { 'Content-Type': 'application/json' },
});

api.interceptors.request.use((config) => {
  const token = tokenStorage.getAccess();
  if (token && !config.headers.Authorization) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// ---- renovação automática do access token -------------------------------
let refreshing: Promise<string | null> | null = null;
let onSessionExpired: (() => void) | null = null;

export function setSessionExpiredHandler(handler: (() => void) | null) {
  onSessionExpired = handler;
}

async function refreshAccessToken(): Promise<string | null> {
  const refresh = tokenStorage.getRefresh();
  if (!refresh) return null;
  try {
    const { data } = await axios.post<{ access_token: string }>(`${API_URL}/api/auth/refresh`, null, {
      headers: { Authorization: `Bearer ${refresh}` },
      timeout: 10000,
    });
    await tokenStorage.save(data.access_token);
    return data.access_token;
  } catch {
    return null;
  }
}

type RetriableConfig = InternalAxiosRequestConfig & { _retried?: boolean };

api.interceptors.response.use(
  (response) => response,
  async (error: AxiosError<ApiErrorBody>) => {
    const config = error.config as RetriableConfig | undefined;
    const status = error.response?.status ?? 0;
    const code = error.response?.data?.error?.code;
    const isAuthCall = config?.url?.startsWith('/auth/login') || config?.url?.startsWith('/auth/refresh');

    if (status === 401 && config && !config._retried && !isAuthCall && code === 'TOKEN_EXPIRED') {
      config._retried = true;
      refreshing ??= refreshAccessToken().finally(() => {
        refreshing = null;
      });
      const token = await refreshing;
      if (token) {
        config.headers.Authorization = `Bearer ${token}`;
        return api.request(config);
      }
    }
    if (status === 401 && !isAuthCall) {
      onSessionExpired?.();
    }
    return Promise.reject(toApiError(error));
  },
);

export function toApiError(error: unknown): ApiError {
  if (error instanceof ApiError) return error;
  if (axios.isAxiosError(error)) {
    const body = error.response?.data as ApiErrorBody | undefined;
    if (body?.error) {
      return new ApiError(body.error.message, error.response!.status, body.error.code, body.error.details);
    }
    if (!error.response) {
      return new ApiError('Não foi possível conectar ao servidor. Verifique a rede.', 0, 'NETWORK_ERROR');
    }
    return new ApiError(`Erro inesperado do servidor (${error.response.status}).`, error.response.status, 'HTTP_ERROR');
  }
  return new ApiError('Erro inesperado.', 0, 'UNKNOWN');
}

export function errorMessage(error: unknown): string {
  return toApiError(error).message;
}
