import { zodResolver } from '@hookform/resolvers/zod';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Plus } from 'lucide-react-native';
import { useState } from 'react';
import { useForm } from 'react-hook-form';
import { ScrollView, StyleSheet, Text, View } from 'react-native';
import { z } from 'zod';

import { Button } from '@/components/Button';
import { Card } from '@/components/Card';
import { EmptyState, ErrorBanner, Loading, SuccessBanner } from '@/components/Feedback';
import { FormField } from '@/components/FormField';
import { Table } from '@/components/Table';
import { errorMessage } from '@/services/api';
import { counterService } from '@/services/counterService';
import { colors, spacing } from '@/theme';
import type { Counter } from '@/types/api';
import { formatTime } from '@/utils/format';

const schema = z.object({
  name: z.string().trim().min(2, 'Informe o nome'),
  number: z.string().regex(/^\d{1,2}$/, 'Número de 1 a 99').refine((v) => Number(v) >= 1, 'Número de 1 a 99'),
});
type FormData = z.infer<typeof schema>;

export default function CountersScreen() {
  const queryClient = useQueryClient();
  const [message, setMessage] = useState<string | null>(null);
  const counters = useQuery({ queryKey: ['counters'], queryFn: counterService.list });
  const sessions = useQuery({ queryKey: ['sessions'], queryFn: counterService.sessions, refetchInterval: 30_000 });
  const invalidate = () => {
    void queryClient.invalidateQueries({ queryKey: ['counters'] });
    void queryClient.invalidateQueries({ queryKey: ['sessions'] });
  };

  const { control, handleSubmit, reset, formState } = useForm<FormData>({ resolver: zodResolver(schema), defaultValues: { name: '', number: '' } });
  const create = useMutation({
    mutationFn: (d: FormData) => counterService.create({ name: d.name, number: Number(d.number) }),
    onSuccess: (c) => {
      setMessage(`Guichê ${c.number} criado.`);
      reset();
      invalidate();
    },
  });
  const toggle = useMutation({
    mutationFn: (c: Counter) => counterService.update(c.id, { active: !c.active }),
    onSuccess: (c) => {
      setMessage(`Guichê ${c.number} ${c.active ? 'ativado' : 'desativado'}.`);
      invalidate();
    },
  });
  const closeSession = useMutation({
    mutationFn: counterService.forceCloseSession,
    onSuccess: () => {
      setMessage('Sessão encerrada.');
      invalidate();
    },
  });
  const anyError = create.error ?? toggle.error ?? closeSession.error;

  return (
    <ScrollView contentContainerStyle={styles.content}>
      <SuccessBanner message={message} />
      <ErrorBanner message={anyError ? errorMessage(anyError) : null} />
      <Card title="Novo guichê">
        <View style={styles.wrap}>
          <FormField control={control} name="name" label="Nome" placeholder="Guichê 06" />
          <FormField control={control} name="number" label="Número" keyboardType="number-pad" placeholder="6" />
        </View>
        <Button title="Criar guichê" icon={Plus} loading={formState.isSubmitting || create.isPending} onPress={handleSubmit((d) => create.mutate(d))} style={{ alignSelf: 'flex-start' }} />
      </Card>

      <Card title="Guichês">
        {counters.isLoading ? <Loading /> : null}
        {counters.data ? (
          <Table
            rows={counters.data}
            rowKey={(c) => c.id}
            columns={[
              { key: 'n', title: 'Número', width: 90, render: (c) => String(c.number).padStart(2, '0') },
              { key: 'm', title: 'Nome', width: 200, render: (c) => c.name },
              { key: 's', title: 'Situação', width: 100, render: (c) => <Text style={{ color: c.active ? colors.success : colors.danger, fontWeight: '700' }}>{c.active ? 'Ativo' : 'Inativo'}</Text> },
              { key: 'a', title: 'Ações', width: 140, render: (c) => <Button size="sm" variant={c.active ? 'danger' : 'success'} title={c.active ? 'Desativar' : 'Ativar'} onPress={() => toggle.mutate(c)} /> },
            ]}
          />
        ) : null}
      </Card>

      <Card title="Sessões abertas">
        {sessions.data?.length === 0 ? <EmptyState message="Nenhum guichê em uso." /> : null}
        {sessions.data?.map((s) => (
          <View key={s.id} style={styles.sessionRow}>
            <Text style={styles.bold}>Guichê {String(s.counter.number).padStart(2, '0')}</Text>
            <Text style={{ flex: 1, color: colors.text }}>{s.user.name} · desde {formatTime(s.opened_at)}</Text>
            <Button size="sm" variant="secondary" title="Encerrar sessão" onPress={() => closeSession.mutate(s.id)} />
          </View>
        ))}
        <Text style={styles.muted}>Use para liberar um guichê deixado aberto (ex.: navegador fechado). Senhas em andamento continuam vinculadas ao guichê.</Text>
      </Card>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  content: { padding: spacing.xl, gap: spacing.lg, maxWidth: 1280, width: '100%', alignSelf: 'center' },
  wrap: { flexDirection: 'row', flexWrap: 'wrap', gap: spacing.md },
  sessionRow: { flexDirection: 'row', alignItems: 'center', gap: spacing.md, paddingVertical: spacing.sm, borderBottomWidth: 1, borderBottomColor: colors.border, flexWrap: 'wrap' },
  bold: { fontWeight: '800', color: colors.primary },
  muted: { color: colors.textMuted, fontSize: 13 },
});
