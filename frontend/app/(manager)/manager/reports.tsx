import { useQuery } from '@tanstack/react-query';
import { useState } from 'react';
import { ScrollView, StyleSheet, Text, View } from 'react-native';

import { StatusBadge, TypeBadge } from '@/components/Badges';
import { Card } from '@/components/Card';
import { Chips } from '@/components/Chips';
import { EmptyState, ErrorBanner, Loading } from '@/components/Feedback';
import { PlainField } from '@/components/FormField';
import { Pagination } from '@/components/Pagination';
import { StatCard } from '@/components/StatCard';
import { Table } from '@/components/Table';
import { TICKET_TYPE_LABEL } from '@/constants/labels';
import { errorMessage } from '@/services/api';
import { reportService } from '@/services/reportService';
import { colors, spacing } from '@/theme';
import type { DailyReport, MonthlyReport, SummaryReport, TicketType } from '@/types/api';
import { currentMonthISO, formatDate, formatDuration, formatTime, isValidISODate, todayISO } from '@/utils/format';

type Mode = 'daily' | 'monthly' | 'period';

const isMonthly = (r: SummaryReport): r is MonthlyReport => 'by_day' in r;
const isDaily = (r: SummaryReport): r is DailyReport => 'by_hour' in r;

function SummaryBlock({ report }: { report: SummaryReport }) {
  const t = report.totals;
  return (
    <>
      <View style={styles.stats}>
        <StatCard label="Emitidas" value={t.issued} />
        <StatCard label="Atendidas" value={t.attended} tone={colors.success} />
        <StatCard label="Não atendidas" value={t.not_attended} tone={colors.danger} hint={`${t.no_show} ausências · ${t.discarded} descartadas`} />
        <StatCard label="Tempo médio" value={formatDuration(t.avg_attendance_seconds)} hint={`Espera média ${formatDuration(t.avg_wait_seconds)}`} />
      </View>
      <View style={styles.row}>
        <Card title="Por categoria" style={styles.flex}>
          <Table
            rows={report.by_type}
            rowKey={(r) => r.type}
            columns={[
              { key: 't', title: 'Categoria', width: 190, render: (r) => <TypeBadge type={r.type} /> },
              { key: 'i', title: 'Emitidas', width: 90, render: (r) => r.issued },
              { key: 'a', title: 'Atendidas', width: 100, render: (r) => r.attended },
              { key: 'n', title: 'Não atend.', width: 100, render: (r) => r.not_attended },
              { key: 'd', title: 'Tempo médio', width: 115, render: (r) => formatDuration(r.avg_attendance_seconds) },
              { key: 'w', title: 'Espera média', width: 115, render: (r) => formatDuration(r.avg_wait_seconds) },
            ]}
          />
        </Card>
        <Card title="Por atendente" style={styles.flex}>
          {report.by_attendant.length === 0 ? <EmptyState message="Sem atendimentos no período." /> : (
            <Table
              rows={report.by_attendant}
              rowKey={(r) => r.user_id}
              columns={[
                { key: 'n', title: 'Atendente', width: 200, render: (r) => r.name },
                { key: 'a', title: 'Atendimentos', width: 130, render: (r) => r.attended },
                { key: 'd', title: 'Tempo médio', width: 120, render: (r) => formatDuration(r.avg_attendance_seconds) },
              ]}
            />
          )}
        </Card>
        <Card title="Por guichê" style={styles.flex}>
          {report.by_counter.length === 0 ? <EmptyState message="Sem atendimentos no período." /> : (
            <Table
              rows={report.by_counter}
              rowKey={(r) => r.counter_id}
              columns={[
                { key: 'n', title: 'Guichê', width: 160, render: (r) => `${String(r.number).padStart(2, '0')} · ${r.name}` },
                { key: 'a', title: 'Atendimentos', width: 130, render: (r) => r.attended },
                { key: 'd', title: 'Tempo médio', width: 120, render: (r) => formatDuration(r.avg_attendance_seconds) },
              ]}
            />
          )}
        </Card>
      </View>
    </>
  );
}

export default function ReportsScreen() {
  const [mode, setMode] = useState<Mode>('daily');
  const [type, setType] = useState<TicketType | 'ALL'>('ALL');
  const [day, setDay] = useState(todayISO());
  const [month, setMonth] = useState(currentMonthISO());
  const [start, setStart] = useState(todayISO().slice(0, 8) + '01');
  const [end, setEnd] = useState(todayISO());
  const [page, setPage] = useState(1);
  const typeParam = type === 'ALL' ? undefined : type;

  const monthValid = /^\d{4}-(0[1-9]|1[0-2])$/.test(month);
  const period = (() => {
    if (mode === 'daily') return { start_date: day, end_date: day, valid: isValidISODate(day) };
    if (mode === 'monthly') {
      if (!monthValid) return { start_date: '', end_date: '', valid: false };
      const [y, m] = month.split('-').map(Number);
      const last = new Date(y, m, 0).getDate();
      return { start_date: `${month}-01`, end_date: `${month}-${String(last).padStart(2, '0')}`, valid: true };
    }
    return { start_date: start, end_date: end, valid: isValidISODate(start) && isValidISODate(end) && start <= end };
  })();

  const report = useQuery({
    queryKey: ['report', mode, day, month, start, end, typeParam],
    enabled: period.valid,
    queryFn: (): Promise<SummaryReport> =>
      mode === 'daily' ? reportService.daily(day, typeParam) : mode === 'monthly' ? reportService.monthly(month, typeParam) : reportService.summary({ start_date: start, end_date: end, type: typeParam }),
  });
  const history = useQuery({
    queryKey: ['history', period.start_date, period.end_date, typeParam, page],
    enabled: period.valid,
    queryFn: () => reportService.history({ start_date: period.start_date, end_date: period.end_date, type: typeParam, page, per_page: 20 }),
  });

  return (
    <ScrollView contentContainerStyle={styles.content}>
      <Card title="Filtros">
        <Chips<Mode>
          label="Relatório"
          value={mode}
          onChange={(m) => { setMode(m); setPage(1); }}
          options={[{ value: 'daily', label: 'Diário' }, { value: 'monthly', label: 'Mensal' }, { value: 'period', label: 'Período' }]}
        />
        <View style={styles.filters}>
          {mode === 'daily' ? <PlainField label="Data (AAAA-MM-DD)" value={day} onChangeText={(v) => { setDay(v); setPage(1); }} /> : null}
          {mode === 'monthly' ? <PlainField label="Mês (AAAA-MM)" value={month} onChangeText={(v) => { setMonth(v); setPage(1); }} /> : null}
          {mode === 'period' ? (
            <>
              <PlainField label="Início (AAAA-MM-DD)" value={start} onChangeText={(v) => { setStart(v); setPage(1); }} />
              <PlainField label="Fim (AAAA-MM-DD)" value={end} onChangeText={(v) => { setEnd(v); setPage(1); }} />
            </>
          ) : null}
        </View>
        <Chips<TicketType | 'ALL'>
          label="Categoria"
          value={type}
          onChange={(t) => { setType(t); setPage(1); }}
          options={[{ value: 'ALL', label: 'Todas' }, ...(['SP', 'SE', 'SG'] as TicketType[]).map((t) => ({ value: t, label: `${t} · ${TICKET_TYPE_LABEL[t]}` }))]}
        />
        {!period.valid ? <ErrorBanner message="Período inválido. Use o formato indicado e garanta que o início seja anterior ao fim." /> : null}
      </Card>

      {report.isLoading ? <Loading /> : null}
      <ErrorBanner message={report.isError ? errorMessage(report.error) : null} />
      {report.data ? <SummaryBlock report={report.data} /> : null}

      {report.data && isMonthly(report.data) ? (
        <Card title={`Detalhamento diário — ${report.data.month}`}>
          <Table
            rows={report.data.by_day.filter((d) => d.issued > 0)}
            rowKey={(r) => r.date}
            columns={[
              { key: 'd', title: 'Dia', width: 110, render: (r) => formatDate(r.date) },
              { key: 'i', title: 'Emitidas', width: 90, render: (r) => r.issued },
              { key: 'a', title: 'Atendidas', width: 90, render: (r) => r.attended },
              { key: 'n', title: 'Não atend.', width: 100, render: (r) => r.not_attended },
              { key: 't', title: 'Tempo médio', width: 120, render: (r) => formatDuration(r.avg_attendance_seconds) },
            ]}
          />
        </Card>
      ) : null}

      {report.data && isDaily(report.data) ? (
        <Card title="Emissões por hora">
          {report.data.by_hour.length === 0 ? <EmptyState message="Sem emissões." /> : null}
          {report.data.by_hour.map((h, _i, all) => {
            const max = Math.max(...all.map((x) => x.issued));
            return (
              <View key={h.hour} style={styles.barRow}>
                <Text style={styles.barLabel}>{String(h.hour).padStart(2, '0')}h</Text>
                <View style={[styles.bar, { flex: h.issued / max }]} />
                <View style={{ flex: 1 - h.issued / max }} />
                <Text style={styles.barValue}>{h.issued}</Text>
              </View>
            );
          })}
        </Card>
      ) : null}

      <Card title="Histórico de atendimentos">
        <ErrorBanner message={history.isError ? errorMessage(history.error) : null} />
        {history.data?.items.length === 0 ? <EmptyState message="Nenhuma senha no período." /> : null}
        {history.data && history.data.items.length > 0 ? (
          <Table
            rows={history.data.items}
            rowKey={(r) => r.ticket_id}
            columns={[
              { key: 'c', title: 'Senha', width: 130, render: (r) => r.code },
              { key: 't', title: 'Tipo', width: 70, render: (r) => <TypeBadge type={r.type} short /> },
              { key: 's', title: 'Situação', width: 160, render: (r) => <StatusBadge status={r.status} /> },
              { key: 'e', title: 'Emissão', width: 120, render: (r) => `${formatDate(r.issued_at).slice(0, 5)} ${formatTime(r.issued_at)}` },
              { key: 'ch', title: 'Chamada', width: 90, render: (r) => formatTime(r.first_called_at) + (r.call_count > 1 ? ' (2×)' : '') },
              { key: 'i', title: 'Início', width: 80, render: (r) => formatTime(r.started_at) },
              { key: 'f', title: 'Fim', width: 80, render: (r) => formatTime(r.finished_at) },
              { key: 'd', title: 'Duração', width: 100, render: (r) => formatDuration(r.duration_seconds) },
              { key: 'a', title: 'Atendente', width: 160, render: (r) => r.attendant?.name ?? '—' },
              { key: 'g', title: 'Guichê', width: 80, render: (r) => (r.counter ? String(r.counter.number).padStart(2, '0') : '—') },
            ]}
          />
        ) : null}
        <Pagination meta={history.data?.meta} onChange={setPage} />
      </Card>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  content: { padding: spacing.xl, gap: spacing.lg, maxWidth: 1280, width: '100%', alignSelf: 'center' },
  stats: { flexDirection: 'row', flexWrap: 'wrap', gap: spacing.md },
  row: { flexDirection: 'row', flexWrap: 'wrap', gap: spacing.lg },
  flex: { flexGrow: 1, flexBasis: 380 },
  filters: { flexDirection: 'row', flexWrap: 'wrap', gap: spacing.md },
  barRow: { flexDirection: 'row', alignItems: 'center', gap: spacing.sm },
  barLabel: { width: 36, color: colors.textMuted, fontSize: 13 },
  bar: { height: 16, backgroundColor: colors.primary, borderRadius: 4 },
  barValue: { width: 36, textAlign: 'right', fontWeight: '700', color: colors.text },
});
