import { StyleSheet, Text, View } from 'react-native';

export function ConnectionDot({ connected, dark }: { connected: boolean; dark?: boolean }) {
  return (
    <View style={styles.row} accessibilityLabel={connected ? 'Tempo real conectado' : 'Tempo real desconectado'}>
      <View style={[styles.dot, { backgroundColor: connected ? '#22C55E' : '#F59E0B' }]} />
      <Text style={[styles.text, { color: dark ? '#9EC3DD' : '#A9CBE3' }]}>{connected ? 'Tempo real' : 'Reconectando…'}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  row: { flexDirection: 'row', alignItems: 'center', gap: 6 },
  dot: { width: 9, height: 9, borderRadius: 5 },
  text: { fontSize: 12, fontWeight: '600' },
});
