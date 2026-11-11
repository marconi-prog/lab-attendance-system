import { Platform } from 'react-native';
import * as SecureStore from 'expo-secure-store';

/**
 * Armazena os tokens JWT.
 * - Nativo: Keychain/Keystore via expo-secure-store.
 * - Web: sessionStorage (é descartado ao fechar a aba; não persiste entre sessões do navegador).
 */
const ACCESS_KEY = 'atendimento.access_token';
const REFRESH_KEY = 'atendimento.refresh_token';

const memory: { access: string | null; refresh: string | null } = { access: null, refresh: null };
const isWeb = Platform.OS === 'web';

async function write(key: string, value: string | null) {
  if (isWeb) {
    try {
      if (value) window.sessionStorage.setItem(key, value);
      else window.sessionStorage.removeItem(key);
    } catch {
      /* armazenamento indisponível: mantém apenas em memória */
    }
    return;
  }
  if (value) await SecureStore.setItemAsync(key, value);
  else await SecureStore.deleteItemAsync(key);
}

async function read(key: string): Promise<string | null> {
  if (isWeb) {
    try {
      return window.sessionStorage.getItem(key);
    } catch {
      return null;
    }
  }
  return SecureStore.getItemAsync(key);
}

export const tokenStorage = {
  getAccess: () => memory.access,
  getRefresh: () => memory.refresh,

  async load() {
    memory.access = await read(ACCESS_KEY);
    memory.refresh = await read(REFRESH_KEY);
    return { access: memory.access, refresh: memory.refresh };
  },

  async save(access: string, refresh?: string) {
    memory.access = access;
    await write(ACCESS_KEY, access);
    if (refresh !== undefined) {
      memory.refresh = refresh;
      await write(REFRESH_KEY, refresh);
    }
  },

  async clear() {
    memory.access = null;
    memory.refresh = null;
    await write(ACCESS_KEY, null);
    await write(REFRESH_KEY, null);
  },
};
