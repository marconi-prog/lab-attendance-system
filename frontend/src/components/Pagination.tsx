import { ChevronLeft, ChevronRight } from 'lucide-react-native';
import { StyleSheet, Text, View } from 'react-native';

import { colors, spacing } from '@/theme';
import type { PageMeta } from '@/types/api';

import { Button } from './Button';

export function Pagination({ meta, onChange }: { meta?: PageMeta; onChange: (page: number) => void }) {
  if (!meta || meta.pages <= 1) return meta ? <Text style={styles.info}>{meta.total} registro(s)</Text> : null;
  return (
    <View style={styles.row}>
      <Button title="Anterior" icon={ChevronLeft} size="sm" variant="secondary" disabled={meta.page <= 1} onPress={() => onChange(meta.page - 1)} />
      <Text style={styles.info}>
        Página {meta.page} de {meta.pages} · {meta.total} registro(s)
      </Text>
      <Button title="Próxima" icon={ChevronRight} size="sm" variant="secondary" disabled={meta.page >= meta.pages} onPress={() => onChange(meta.page + 1)} />
    </View>
  );
}

const styles = StyleSheet.create({
  row: { flexDirection: 'row', alignItems: 'center', gap: spacing.md, flexWrap: 'wrap' },
  info: { color: colors.textMuted, fontSize: 13 },
});
