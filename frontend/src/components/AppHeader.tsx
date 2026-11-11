import { LogOut } from 'lucide-react-native';
import type { ReactNode } from 'react';
import { StyleSheet, Text, View } from 'react-native';

import { LAB_NAME } from '@/constants/config';
import { useAuth } from '@/contexts/AuthContext';
import { colors, spacing } from '@/theme';

import { Button } from './Button';

export function AppHeader({ title, children }: { title: string; children?: ReactNode }) {
  const { user, logout } = useAuth();
  return (
    <View style={styles.header}>
      <View style={{ flexShrink: 1 }}>
        <Text style={styles.lab}>{LAB_NAME}</Text>
        <Text style={styles.title}>{title}</Text>
      </View>
      <View style={styles.right}>
        {children}
        {user ? (
          <View style={{ alignItems: 'flex-end' }}>
            <Text style={styles.user}>{user.name}</Text>
            <Text style={styles.role}>{user.role === 'ADMIN' ? 'Gestor' : 'Atendente'}</Text>
          </View>
        ) : null}
        <Button title="Sair" icon={LogOut} variant="secondary" size="sm" onPress={() => void logout()} />
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  header: {
    backgroundColor: colors.primaryDark,
    paddingHorizontal: spacing.xl,
    paddingVertical: spacing.lg,
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    flexWrap: 'wrap',
    gap: spacing.md,
  },
  lab: { color: '#A9CBE3', fontSize: 12, fontWeight: '600', letterSpacing: 0.4, textTransform: 'uppercase' },
  title: { color: colors.white, fontSize: 22, fontWeight: '800' },
  right: { flexDirection: 'row', alignItems: 'center', gap: spacing.md, flexWrap: 'wrap' },
  user: { color: colors.white, fontWeight: '700' },
  role: { color: '#A9CBE3', fontSize: 12 },
});
