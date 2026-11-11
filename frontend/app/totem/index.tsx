import { useMutation, useQuery } from '@tanstack/react-query';
import { router } from 'expo-router';
import { Accessibility, ClipboardList, Users } from 'lucide-react-native';
import type { LucideIcon } from 'lucide-react-native';
import { useEffect, useState } from 'react';
import { ActivityIndicator, Pressable, StyleSheet, Text, View } from 'react-native';

import { LAB_NAME, TOTEM_RESET_SECONDS } from '@/constants/config';
import { useClock } from '@/hooks/useClock';
import { useResponsive } from '@/hooks/useResponsive';
import { errorMessage } from '@/services/api';
import { ticketService } from '@/services/ticketService';
import { colors, radius, spacing, typeColors } from '@/theme';
import type { IssuedTicket, TicketType } from '@/types/api';
import { formatDate, formatTime } from '@/utils/format';

const OPTIONS: { type: TicketType; title: string; subtitle: string; icon: LucideIcon }[] = [
  { type: 'SE', title: 'RETIRADA DE EXAMES', subtitle: 'Buscar resultados', icon: ClipboardList },
  { type: 'SP', title: 'ATENDIMENTO PRIORITÁRIO', subtitle: 'Idosos, gestantes, PcD e lactantes', icon: Accessibility },
  { type: 'SG', title: 'ATENDIMENTO GERAL', subtitle: 'Coleta e demais serviços', icon: Users },
];

export default function TotemScreen() {
  const { time } = useClock();
  const { isWide } = useResponsive();
  const [issued, setIssued] = useState<IssuedTicket | null>(null);
  const [countdown, setCountdown] = useState(TOTEM_RESET_SECONDS);

  const info = useQuery({ queryKey: ['ticket-types'], queryFn: ticketService.types, refetchInterval: 60_000 });
  const issue = useMutation({
    mutationFn: ticketService.issue,
    onSuccess: (data) => {
      setIssued(data);
      setCountdown(TOTEM_RESET_SECONDS);
    },
  });

  // Volta automaticamente para a tela de seleção.
  useEffect(() => {
    if (!issued) return;
    if (countdown <= 0) {
      setIssued(null);
      issue.reset();
      return;
    }
    const id = setTimeout(() => setCountdown((c) => c - 1), 1000);
    return () => clearTimeout(id);
  }, [issued, countdown, issue]);

  const closed = info.data && !info.data.issuing_allowed;

  return (
    <View style={styles.screen}>
      <View style={styles.header}>
        <Pressable onLongPress={() => router.replace('/')} delayLongPress={1500} accessibilityHint="Pressione longamente para sair do modo totem">
          <Text style={styles.lab}>{LAB_NAME}</Text>
        </Pressable>
        <Text style={styles.clock}>{time}</Text>
      </View>

      {issued ? (
        <Pressable style={styles.resultArea} onPress={() => setCountdown(0)} accessibilityLabel="Senha emitida. Toque para concluir">
          <View style={[styles.ticketCard, { borderColor: typeColors[issued.ticket.type].bg }]}>
            <Text style={styles.resultLabel}>Sua senha</Text>
            <Text style={[styles.ticketCode, { color: typeColors[issued.ticket.type].bg }]}>{issued.ticket.short_code}</Text>
            <Text style={styles.ticketType}>{issued.ticket.type_label}</Text>
            <View style={styles.divider} />
            <Text style={styles.ticketFull}>{issued.ticket.code}</Text>
            <Text style={styles.ticketMeta}>
              Emitida em {formatDate(issued.ticket.issued_at)} às {formatTime(issued.ticket.issued_at)}
            </Text>
            <Text style={styles.ticketMeta}>
              {issued.waiting_ahead === 0 ? 'Você é o próximo da sua categoria.' : `${issued.waiting_ahead} senha(s) da sua categoria à frente.`}
            </Text>
            <Text style={styles.hint}>Aguarde a chamada no painel. Voltando em {countdown}s…</Text>
          </View>
        </Pressable>
      ) : (
        <View style={styles.body}>
          <Text style={styles.prompt}>Toque no tipo de atendimento</Text>
          {issue.isError ? <Text style={styles.error}>{errorMessage(issue.error)}</Text> : null}
          {closed ? <Text style={styles.error}>Emissão de senhas encerrada. Horário: {info.data?.business_hours.issue_open} às {info.data?.business_hours.close}.</Text> : null}
          <View style={[styles.options, { flexDirection: isWide ? 'row' : 'column' }]}>
            {OPTIONS.map(({ type, title, subtitle, icon: Icon }) => (
              <Pressable
                key={type}
                accessibilityRole="button"
                accessibilityLabel={title}
                disabled={issue.isPending || !!closed}
                onPress={() => issue.mutate(type)}
                style={({ pressed }) => [
                  styles.option,
                  { backgroundColor: typeColors[type].bg, opacity: closed ? 0.4 : pressed ? 0.85 : 1, transform: [{ scale: pressed ? 0.98 : 1 }] },
                ]}
              >
                {issue.isPending && issue.variables === type ? <ActivityIndicator color="#fff" size="large" /> : <Icon color="#fff" size={56} />}
                <Text style={styles.optionTitle}>{title}</Text>
                <Text style={styles.optionSubtitle}>{subtitle}</Text>
              </Pressable>
            ))}
          </View>
        </View>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  screen: { flex: 1, backgroundColor: colors.bg },
  header: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', paddingHorizontal: spacing.xxl, paddingVertical: spacing.lg, backgroundColor: colors.primaryDark },
  lab: { color: colors.white, fontSize: 20, fontWeight: '800' },
  clock: { color: colors.white, fontSize: 22, fontWeight: '700', fontVariant: ['tabular-nums'] },
  body: { flex: 1, padding: spacing.xxl, gap: spacing.xl, justifyContent: 'center' },
  prompt: { fontSize: 30, fontWeight: '800', color: colors.text, textAlign: 'center' },
  error: { color: colors.danger, fontSize: 18, fontWeight: '700', textAlign: 'center' },
  options: { gap: spacing.xl, justifyContent: 'center', alignItems: 'stretch' },
  option: { flex: 1, minHeight: 200, borderRadius: radius.xl, padding: spacing.xxl, alignItems: 'center', justifyContent: 'center', gap: spacing.md },
  optionTitle: { color: '#fff', fontSize: 26, fontWeight: '900', textAlign: 'center', letterSpacing: 0.5 },
  optionSubtitle: { color: 'rgba(255,255,255,0.9)', fontSize: 16, textAlign: 'center' },
  resultArea: { flex: 1, alignItems: 'center', justifyContent: 'center', padding: spacing.xl },
  ticketCard: { backgroundColor: colors.surface, borderRadius: radius.xl, borderWidth: 4, padding: spacing.xxl, alignItems: 'center', gap: spacing.sm, width: '100%', maxWidth: 560 },
  resultLabel: { fontSize: 20, color: colors.textMuted, fontWeight: '700', textTransform: 'uppercase' },
  ticketCode: { fontSize: 112, fontWeight: '900', letterSpacing: 4, fontVariant: ['tabular-nums'] },
  ticketType: { fontSize: 24, fontWeight: '800', color: colors.text },
  divider: { height: 1, alignSelf: 'stretch', backgroundColor: colors.border, marginVertical: spacing.md },
  ticketFull: { fontSize: 18, color: colors.textMuted, fontVariant: ['tabular-nums'] },
  ticketMeta: { fontSize: 16, color: colors.text },
  hint: { marginTop: spacing.md, fontSize: 15, color: colors.textMuted },
});
