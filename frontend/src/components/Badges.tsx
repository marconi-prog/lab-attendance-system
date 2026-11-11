import { StyleSheet, Text, View } from 'react-native';

import { STATUS_LABEL, TICKET_TYPE_LABEL } from '@/constants/labels';
import { statusColors, typeColors } from '@/theme';
import type { TicketStatus, TicketType } from '@/types/api';

export function StatusBadge({ status }: { status: TicketStatus }) {
  const c = statusColors[status];
  return (
    <View style={[styles.badge, { backgroundColor: c.bg }]}>
      <Text style={[styles.text, { color: c.fg }]}>{STATUS_LABEL[status]}</Text>
    </View>
  );
}

export function TypeBadge({ type, short }: { type: TicketType; short?: boolean }) {
  const c = typeColors[type];
  return (
    <View style={[styles.badge, { backgroundColor: c.bg }]}>
      <Text style={[styles.text, { color: c.fg }]}>{short ? type : `${type} · ${TICKET_TYPE_LABEL[type]}`}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  badge: { paddingHorizontal: 10, paddingVertical: 4, borderRadius: 999, alignSelf: 'flex-start' },
  text: { fontSize: 12, fontWeight: '700' },
});
