import { router, Slot, usePathname, type Href } from 'expo-router';
import { BarChart3, LayoutDashboard, MonitorSmartphone, ScrollText, Users } from 'lucide-react-native';
import type { LucideIcon } from 'lucide-react-native';
import { Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';

import { AppHeader } from '@/components/AppHeader';
import { ConnectionDot } from '@/components/ConnectionDot';
import { useStaffSocket } from '@/hooks/useStaffSocket';
import { colors, radius, spacing } from '@/theme';

const NAV: { href: Href; path: string; label: string; icon: LucideIcon }[] = [
  { href: '/manager', path: '/manager', label: 'Visão geral', icon: LayoutDashboard },
  { href: '/manager/reports', path: '/manager/reports', label: 'Relatórios', icon: BarChart3 },
  { href: '/manager/users', path: '/manager/users', label: 'Usuários', icon: Users },
  { href: '/manager/counters', path: '/manager/counters', label: 'Guichês', icon: MonitorSmartphone },
  { href: '/manager/audit', path: '/manager/audit', label: 'Auditoria', icon: ScrollText },
];

export default function ManagerLayout() {
  const pathname = usePathname();
  // Atualiza indicadores e sessões em tempo real.
  const connected = useStaffSocket([['dashboard'], ['sessions']]);
  return (
    <View style={styles.screen}>
      <AppHeader title="Gestão">
        <ConnectionDot connected={connected} />
      </AppHeader>
      <View style={styles.navWrap}>
        <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.nav}>
          {NAV.map(({ href, path, label, icon: Icon }) => {
            const active = pathname === path;
            return (
              <Pressable
                key={path}
                onPress={() => router.push(href)}
                style={[styles.navItem, active && styles.navItemActive]}
                accessibilityRole="tab"
                accessibilityState={{ selected: active }}
              >
                <Icon color={active ? colors.white : colors.primary} size={17} />
                <Text style={[styles.navText, active && { color: colors.white }]}>{label}</Text>
              </Pressable>
            );
          })}
        </ScrollView>
      </View>
      <View style={{ flex: 1 }}>
        <Slot />
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  screen: { flex: 1, backgroundColor: colors.bg },
  navWrap: { backgroundColor: colors.surface, borderBottomWidth: 1, borderBottomColor: colors.border },
  nav: { paddingHorizontal: spacing.xl, paddingVertical: spacing.sm, gap: spacing.sm },
  navItem: { flexDirection: 'row', alignItems: 'center', gap: 6, paddingHorizontal: 14, paddingVertical: 8, borderRadius: radius.md },
  navItemActive: { backgroundColor: colors.primary },
  navText: { color: colors.primary, fontWeight: '700', fontSize: 14 },
});
