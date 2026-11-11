import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { BellRing, CheckCircle2, DoorOpen, Megaphone, Play, UserX } from 'lucide-react-native';
import { useEffect, useState } from 'react';
import { Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';

import { AppHeader } from '@/components/AppHeader';
import { StatusBadge, TypeBadge } from '@/components/Badges';
import { Button } from '@/components/Button';
import { Card } from '@/components/Card';
import { ConnectionDot } from '@/components/ConnectionDot';
import { EmptyState, ErrorBanner, Loading, SuccessBanner } from '@/components/Feedback';
import { TICKET_TYPE_LABEL, TICKET_TYPES } from '@/constants/labels';
import { useResponsive } from '@/hooks/useResponsive';
import { useStaffSocket } from '@/hooks/useStaffSocket';
import { errorMessage } from '@/services/api';
import { attendanceService } from '@/services/attendanceService';
import { colors, radius, spacing, typeColors } from '@/theme';
import type { AttendantState, TicketStatus } from '@/types/api';
import { formatDuration, formatTime } from '@/utils/format';

const STATE_KEY = ['attendant-state'] as const;
const COUNTERS_KEY = ['attendant-counters'] as const;

const STEPS: { status: TicketStatus[]; label: string }[] = [
  { status: ['CHAMADA', 'CHAMADA_NOVAMENTE'], label: 'Chamada' },
  { status: ['EM_ATENDIMENTO'], label: 'Em atendimento' },
  { status: ['ATENDIDA'], label: 'Finalizada' },
];

function useElapsed(startIso: string | null | undefined) {
  const [now, setNow] = useState(Date.now());
  useEffect(() => {
    if (!startIso) return;
    const id = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(id);
  }, [startIso]);
  return startIso ? Math.max(0, (now - Date.parse(startIso)) / 1000) : null;
}

function CounterPicker({ onOpened }: { onOpened: () => void }) {
  const counters = useQuery({ queryKey: COUNTERS_KEY, queryFn: attendanceService.counters });
  const open = useMutation({ mutationFn: attendanceService.openSession, onSuccess: onOpened });
  if (counters.isLoading) return <Loading />;
  return (
    <Card title="Selecione seu guichê">
      <ErrorBanner message={counters.isError ? errorMessage(counters.error) : open.isError ? errorMessage(open.error) : null} />
      {counters.data?.length === 0 ? <EmptyState message="Nenhum guichê autorizado. Solicite ao gestor." /> : null}
      <View style={styles.counterGrid}>
        {counters.data?.map(({ counter, occupied_by }) => (
          <Pressable
            key={counter.id}
            disabled={!!occupied_by || open.isPending}
            onPress={() => open.mutate(counter.id)}
            style={({ pressed }) => [styles.counterTile, occupied_by && { opacity: 0.5 }, pressed && { opacity: 0.8 }]}
            accessibilityRole="button"
            accessibilityLabel={`Guichê ${counter.number}`}
          >
            <Text style={styles.counterTileNumber}>{String(counter.number).padStart(2, '0')}</Text>
            <Text style={styles.counterTileName}>{counter.name}</Text>
            <Text style={styles.counterTileStatus}>{occupied_by ? `Em uso por ${occupied_by.name}` : 'Disponível'}</Text>
          </Pressable>
        ))}
      </View>
    </Card>
  );
}

function QueueSummaryCard({ state }: { state: AttendantState }) {
  const q = state.queue;
  return (
    <Card title="Fila de espera" right={<Text style={styles.muted}>{q.total_waiting} aguardando</Text>}>
      <View style={styles.queueRow}>
        {TICKET_TYPES.map((t) => (
          <View key={t} style={[styles.queueBox, { backgroundColor: typeColors[t].soft }]}>
            <Text style={[styles.queueCount, { color: typeColors[t].bg }]}>{q.waiting[t] ?? 0}</Text>
            <Text style={styles.queueLabel}>{TICKET_TYPE_LABEL[t]}</Text>
          </View>
        ))}
      </View>
      <Text style={styles.muted}>Próxima categoria pelo ciclo de prioridade: {q.next_type ? `${q.next_type} · ${TICKET_TYPE_LABEL[q.next_type]}` : '—'}</Text>
      {!q.calling_allowed ? <ErrorBanner message="Fora do horário de chamadas (07h–17h). Atendimentos em andamento podem ser finalizados." /> : null}
    </Card>
  );
}

export default function AttendantScreen() {
  const queryClient = useQueryClient();
  const { isWide } = useResponsive();
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const connected = useStaffSocket([STATE_KEY]);
  const state = useQuery({ queryKey: STATE_KEY, queryFn: attendanceService.state, refetchInterval: 30_000 });

  const refresh = () => void queryClient.invalidateQueries({ queryKey: STATE_KEY });
  const action = useMutation({
    mutationFn: async (fn: () => Promise<string>) => fn(),
    onMutate: () => {
      setError(null);
      setMessage(null);
    },
    onSuccess: (msg) => setMessage(msg),
    onError: (e) => setError(errorMessage(e)),
    onSettled: refresh,
  });

  const current = state.data?.current;
  const elapsed = useElapsed(current?.attendance?.started_at);
  const run = (fn: () => Promise<string>) => action.mutate(fn);

  if (state.isLoading) return <Loading />;
  const session = state.data?.session;
  const status = current?.ticket.status;

  return (
    <View style={styles.screen}>
      <AppHeader title={session ? `Atendimento · Guichê ${String(session.counter.number).padStart(2, '0')}` : 'Atendimento'}>
        <ConnectionDot connected={connected} />
      </AppHeader>
      <ScrollView contentContainerStyle={styles.content}>
        <ErrorBanner message={error ?? (state.isError ? errorMessage(state.error) : null)} />
        <SuccessBanner message={message} />

        {!session ? (
          <CounterPicker onOpened={() => { refresh(); void queryClient.invalidateQueries({ queryKey: COUNTERS_KEY }); }} />
        ) : (
          <View style={[styles.columns, { flexDirection: isWide ? 'row' : 'column' }]}>
            <View style={{ flex: 3, gap: spacing.lg }}>
              <Card
                title="Senha atual"
                right={current ? <StatusBadge status={current.ticket.status} /> : <Text style={styles.muted}>Livre</Text>}
              >
                {current ? (
                  <View style={styles.ticketBox}>
                    <Text style={[styles.ticketCode, { color: typeColors[current.ticket.type].bg }]}>{current.ticket.short_code}</Text>
                    <TypeBadge type={current.ticket.type} />
                    <View style={styles.metaRow}>
                      <Meta label="Emitida" value={formatTime(current.ticket.issued_at)} />
                      <Meta label="Chamada" value={formatTime(current.called_at)} />
                      <Meta label="Tentativa" value={`${current.attempt_number} de 2`} />
                      {current.attendance ? <Meta label="Duração" value={formatDuration(elapsed)} /> : null}
                    </View>
                    <View style={styles.steps}>
                      {STEPS.map((step, i) => {
                        const activeIndex = STEPS.findIndex((s) => status && s.status.includes(status));
                        const done = i <= activeIndex;
                        return (
                          <View key={step.label} style={styles.step}>
                            <View style={[styles.stepDot, done && { backgroundColor: colors.primary }]} />
                            <Text style={[styles.stepLabel, done && { color: colors.primary }]}>{step.label}</Text>
                          </View>
                        );
                      })}
                    </View>
                    {status === 'CHAMADA_NOVAMENTE' ? (
                      <Text style={styles.warn}>Última chamada realizada. Se o cliente não comparecer, registre a ausência.</Text>
                    ) : null}
                  </View>
                ) : (
                  <EmptyState message="Nenhuma senha em atendimento. Chame a próxima." />
                )}

                <View style={styles.actions}>
                  <Button
                    title="CHAMAR PRÓXIMA"
                    icon={BellRing}
                    size="lg"
                    style={styles.actionBtn}
                    disabled={!!current || !state.data?.queue.calling_allowed}
                    loading={action.isPending && !current}
                    onPress={() => run(async () => { const r = await attendanceService.callNext(); return `Senha ${r.ticket.short_code} chamada.`; })}
                  />
                  <Button
                    title="REPETIR CHAMADA"
                    icon={Megaphone}
                    size="lg"
                    variant="warning"
                    style={styles.actionBtn}
                    disabled={status !== 'CHAMADA' || action.isPending}
                    onPress={() => run(async () => { const r = await attendanceService.recall(current!.ticket.id); return `Última chamada da senha ${r.ticket.short_code}.`; })}
                  />
                  <Button
                    title="INICIAR ATENDIMENTO"
                    icon={Play}
                    size="lg"
                    variant="primary"
                    style={styles.actionBtn}
                    disabled={!(status === 'CHAMADA' || status === 'CHAMADA_NOVAMENTE') || action.isPending}
                    onPress={() => run(async () => { await attendanceService.start(current!.ticket.id); return 'Atendimento iniciado.'; })}
                  />
                  <Button
                    title="FINALIZAR ATENDIMENTO"
                    icon={CheckCircle2}
                    size="lg"
                    variant="success"
                    style={styles.actionBtn}
                    disabled={status !== 'EM_ATENDIMENTO' || action.isPending}
                    onPress={() => run(async () => { const r = await attendanceService.finish(current!.ticket.id); return `Atendimento finalizado (${formatDuration(r.attendance.duration_seconds)}).`; })}
                  />
                  <Button
                    title="REGISTRAR AUSÊNCIA"
                    icon={UserX}
                    size="lg"
                    variant="danger"
                    style={styles.actionBtn}
                    disabled={status !== 'CHAMADA_NOVAMENTE' || action.isPending}
                    onPress={() => run(async () => { const r = await attendanceService.noShow(current!.ticket.id); return `Senha ${r.ticket.short_code} marcada como não compareceu.`; })}
                  />
                </View>
              </Card>
            </View>

            <View style={{ flex: 2, gap: spacing.lg }}>
              {state.data ? <QueueSummaryCard state={state.data} /> : null}
              <Card title="Identificação">
                <Meta label="Atendente" value={state.data?.user.name ?? '—'} />
                <Meta label="Guichê" value={`${session.counter.name} (nº ${String(session.counter.number).padStart(2, '0')})`} />
                <Meta label="No guichê desde" value={formatTime(session.opened_at)} />
                <Button
                  title="Sair do guichê"
                  icon={DoorOpen}
                  variant="secondary"
                  disabled={!!current || action.isPending}
                  onPress={() => run(async () => { await attendanceService.closeSession(); void queryClient.invalidateQueries({ queryKey: COUNTERS_KEY }); return 'Guichê liberado.'; })}
                />
              </Card>
            </View>
          </View>
        )}
      </ScrollView>
    </View>
  );
}

function Meta({ label, value }: { label: string; value: string }) {
  return (
    <View style={{ gap: 2, minWidth: 110 }}>
      <Text style={styles.metaLabel}>{label}</Text>
      <Text style={styles.metaValue}>{value}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  screen: { flex: 1, backgroundColor: colors.bg },
  content: { padding: spacing.xl, gap: spacing.lg, maxWidth: 1280, width: '100%', alignSelf: 'center' },
  columns: { gap: spacing.lg },
  muted: { color: colors.textMuted, fontSize: 13 },
  warn: { color: colors.warning, fontWeight: '700', textAlign: 'center' },
  ticketBox: { alignItems: 'center', gap: spacing.md, paddingVertical: spacing.md },
  ticketCode: { fontSize: 88, fontWeight: '900', letterSpacing: 3, fontVariant: ['tabular-nums'] },
  metaRow: { flexDirection: 'row', flexWrap: 'wrap', gap: spacing.xl, justifyContent: 'center' },
  metaLabel: { fontSize: 12, color: colors.textMuted, fontWeight: '600', textTransform: 'uppercase' },
  metaValue: { fontSize: 16, color: colors.text, fontWeight: '700' },
  steps: { flexDirection: 'row', gap: spacing.xl, marginTop: spacing.sm },
  step: { flexDirection: 'row', alignItems: 'center', gap: 6 },
  stepDot: { width: 12, height: 12, borderRadius: 6, backgroundColor: colors.border },
  stepLabel: { fontSize: 13, color: colors.textMuted, fontWeight: '700' },
  actions: { flexDirection: 'row', flexWrap: 'wrap', gap: spacing.md },
  actionBtn: { flexGrow: 1, flexBasis: 220 },
  queueRow: { flexDirection: 'row', gap: spacing.md },
  queueBox: { flex: 1, borderRadius: radius.md, padding: spacing.md, alignItems: 'center' },
  queueCount: { fontSize: 32, fontWeight: '900' },
  queueLabel: { fontSize: 12, color: colors.text, fontWeight: '600', textAlign: 'center' },
  counterGrid: { flexDirection: 'row', flexWrap: 'wrap', gap: spacing.md },
  counterTile: { width: 180, borderWidth: 1, borderColor: colors.border, borderRadius: radius.lg, padding: spacing.lg, backgroundColor: colors.primarySoft, gap: 4 },
  counterTileNumber: { fontSize: 36, fontWeight: '900', color: colors.primary },
  counterTileName: { fontSize: 15, fontWeight: '700', color: colors.text },
  counterTileStatus: { fontSize: 12, color: colors.textMuted },
});
