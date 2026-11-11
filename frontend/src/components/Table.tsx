import type { ReactNode } from 'react';
import { ScrollView, StyleSheet, Text, View } from 'react-native';

import { colors, spacing } from '@/theme';

export interface Column<T> {
  key: string;
  title: string;
  width?: number;
  render: (row: T) => ReactNode;
}

/** Tabela com rolagem horizontal (útil em telas estreitas). */
export function Table<T>({ columns, rows, rowKey }: { columns: Column<T>[]; rows: T[]; rowKey: (row: T) => string | number }) {
  return (
    <ScrollView horizontal showsHorizontalScrollIndicator>
      <View>
        <View style={[styles.row, styles.head]}>
          {columns.map((c) => (
            <Text key={c.key} style={[styles.cell, styles.headText, { width: c.width ?? 140 }]}>
              {c.title}
            </Text>
          ))}
        </View>
        {rows.map((row) => (
          <View key={rowKey(row)} style={styles.row}>
            {columns.map((c) => {
              const content = c.render(row);
              return (
                <View key={c.key} style={[styles.cell, { width: c.width ?? 140 }]}>
                  {typeof content === 'string' || typeof content === 'number' ? <Text style={styles.text}>{content}</Text> : content}
                </View>
              );
            })}
          </View>
        ))}
      </View>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  row: { flexDirection: 'row', borderBottomWidth: 1, borderBottomColor: colors.border, alignItems: 'center' },
  head: { backgroundColor: colors.bg },
  cell: { paddingVertical: 10, paddingHorizontal: spacing.sm },
  headText: { fontSize: 12, fontWeight: '700', color: colors.textMuted, textTransform: 'uppercase' },
  text: { fontSize: 14, color: colors.text },
});
