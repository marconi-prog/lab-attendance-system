import { zodResolver } from '@hookform/resolvers/zod';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { UserPlus } from 'lucide-react-native';
import { useState } from 'react';
import { Controller, useForm } from 'react-hook-form';
import { ScrollView, StyleSheet, Text, View } from 'react-native';
import { z } from 'zod';

import { Button } from '@/components/Button';
import { Card } from '@/components/Card';
import { Chips } from '@/components/Chips';
import { ErrorBanner, Loading, SuccessBanner } from '@/components/Feedback';
import { FormField, PlainField } from '@/components/FormField';
import { Pagination } from '@/components/Pagination';
import { Table } from '@/components/Table';
import { useAuth } from '@/contexts/AuthContext';
import { errorMessage } from '@/services/api';
import { counterService } from '@/services/counterService';
import { userService } from '@/services/userService';
import { colors, radius, spacing } from '@/theme';
import type { Counter, User, UserRole } from '@/types/api';

const password = z.string().min(8, 'Mínimo de 8 caracteres').regex(/[A-Za-z]/, 'Inclua letras').regex(/\d/, 'Inclua números');
const schema = z.object({
  name: z.string().trim().min(2, 'Informe o nome'),
  email: z.string().trim().email('E-mail inválido'),
  password: z.union([password, z.literal('')]),
  role: z.enum(['ADMIN', 'ATTENDANT']),
  counter_ids: z.array(z.number()),
});
type FormData = z.infer<typeof schema>;

function CounterSelector({ counters, value, onChange }: { counters: Counter[]; value: number[]; onChange: (ids: number[]) => void }) {
  return (
    <View style={{ gap: spacing.xs }}>
      <Text style={styles.label}>Guichês autorizados</Text>
      <View style={styles.wrap}>
        {counters.map((c) => {
          const on = value.includes(c.id);
          return (
            <Button
              key={c.id}
              size="sm"
              title={`${String(c.number).padStart(2, '0')}${c.active ? '' : ' (inativo)'}`}
              variant={on ? 'primary' : 'secondary'}
              onPress={() => onChange(on ? value.filter((id) => id !== c.id) : [...value, c.id])}
            />
          );
        })}
      </View>
    </View>
  );
}

function UserForm({ editing, counters, onDone }: { editing: User | null; counters: Counter[]; onDone: (msg: string) => void }) {
  const queryClient = useQueryClient();
  const [error, setError] = useState<string | null>(null);
  const { control, handleSubmit, reset, formState } = useForm<FormData>({
    resolver: zodResolver(schema.refine((d) => editing || d.password !== '', { path: ['password'], message: 'Informe a senha inicial' })),
    values: editing
      ? { name: editing.name, email: editing.email, password: '', role: editing.role, counter_ids: editing.counters.map((c) => c.id) }
      : { name: '', email: '', password: '', role: 'ATTENDANT', counter_ids: [] },
  });

  const submit = handleSubmit(async (data) => {
    setError(null);
    try {
      if (editing) {
        await userService.update(editing.id, { name: data.name, email: data.email, role: data.role, ...(data.password ? { password: data.password } : {}) });
        await userService.assignCounters(editing.id, data.counter_ids);
        onDone(`Usuário ${data.name} atualizado.`);
      } else {
        await userService.create({ ...data, password: data.password });
        onDone(`Usuário ${data.name} criado.`);
        reset();
      }
      void queryClient.invalidateQueries({ queryKey: ['users'] });
    } catch (e) {
      setError(errorMessage(e));
    }
  });

  return (
    <Card title={editing ? `Editar: ${editing.name}` : 'Novo usuário'}>
      <ErrorBanner message={error} />
      <View style={styles.wrap}>
        <FormField control={control} name="name" label="Nome" />
        <FormField control={control} name="email" label="E-mail" autoCapitalize="none" keyboardType="email-address" />
        <FormField control={control} name="password" label={editing ? 'Nova senha (opcional)' : 'Senha inicial'} secureTextEntry />
      </View>
      <Controller
        control={control}
        name="role"
        render={({ field }) => (
          <Chips<UserRole> label="Perfil" value={field.value} onChange={field.onChange} options={[{ value: 'ATTENDANT', label: 'Atendente' }, { value: 'ADMIN', label: 'Gestor (admin)' }]} />
        )}
      />
      <Controller control={control} name="counter_ids" render={({ field }) => <CounterSelector counters={counters} value={field.value} onChange={field.onChange} />} />
      <View style={styles.wrap}>
        <Button title={editing ? 'Salvar alterações' : 'Criar usuário'} icon={UserPlus} loading={formState.isSubmitting} onPress={() => void submit()} />
        {editing ? <Button title="Cancelar" variant="secondary" onPress={() => onDone('')} /> : null}
      </View>
    </Card>
  );
}

export default function UsersScreen() {
  const { user: me } = useAuth();
  const queryClient = useQueryClient();
  const [search, setSearch] = useState('');
  const [page, setPage] = useState(1);
  const [editing, setEditing] = useState<User | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const users = useQuery({ queryKey: ['users', search, page], queryFn: () => userService.list({ search: search || undefined, page, per_page: 15 }) });
  const counters = useQuery({ queryKey: ['counters'], queryFn: counterService.list });
  const toggle = useMutation({
    mutationFn: (u: User) => userService.update(u.id, { active: !u.active }),
    onSuccess: (u) => {
      setMessage(`${u.name} ${u.active ? 'ativado' : 'desativado'}.`);
      void queryClient.invalidateQueries({ queryKey: ['users'] });
    },
  });

  return (
    <ScrollView contentContainerStyle={styles.content}>
      <SuccessBanner message={message} />
      <ErrorBanner message={toggle.isError ? errorMessage(toggle.error) : null} />
      <UserForm
        key={editing?.id ?? 'new'}
        editing={editing}
        counters={counters.data ?? []}
        onDone={(msg) => {
          setEditing(null);
          setMessage(msg || null);
        }}
      />
      <Card title="Usuários" right={<View style={{ width: 260 }}><PlainField label="Buscar" value={search} onChangeText={(v) => { setSearch(v); setPage(1); }} placeholder="Nome ou e-mail" /></View>}>
        {users.isLoading ? <Loading /> : null}
        <ErrorBanner message={users.isError ? errorMessage(users.error) : null} />
        {users.data ? (
          <Table
            rows={users.data.items}
            rowKey={(u) => u.id}
            columns={[
              { key: 'n', title: 'Nome', width: 200, render: (u) => u.name },
              { key: 'e', title: 'E-mail', width: 220, render: (u) => u.email },
              { key: 'r', title: 'Perfil', width: 100, render: (u) => (u.role === 'ADMIN' ? 'Gestor' : 'Atendente') },
              { key: 'g', title: 'Guichês', width: 130, render: (u) => u.counters.map((c) => String(c.number).padStart(2, '0')).join(', ') || '—' },
              { key: 's', title: 'Situação', width: 90, render: (u) => <Text style={{ color: u.active ? colors.success : colors.danger, fontWeight: '700' }}>{u.active ? 'Ativo' : 'Inativo'}</Text> },
              {
                key: 'a',
                title: 'Ações',
                width: 220,
                render: (u) => (
                  <View style={styles.wrap}>
                    <Button size="sm" variant="secondary" title="Editar" onPress={() => setEditing(u)} />
                    <Button size="sm" variant={u.active ? 'danger' : 'success'} title={u.active ? 'Desativar' : 'Ativar'} disabled={u.id === me?.id} onPress={() => toggle.mutate(u)} />
                  </View>
                ),
              },
            ]}
          />
        ) : null}
        <Pagination meta={users.data?.meta} onChange={setPage} />
      </Card>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  content: { padding: spacing.xl, gap: spacing.lg, maxWidth: 1280, width: '100%', alignSelf: 'center' },
  wrap: { flexDirection: 'row', flexWrap: 'wrap', gap: spacing.sm },
  label: { fontSize: 13, fontWeight: '600', color: colors.text, borderRadius: radius.sm },
});
