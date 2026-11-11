import { zodResolver } from '@hookform/resolvers/zod';
import { Redirect, router } from 'expo-router';
import { LogIn } from 'lucide-react-native';
import { useState } from 'react';
import { useForm } from 'react-hook-form';
import { KeyboardAvoidingView, Platform, ScrollView, StyleSheet, Text, View } from 'react-native';
import { z } from 'zod';

import { Button } from '@/components/Button';
import { ErrorBanner } from '@/components/Feedback';
import { FormField } from '@/components/FormField';
import { LAB_NAME } from '@/constants/config';
import { useAuth } from '@/contexts/AuthContext';
import { errorMessage } from '@/services/api';
import { colors, radius, spacing } from '@/theme';

const schema = z.object({
  email: z.string().trim().min(1, 'Informe o e-mail').email('E-mail inválido'),
  password: z.string().min(1, 'Informe a senha'),
});
type FormData = z.infer<typeof schema>;

export default function LoginScreen() {
  const { user, login } = useAuth();
  const [error, setError] = useState<string | null>(null);
  const { control, handleSubmit, formState } = useForm<FormData>({ resolver: zodResolver(schema), defaultValues: { email: '', password: '' } });

  if (user) return <Redirect href={user.role === 'ADMIN' ? '/manager' : '/attendant'} />;

  const onSubmit = handleSubmit(async ({ email, password }) => {
    setError(null);
    try {
      const logged = await login(email, password);
      router.replace(logged.role === 'ADMIN' ? '/manager' : '/attendant');
    } catch (e) {
      setError(errorMessage(e));
    }
  });

  return (
    <KeyboardAvoidingView behavior={Platform.OS === 'ios' ? 'padding' : undefined} style={{ flex: 1 }}>
      <ScrollView contentContainerStyle={styles.container} keyboardShouldPersistTaps="handled">
        <View style={styles.card}>
          <Text style={styles.lab}>{LAB_NAME}</Text>
          <Text style={styles.title}>Acesso da equipe</Text>
          <Text style={styles.subtitle}>Atendentes e gestores</Text>
          <ErrorBanner message={error} />
          <FormField control={control} name="email" label="E-mail" keyboardType="email-address" autoCapitalize="none" autoComplete="email" />
          <FormField control={control} name="password" label="Senha" secureTextEntry autoComplete="password" onSubmitEditing={() => void onSubmit()} />
          <Button title="Entrar" icon={LogIn} size="lg" loading={formState.isSubmitting} onPress={() => void onSubmit()} />
          <Button title="Voltar ao início" variant="ghost" onPress={() => router.replace('/')} />
        </View>
      </ScrollView>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  container: { flexGrow: 1, backgroundColor: colors.primaryDark, alignItems: 'center', justifyContent: 'center', padding: spacing.xl },
  card: { width: '100%', maxWidth: 420, backgroundColor: colors.surface, borderRadius: radius.xl, padding: spacing.xxl, gap: spacing.lg },
  lab: { color: colors.primary, fontWeight: '700', fontSize: 12, textTransform: 'uppercase', letterSpacing: 0.6 },
  title: { fontSize: 26, fontWeight: '800', color: colors.text, marginTop: -8 },
  subtitle: { color: colors.textMuted, marginTop: -12 },
});
