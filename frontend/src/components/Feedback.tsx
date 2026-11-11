import { AlertCircle, CheckCircle2, Inbox } from 'lucide-react-native';
import { ActivityIndicator, StyleSheet, Text, View } from 'react-native';

import { colors, radius, spacing } from '@/theme';

export function ErrorBanner({ message }: { message?: string | null }) {
  if (!message) return null;
  return (
    <View style={[styles.banner, { backgroundColor: colors.dangerSoft, borderColor: '#F3C4C0' }]} accessibilityRole="alert">
      <AlertCircle color={colors.danger} size={18} />
      <Text style={[styles.bannerText, { color: colors.danger }]}>{message}</Text>
    </View>
  );
}

export function SuccessBanner({ message }: { message?: string | null }) {
  if (!message) return null;
  return (
    <View style={[styles.banner, { backgroundColor: colors.successSoft, borderColor: '#BDE5D5' }]}>
      <CheckCircle2 color={colors.success} size={18} />
      <Text style={[styles.bannerText, { color: colors.success }]}>{message}</Text>
    </View>
  );
}

export function Loading({ label = 'Carregando…' }: { label?: string }) {
  return (
    <View style={styles.center}>
      <ActivityIndicator color={colors.primary} size="large" />
      <Text style={styles.muted}>{label}</Text>
    </View>
  );
}

export function EmptyState({ message }: { message: string }) {
  return (
    <View style={styles.center}>
      <Inbox color={colors.textMuted} size={28} />
      <Text style={styles.muted}>{message}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  banner: { flexDirection: 'row', alignItems: 'center', gap: spacing.sm, padding: spacing.md, borderRadius: radius.md, borderWidth: 1 },
  bannerText: { flex: 1, fontSize: 14, fontWeight: '600' },
  center: { alignItems: 'center', justifyContent: 'center', padding: spacing.xl, gap: spacing.sm },
  muted: { color: colors.textMuted, fontSize: 14, textAlign: 'center' },
});
