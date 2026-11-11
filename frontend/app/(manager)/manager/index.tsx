import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Ban, CheckCircle2, Clock, Hourglass, ListOrdered, Ticket, UserX } from 'lucide-react-native';
import { useState } from 'react';
import { ScrollView, StyleSheet, Text, View } from 'react-native';

import { StatusBadge, TypeBadge } from '@/components/Badges';
import { Button } from '@/components/Button';
import { Card } from '@/components/Card';
import { EmptyState, ErrorBanner, Loading, SuccessBanner } from '@/components/Feedback';
import { StatCard } from '@/components/StatCard';
import { Table } from '@/components/Table';
import { errorMessage } from '@/services/api';
import { reportService } from '@/services/reportService';
import { colors, spacing } from '@/theme';
import { formatDate, formatDuration, formatTime } from '@/utils/format';

export default function ManagerDashboard() {
  const queryClient = useQueryClient();
  const [message, setMessage] = useState<string | null>(null);
  const dashboard = useQuery({ queryKey: ['dashboard'], queryFn: reportService.dashboard, refetchInterval: 30_000 });
  const system = useQuery({ queryKey: ['system-info'], queryFn: reportService.systemInfo });
  const closeDay = useMutation({
    mutationFn: reportService.closeDay,
    onSuccess: (r) => {
      setMessage(`Expediente encerrado: ${r.discarded} senha(s) aguardando foram descartadas.`);
      void queryClient.invalidateQueries({ queryKey: ['dashboard'] });
    },
  });

  if (dashboard.isLoading) return <Loading />;
  if (dashboard.isError) return <View style={styles.content}><ErrorBanner message={errorMessage(dashboard.error)} /></View>;
  const d = dashboard.data!;

  return (
    <ScrollView contentContainerStyle={styles.content}>
      <Text style={styles.heading}>Hoje, {formatDate(d.date)}</Text>
      <SuccessBanner message={message} />
      <ErrorBanner message={closeDay.isError ? errorMessage(closeDay.error) : null} />
      <View style={styles.stats}>
        <StatCard label="Senhas emitidas" value={d.issued} icon={Ticket} />
        <StatCard label="Atendimentos realizados" value={d.attended} icon={CheckCircle2} tone={colors.success} />
        <StatCard label="Aguardando" value={d.waiting} icon={ListOrdered} tone={colors.warning} />
        <StatCard label="Em andamento" value={d.in_progress} icon={Hourglass} tone={colors.primary} />
        <StatCard label="Não compareceram" value={d.no_show} icon={UserX} tone={colors.danger} />
        <StatCard label="Descartadas" value={d.discarded} icon={Ban} tone={colors.textMuted} />
        <StatCard label="Tempo médio de atendimento" value={formatDuration(d.avg_attendance_seconds)} icon={Clock} hint={`Espera média: ${formatDuration(d.avg_wait_seconds)}`} />
      </View>

      <View style={styles.row}>
        <Card title="Por categoria" style={styles.flex}>
          <Table
            rows={d.by_type}
            rowKey={(r) => r.type}
            columns={[
              { key: 'type', title: 'Categoria', width: 190, render: (r) => <TypeBadge type={r.type} /> },
              { key: 'issued', title: 'Emitidas', width: 90, render: (r) => r.issued },
              { key: 'attended', title: 'Atendidas', width: 90, render: (r) => r.attended },
              { key: 'pending', title: 'Pendentes', width: 90, render: (r) => r.pending },
              { key: 'avg', title: 'Tempo médio', width: 120, render: (r) => formatDuration(r.avg_attendance_seconds) },
            ]}
          />
        </Card>
        <Card title="Guichês em operação" style={styles.flex}>
          {d.open_sessions.length === 0 ? <EmptyState message="Nenhum guichê aberto." /> : null}
          {d.open_sessions.map((s) => (
            <View key={s.session_id} style={styles.sessionRow}>
              <Text style={styles.sessionCounter}>{String(s.counter.number).padStart(2, '0')}</Text>
              <View style={{ flex: 1 }}>
                <Text style={styles.bold}>{s.attendant.name}</Text>
                <Text style={styles.muted}>desde {formatTime(s.opened_at)}</Text>
              </View>
              {s.current_ticket ? (
                <View style={{ alignItems: 'flex-end', gap: 4 }}>
                  <Text style={styles.bold}>{s.current_ticket.code}</Text>
                  <StatusBadge status={s.current_ticket.status} />
                </View>
              ) : (
                <Text style={styles.muted}>Livre</Text>
              )}
            </View>
          ))}
        </Card>
      </View>

      <View style={styles.row}>
        <Card title="Últimas chamadas" style={styles.flex}>
          {d.recent_calls.length === 0 ? <EmptyState message="Nenhuma chamada hoje." /> : null}
          {d.recent_calls.map((c) => (
            <View key={c.call_id} style={styles.sessionRow}>
              <TypeBadge type={c.type} short />
              <Text style={[styles.bold, { flex: 1 }]}>{c.short_code}{c.is_repeat ? ' (repetição)' : ''}</Text>
              <Text style={styles.muted}>Guichê {c.counter_label} · {formatTime(c.called_at)}</Text>
            </View>
          ))}
        </Card>
        <Card title="Sistema" style={styles.flex}>
          <Text style={styles.muted}>
            Expediente: {d.business_hours.open}–{d.business_hours.close} ({d.business_hours.timezone})
            {d.business_hours.enforced ? '' : ' · controle de horário DESATIVADO'}
          </Text>
          <Text style={styles.muted}>Chamadas permitidas agora: {d.business_hours.calling_allowed_now ? 'sim' : 'não'}</Text>
          {system.data ? (
            <>
              <Text style={styles.muted}>Versão {system.data.version} · {system.data.database.engine} {system.data.database.version}</Text>
              <Text style={styles.muted}>
                Usuários ativos: {system.data.counts.active_users} · Guichês ativos: {system.data.counts.active_counters}
              </Text>
            </>
          ) : null}
          <Button
            title="Encerrar expediente agora"
            variant="danger"
            loading={closeDay.isPending}
            onPress={() => closeDay.mutate()}
            accessibilityLabel="Encerrar expediente e descartar senhas aguardando"
          />
          <Text style={styles.muted}>Descarta as senhas que ainda aguardam. O encerramento ocorre automaticamente às {d.business_hours.close} quando o controle de horário está ativo.</Text>
        </Card>
      </View>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  content: { padding: spacing.xl, gap: spacing.lg, maxWidth: 1280, width: '100%', alignSelf: 'center' },
  heading: { fontSize: 22, fontWeight: '800', color: colors.text },
  stats: { flexDirection: 'row', flexWrap: 'wrap', gap: spacing.md },
  row: { flexDirection: 'row', flexWrap: 'wrap', gap: spacing.lg },
  flex: { flexGrow: 1, flexBasis: 420 },
  sessionRow: { flexDirection: 'row', alignItems: 'center', gap: spacing.md, paddingVertical: spacing.sm, borderBottomWidth: 1, borderBottomColor: colors.border },
  sessionCounter: { fontSize: 24, fontWeight: '900', color: colors.primary, width: 44 },
  bold: { fontWeight: '700', color: colors.text },
  muted: { color: colors.textMuted, fontSize: 13 },
});
