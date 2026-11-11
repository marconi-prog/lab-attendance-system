import * as Speech from 'expo-speech';
import { useCallback, useEffect, useRef, useState } from 'react';
import { Platform } from 'react-native';

/**
 * Anúncios de áudio do painel.
 *
 * - Toca um sinal sonoro (Web Audio API no navegador) e depois a voz.
 * - Voz: Expo Speech (Android/iOS e navegadores com Web Speech API).
 * - Alternativa web: se a síntese de voz não existir/falhar, o sinal sonoro
 *   é tocado mesmo assim e a chamada continua visível em destaque.
 * - Os anúncios são enfileirados: chamadas simultâneas não se sobrepõem.
 * - Navegadores bloqueiam áudio até uma interação do usuário: `unlock()`
 *   deve ser chamado num toque/clique ("Ativar som").
 */
type AudioCtx = AudioContext;

function getAudioContextCtor(): (new () => AudioCtx) | null {
  if (Platform.OS !== 'web' || typeof window === 'undefined') return null;
  const w = window as unknown as { AudioContext?: new () => AudioCtx; webkitAudioContext?: new () => AudioCtx };
  return w.AudioContext ?? w.webkitAudioContext ?? null;
}

export function webSpeechAvailable(): boolean {
  return Platform.OS !== 'web' || (typeof window !== 'undefined' && 'speechSynthesis' in window);
}

export function useAnnouncer() {
  const [enabled, setEnabled] = useState(Platform.OS !== 'web');
  const audioCtx = useRef<AudioCtx | null>(null);
  const queue = useRef<string[]>([]);
  const busy = useRef(false);

  const chime = useCallback(async () => {
    const ctx = audioCtx.current;
    if (!ctx) return;
    const notes = [880, 660];
    notes.forEach((freq, i) => {
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();
      const start = ctx.currentTime + i * 0.35;
      osc.type = 'sine';
      osc.frequency.value = freq;
      gain.gain.setValueAtTime(0.0001, start);
      gain.gain.exponentialRampToValueAtTime(0.35, start + 0.03);
      gain.gain.exponentialRampToValueAtTime(0.0001, start + 0.32);
      osc.connect(gain).connect(ctx.destination);
      osc.start(start);
      osc.stop(start + 0.34);
    });
    await new Promise((r) => setTimeout(r, 750));
  }, []);

  const speak = useCallback(
    (text: string) =>
      new Promise<void>((resolve) => {
        if (!webSpeechAvailable()) return resolve();
        // Garante que a fila nunca trave caso o motor de voz não dispare callbacks.
        const safety = setTimeout(resolve, 12000);
        const done = () => {
          clearTimeout(safety);
          resolve();
        };
        try {
          Speech.speak(text, { language: 'pt-BR', rate: 0.92, pitch: 1.0, onDone: done, onStopped: done, onError: done });
        } catch {
          done();
        }
      }),
    [],
  );

  const drain = useCallback(async () => {
    if (busy.current) return;
    busy.current = true;
    try {
      while (queue.current.length) {
        const text = queue.current.shift()!;
        await chime();
        await speak(text);
      }
    } finally {
      busy.current = false;
    }
  }, [chime, speak]);

  const announce = useCallback(
    (text: string) => {
      if (!enabled) return;
      queue.current.push(text);
      void drain();
    },
    [enabled, drain],
  );

  const unlock = useCallback(() => {
    const Ctor = getAudioContextCtor();
    if (Ctor && !audioCtx.current) audioCtx.current = new Ctor();
    void audioCtx.current?.resume();
    setEnabled(true);
    // "Aquece" a síntese de voz com o gesto do usuário (necessário em alguns navegadores).
    if (webSpeechAvailable()) Speech.speak(' ', { language: 'pt-BR', volume: 0 });
  }, []);

  useEffect(
    () => () => {
      void Speech.stop();
      void audioCtx.current?.close();
    },
    [],
  );

  return { enabled, announce, unlock, voiceAvailable: webSpeechAvailable() };
}
