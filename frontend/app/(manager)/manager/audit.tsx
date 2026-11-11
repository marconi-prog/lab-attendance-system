import { useQuery } from '@tanstack/react-query';
import { useState } from 'react';
import { ScrollView, StyleSheet, Text } from 'react-native';

import { Card } from '@/components/Card';
import { Chips } from '@/components/Chips';
import { EmptyState, ErrorBanner, Loading } from '@/components/Feedback';
import { Pagination } from '@/components/Pagination';
import { Table } from '@/components/Table';
import { errorMessage } from '@/services/api';
import { reportService } from '@/services/reportService';
import { colors, spacing } from '@/theme';
import { formatDateTime } from '@/utils/format';

const ACTIONS = [
  { value: '', label: 'Todas' },
  { value: 'LOGIN', label: 'Login' },
  { value: 'LOGIN_FAILED', label: 'Falha de login' },
  { value: 'TICKET_ISSUED', label: 'Emissão' },
  { value: 'TICKET_CALLED', label: 'Chamada' },
  { value: 'TICKET_RECALLED', label: 'Repetição' },
  { value: 'ATTENDANCE_STARTED', label: 'Início' },
  { value: 'ATTENDANCE_FINISHED', label: 'Finalização' },
  { value: 'TICKET_NO_SHOW', label: 'Ausência' },
  { value: 'DAY_CLOSED', label: 'Encerramento' },
  { value: 'USER_CREATED', label: 'Usuário criado' },
  { value: 'USER_UPDATED', label: 'Usuário alterado' },
];

export default function AuditScreen() {
  const [action, setAction] = useState('');
  const [page, setPage] = useState(1);
  const logs = useQuery({ queryKey: ['audit', action, page], queryFn: () => reportService.auditLogs({ action: action || undefined, page, per_page: 25 }) });

  return (
    <ScrollView contentContainerStyle={styles.content}>
      <Card title="Trilha de auditoria">
        <Chips<string> label="Ação" value={action} options={ACTIONS} onChange={(a) => { setAction(a); setPage(1); }} />
        {logs.isLoading ? <Loading /> : null}
        <ErrorBanner message={logs.isError ? errorMessage(logs.error) : null} />
        {logs.data?.items.length === 0 ? <EmptyState message="Nenhum registro." /> : null}
        {logs.data && logs.data.items.length > 0 ? (
          <Table
            rows={logs.data.items}
            rowKey={(l) => l.id}
            columns={[
              { key: 'd', title: 'Data/hora', width: 150, render: (l) => formatDateTime(l.created_at) },
              { key: 'u', title: 'Usuário', width: 170, render: (l) => l.user?.name ?? 'Sistema / Totem' },
              { key: 'a', title: 'Ação', width: 190, render: (l) => <Text style={styles.action}>{l.action}</Text> },
              { key: 'e', title: 'Entidade', width: 120, render: (l) => `${l.entity}${l.entity_id ? ` #${l.entity_id}` : ''}` },
              { key: 'x', title: 'Detalhes', width: 320, render: (l) => (l.details ? Object.entries(l.details).map(([k, v]) => `${k}: ${JSON.stringify(v)}`).join(' · ') : '—') },
              { key: 'i', title: 'IP', width: 120, render: (l) => l.ip_address ?? '—' },
            ]}
          />
        ) : null}
        <Pagination meta={logs.data?.meta} onChange={setPage} />
      </Card>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  content: { padding: spacing.xl, gap: spacing.lg, maxWidth: 1280, width: '100%', alignSelf: 'center' },
  action: { fontWeight: '700', color: colors.primary, fontSize: 13 },
});
