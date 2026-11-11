import { Link, type Href } from 'expo-router';
import { LayoutDashboard, LogIn, MonitorPlay, Ticket } from 'lucide-react-native';
import type { LucideIcon } from 'lucide-react-native';
import { Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';

import { LAB_NAME } from '@/constants/config';
import { useAuth } from '@/contexts/AuthContext';
import { colors, radius, spacing } from '@/theme';

function Entry({ href, title, description, icon: Icon }: { href: Href; title: string; description: string; icon: LucideIcon }) {
  return (
    <Link href={href} asChild>
      <Pressable style={({ pressed }) => [styles.entry, pressed && { opacity: 0.85 }]} accessibilityRole="link">
        <View style={styles.iconBox}>
          <Icon color={colors.primary} size={28} />
        </View>
        <Text style={styles.entryTitle}>{title}</Text>
        <Text style={styles.entryText}>{description}</Text>
      </Pressable>
    </Link>
  );
}

export default function Home() {
  const { user } = useAuth();
  const staffHref: Href = user ? (user.role === 'ADMIN' ? '/manager' : '/attendant') : '/login';
  return (
    <ScrollView contentContainerStyle={styles.container}>
      <Text style={styles.lab}>{LAB_NAME}</Text>
      <Text style={styles.title}>Sistema de Controle de Atendimento</Text>
      <Text style={styles.subtitle}>Escolha o modo de operação deste dispositivo.</Text>
      <View style={styles.grid}>
        <Entry href="/totem" title="Totem" description="Emissão de senhas pelo cliente, sem login." icon={Ticket} />
        <Entry href="/panel" title="Painel" description="Exibição pública das chamadas com áudio." icon={MonitorPlay} />
        <Entry
          href={staffHref}
          title={user ? (user.role === 'ADMIN' ? 'Gestão' : 'Atendimento') : 'Equipe'}
          description={user ? `Continuar como ${user.name}.` : 'Login de atendentes e gestores.'}
          icon={user?.role === 'ADMIN' ? LayoutDashboard : LogIn}
        />
      </View>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flexGrow: 1, backgroundColor: colors.bg, padding: spacing.xl, alignItems: 'center', justifyContent: 'center', gap: spacing.sm },
  lab: { color: colors.primary, fontWeight: '700', textTransform: 'uppercase', letterSpacing: 0.6 },
  title: { fontSize: 30, fontWeight: '800', color: colors.text, textAlign: 'center' },
  subtitle: { color: colors.textMuted, fontSize: 16, marginBottom: spacing.xl },
  grid: { flexDirection: 'row', flexWrap: 'wrap', gap: spacing.lg, justifyContent: 'center', maxWidth: 960 },
  entry: {
    width: 280,
    backgroundColor: colors.surface,
    borderRadius: radius.lg,
    borderWidth: 1,
    borderColor: colors.border,
    padding: spacing.xl,
    gap: spacing.sm,
  },
  iconBox: { width: 52, height: 52, borderRadius: radius.md, backgroundColor: colors.primarySoft, alignItems: 'center', justifyContent: 'center' },
  entryTitle: { fontSize: 20, fontWeight: '800', color: colors.text },
  entryText: { color: colors.textMuted, fontSize: 14, lineHeight: 20 },
});
