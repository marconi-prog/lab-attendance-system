import { useQuery, useQueryClient } from '@tanstack/react-query';
import { router } from 'expo-router';
import { Volume2, VolumeX } from 'lucide-react-native';
import { useEffect, useRef, useState, type ReactNode } from 'react';
import { Animated, Easing, Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';

import { ConnectionDot } from '@/components/ConnectionDot';
import { LAB_NAME } from '@/constants/config';
import { useAnnouncer } from '@/hooks/useAnnouncer';
import { useClock } from '@/hooks/useClock';
import { useResponsive } from '@/hooks/useResponsive';
import { panelService } from '@/services/panelService';
import { createPanelSocket, SocketEvents } from '@/services/socket';
import { colors, radius, spacing, typeColors } from '@/theme';
import type { CallResult, PanelSnapshot, WaitingQueue } from '@/types/api';
import { formatTime } from '@/utils/format';

const PANEL_KEY = ['panel'] as const;
const READY = '#22C55E';

/** Entrada discreta (fade + leve subida) para senhas que acabaram de aparecer. */
function FadeIn({ children }: { children: ReactNode }) {
  const v = useRef(new Animated.Value(0)).current;
  useEffect(() => {
    Animated.timing(v, { toValue: 1, duration: 450, easing: Easing.out(Easing.quad), useNativeDriver: false }).start();
  }, [v]);
  const translateY = v.interpolate({ inputRange: [0, 1], outputRange: [8, 0] });
  return <Animated.View style={{ opacity: v, transform: [{ translateY }] }}>{children}</Animated.View>;
}

function QueueBlock({ queue }: { queue: WaitingQueue }) {
  const c = typeColors[queue.type];
  const hidden = queue.total - queue.tickets.length;
  return (
    <View style={styles.queueBlock}>
      <View style={styles.queueHeader}>
        <View style={[styles.queueDot, { backgroundColor: c.bg }]} />
        <Text style={styles.queueTitle}>{queue.label}</Text>
        <Text style={styles.queueCount}>{queue.total}</Text>
      </View>
      {queue.total === 0 ? (
        <Text style={styles.queueEmpty}>Nenhuma senha</Text>
      ) : (
        <View style={styles.tiles}>
          {queue.tickets.map((t) => (
            <FadeIn key={t.ticket_id}>
              <View style={[styles.tile, t.position === 1 && { borderColor: c.bg, backgroundColor: '#123A57' }]}>
                <Text style={[styles.tileCode, t.position === 1 && { color: colors.panelText }]}>{t.short_code}</Text>
              </View>
            </FadeIn>
          ))}
          {hidden > 0 ? (
            <View style={[styles.tile, styles.tileMore]}>
              <Text style={styles.tileMoreText}>+{hidden}</Text>
            </View>
          ) : null}
        </View>
      )}
    </View>
  );
}

export default function PanelScreen() {
  const queryClient = useQueryClient();
  const { time, date } = useClock();
  const { isWide, width } = useResponsive();
  const { enabled: soundOn, announce, unlock, voiceAvailable } = useAnnouncer();
  const [connected, setConnected] = useState(false);
  const flash = useRef(new Animated.Value(0)).current;

  // Carga inicial via REST; depois o socket mantém os dados atualizados
  // (emissão, chamada, início/fim de atendimento e encerramento do dia).
  const { data, isError } = useQuery({ queryKey: PANEL_KEY, queryFn: panelService.snapshot, refetchInterval: connected ? false : 15_000 });

  const announceRef = useRef(announce);
  announceRef.current = announce;

  useEffect(() => {
    const socket = createPanelSocket();
    socket.on('connect', () => setConnected(true));
    socket.on('disconnect', () => setConnected(false));
    socket.on(SocketEvents.PANEL_UPDATED, (snapshot: PanelSnapshot) => queryClient.setQueryData(PANEL_KEY, snapshot));
    const onCall = (call: CallResult) => {
      announceRef.current(call.announcement.speech);
      flash.setValue(0);
      Animated.sequence([
        Animated.timing(flash, { toValue: 1, duration: 350, easing: Easing.out(Easing.quad), useNativeDriver: false }),
        Animated.timing(flash, { toValue: 0, duration: 1600, easing: Easing.in(Easing.quad), useNativeDriver: false }),
      ]).start();
    };
    socket.on(SocketEvents.TICKET_CALLED, onCall);
    socket.on(SocketEvents.TICKET_RECALLED, onCall);
    return () => {
      socket.removeAllListeners();
      socket.disconnect();
    };
  }, [queryClient, flash]);

  const latest = data?.latest ?? [];
  const [current, ...previous] = latest;
  const highlightBg = flash.interpolate({ inputRange: [0, 1], outputRange: [colors.panelCard, '#1E6A9E'] });
  const codeSize = Math.min(isWide ? 170 : 110, width / (isWide ? 7 : 4.5));

  const nextColumn = (
    <View style={[styles.column, styles.nextColumn, isWide && { flex: 1.25 }]}>
      <View style={styles.columnHead}>
        <Text style={styles.columnTitle}>PRÓXIMOS</Text>
        <Text style={styles.columnSub}>{data?.total_waiting ?? 0} senha(s) aguardando por fila</Text>
      </View>
      {data && data.next_up.length > 0 ? (
        <View style={styles.nextUp}>
          <Text style={styles.sectionLabel}>Ordem de chamada</Text>
          <View style={styles.nextRow}>
            {data.next_up.map((n, i) => (
              <FadeIn key={n.ticket_id}>
                <View style={[styles.nextChip, i === 0 && styles.nextChipFirst]}>
                  <Text style={styles.nextIndex}>{i + 1}º</Text>
                  <View style={[styles.queueDot, { backgroundColor: typeColors[n.type].bg }]} />
                  <Text style={[styles.nextCode, i === 0 && { color: colors.panelText }]}>{n.short_code}</Text>
                </View>
              </FadeIn>
            ))}
          </View>
        </View>
      ) : null}
      {(data?.queues ?? []).map((q) => (
        <QueueBlock key={q.type} queue={q} />
      ))}
    </View>
  );

  const ready = (
    <View style={[styles.column, isWide && { flex: 1.6 }]}>
      <View style={styles.columnHead}>
        <Text style={[styles.columnTitle, { color: READY }]}>CHAMANDO</Text>
        <Text style={styles.columnSub}>Dirija-se ao guichê indicado</Text>
      </View>
      <Animated.View style={[styles.current, { backgroundColor: highlightBg }]}>
        {current ? (
          <>
            <Text style={styles.currentLabel}>{current.is_repeat ? 'ÚLTIMA CHAMADA' : 'SENHA CHAMADA'}</Text>
            <Text style={[styles.currentCode, { fontSize: codeSize }]} adjustsFontSizeToFit numberOfLines={1}>
              {current.short_code}
            </Text>
            <View style={[styles.typePill, { backgroundColor: typeColors[current.type].bg }]}>
              <Text style={styles.typePillText}>{current.type_label}</Text>
            </View>
            <Text style={styles.counterLabel}>GUICHÊ</Text>
            <Text style={[styles.counterNumber, { fontSize: codeSize * 0.75 }]}>{current.counter_label}</Text>
          </>
        ) : (
          <Text style={styles.waiting}>{isError ? 'Sem conexão com o servidor' : 'Aguardando chamadas…'}</Text>
        )}
      </Animated.View>
      {data && data.in_service.length > 0 ? (
        <View style={styles.inService}>
          <Text style={styles.sectionLabel}>Em atendimento</Text>
          <View style={styles.nextRow}>
            {data.in_service.map((s) => (
              <View key={s.ticket_id} style={styles.serviceChip}>
                <Text style={styles.serviceCode}>{s.short_code}</Text>
                <Text style={styles.serviceCounter}>G{s.counter_label}</Text>
              </View>
            ))}
          </View>
        </View>
      ) : null}
    </View>
  );

  const history = (
    <View style={[styles.column, isWide && { flex: 1 }]}>
      <View style={styles.columnHead}>
        <Text style={styles.columnTitle}>ÚLTIMAS CHAMADAS</Text>
        <Text style={styles.columnSub}>Chamadas anteriores</Text>
      </View>
      {previous.length === 0 ? <Text style={styles.queueEmpty}>—</Text> : null}
      {previous.map((item) => (
        <FadeIn key={item.call_id}>
          <View style={styles.historyRow}>
            <View style={[styles.typeBar, { backgroundColor: typeColors[item.type].bg }]} />
            <Text style={styles.historyCode}>{item.short_code}</Text>
            <View style={{ alignItems: 'flex-end' }}>
              <Text style={styles.historyCounter}>Guichê {item.counter_label}</Text>
              <Text style={styles.historyTime}>{formatTime(item.called_at)}</Text>
            </View>
          </View>
        </FadeIn>
      ))}
    </View>
  );

  return (
    <View style={styles.screen}>
      <View style={styles.header}>
        <Pressable onLongPress={() => router.replace('/')} delayLongPress={1500}>
          <Text style={styles.lab}>{data?.lab_name ?? LAB_NAME}</Text>
          <Text style={styles.date}>{date.charAt(0).toUpperCase() + date.slice(1)}</Text>
        </Pressable>
        <View style={styles.headerRight}>
          <ConnectionDot connected={connected} dark />
          <Pressable onPress={unlock} accessibilityLabel={soundOn ? 'Som ativado' : 'Ativar som'} style={styles.soundBtn}>
            {soundOn ? <Volume2 color={colors.panelText} size={22} /> : <VolumeX color="#F59E0B" size={22} />}
          </Pressable>
          <Text style={styles.clock}>{time}</Text>
        </View>
      </View>

      {isWide ? (
        <View style={[styles.body, { flexDirection: 'row' }]}>
          {nextColumn}
          {ready}
          {history}
        </View>
      ) : (
        <ScrollView contentContainerStyle={styles.body}>
          {ready}
          {nextColumn}
          {history}
        </ScrollView>
      )}

      {!soundOn ? (
        <Pressable style={styles.overlay} onPress={unlock} accessibilityRole="button" accessibilityLabel="Ativar som do painel">
          <Volume2 color="#fff" size={48} />
          <Text style={styles.overlayTitle}>Toque para ativar o som do painel</Text>
          <Text style={styles.overlayText}>
            {voiceAvailable ? 'O navegador exige uma interação antes de reproduzir áudio.' : 'Este navegador não possui voz sintetizada; será tocado um sinal sonoro.'}
          </Text>
        </Pressable>
      ) : null}
    </View>
  );
}

const styles = StyleSheet.create({
  screen: { flex: 1, backgroundColor: colors.panelBg },
  header: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', paddingHorizontal: spacing.xxl, paddingVertical: spacing.md, borderBottomWidth: 1, borderBottomColor: '#123E5E' },
  headerRight: { flexDirection: 'row', alignItems: 'center', gap: spacing.lg },
  lab: { color: colors.panelText, fontSize: 24, fontWeight: '800' },
  date: { color: colors.panelMuted, fontSize: 14 },
  clock: { color: colors.panelText, fontSize: 36, fontWeight: '800', fontVariant: ['tabular-nums'] },
  soundBtn: { padding: spacing.sm },
  body: { flexGrow: 1, flex: 1, padding: spacing.lg, gap: spacing.lg },

  column: { gap: spacing.md },
  columnHead: { borderBottomWidth: 3, borderBottomColor: '#1A4A6E', paddingBottom: spacing.sm },
  columnTitle: { color: colors.panelText, fontSize: 26, fontWeight: '900', letterSpacing: 3 },
  columnSub: { color: colors.panelMuted, fontSize: 14, fontWeight: '600' },
  sectionLabel: { color: colors.panelMuted, fontSize: 13, fontWeight: '800', textTransform: 'uppercase', letterSpacing: 1.5, marginBottom: 6 },

  nextColumn: { backgroundColor: '#082C45', borderRadius: radius.xl, padding: spacing.lg },
  nextUp: { gap: 2 },
  nextRow: { flexDirection: 'row', flexWrap: 'wrap', gap: spacing.sm },
  nextChip: { flexDirection: 'row', alignItems: 'center', gap: 6, backgroundColor: '#0C3654', borderRadius: radius.md, paddingHorizontal: 10, paddingVertical: 6, borderWidth: 1, borderColor: '#1A4A6E' },
  nextChipFirst: { borderColor: '#FACC15', backgroundColor: '#123A57' },
  nextIndex: { color: '#FACC15', fontSize: 13, fontWeight: '800' },
  nextCode: { color: colors.panelMuted, fontSize: 20, fontWeight: '900', fontVariant: ['tabular-nums'] },

  queueBlock: { gap: 6 },
  queueHeader: { flexDirection: 'row', alignItems: 'center', gap: spacing.sm },
  queueDot: { width: 12, height: 12, borderRadius: 6 },
  queueTitle: { flex: 1, color: colors.panelText, fontSize: 16, fontWeight: '800' },
  queueCount: { color: colors.panelMuted, fontSize: 16, fontWeight: '800', fontVariant: ['tabular-nums'] },
  queueEmpty: { color: '#5D84A3', fontSize: 15, fontStyle: 'italic' },
  tiles: { flexDirection: 'row', flexWrap: 'wrap', gap: 6 },
  tile: { minWidth: 82, alignItems: 'center', paddingVertical: 6, paddingHorizontal: 8, borderRadius: radius.sm, borderWidth: 2, borderColor: 'transparent', backgroundColor: '#0C3654' },
  tileCode: { color: '#A6C6DE', fontSize: 22, fontWeight: '800', fontVariant: ['tabular-nums'] },
  tileMore: { backgroundColor: 'transparent', borderColor: '#1A4A6E', borderStyle: 'dashed' },
  tileMoreText: { color: colors.panelMuted, fontSize: 20, fontWeight: '800' },

  current: { flex: 1, minHeight: 320, borderRadius: radius.xl, alignItems: 'center', justifyContent: 'center', padding: spacing.xl, gap: spacing.xs, borderWidth: 3, borderColor: READY },
  currentLabel: { color: colors.panelMuted, fontSize: 22, fontWeight: '800', letterSpacing: 3 },
  currentCode: { color: colors.panelText, fontWeight: '900', letterSpacing: 6, fontVariant: ['tabular-nums'] },
  typePill: { paddingHorizontal: 18, paddingVertical: 6, borderRadius: 999 },
  typePillText: { color: '#fff', fontSize: 20, fontWeight: '800' },
  counterLabel: { color: colors.panelMuted, fontSize: 22, fontWeight: '800', letterSpacing: 3, marginTop: spacing.md },
  counterNumber: { color: '#FACC15', fontWeight: '900', fontVariant: ['tabular-nums'] },
  waiting: { color: colors.panelMuted, fontSize: 30, fontWeight: '700' },
  inService: { gap: 2 },
  serviceChip: { flexDirection: 'row', alignItems: 'baseline', gap: 6, backgroundColor: '#0C3654', borderRadius: radius.md, paddingHorizontal: 10, paddingVertical: 6 },
  serviceCode: { color: colors.panelText, fontSize: 18, fontWeight: '800' },
  serviceCounter: { color: '#FACC15', fontSize: 14, fontWeight: '800' },

  historyRow: { flexDirection: 'row', alignItems: 'center', backgroundColor: colors.panelCard, borderRadius: radius.lg, padding: spacing.md, gap: spacing.md },
  typeBar: { width: 8, alignSelf: 'stretch', borderRadius: 4 },
  historyCode: { flex: 1, color: colors.panelText, fontSize: 36, fontWeight: '900', fontVariant: ['tabular-nums'] },
  historyCounter: { color: '#FACC15', fontSize: 20, fontWeight: '800' },
  historyTime: { color: colors.panelMuted, fontSize: 14 },

  overlay: { position: 'absolute', top: 0, left: 0, right: 0, bottom: 0, backgroundColor: 'rgba(3, 20, 33, 0.88)', alignItems: 'center', justifyContent: 'center', gap: spacing.md, padding: spacing.xl },
  overlayTitle: { color: '#fff', fontSize: 28, fontWeight: '800', textAlign: 'center' },
  overlayText: { color: colors.panelMuted, fontSize: 16, textAlign: 'center' },
});
