import type { LucideIcon } from 'lucide-react-native';
import { ActivityIndicator, Pressable, StyleSheet, Text, View, type StyleProp, type ViewStyle } from 'react-native';

import { colors, radius, spacing } from '@/theme';

type Variant = 'primary' | 'secondary' | 'danger' | 'success' | 'warning' | 'ghost';

const variants: Record<Variant, { bg: string; fg: string; border: string }> = {
  primary: { bg: colors.primary, fg: colors.white, border: colors.primary },
  secondary: { bg: colors.surface, fg: colors.primary, border: colors.border },
  danger: { bg: colors.danger, fg: colors.white, border: colors.danger },
  success: { bg: colors.success, fg: colors.white, border: colors.success },
  warning: { bg: colors.warning, fg: colors.white, border: colors.warning },
  ghost: { bg: 'transparent', fg: colors.primary, border: 'transparent' },
};

interface ButtonProps {
  title: string;
  onPress?: () => void;
  variant?: Variant;
  icon?: LucideIcon;
  loading?: boolean;
  disabled?: boolean;
  size?: 'sm' | 'md' | 'lg';
  style?: StyleProp<ViewStyle>;
  accessibilityLabel?: string;
}

export function Button({ title, onPress, variant = 'primary', icon: Icon, loading, disabled, size = 'md', style, accessibilityLabel }: ButtonProps) {
  const v = variants[variant];
  const inactive = disabled || loading;
  const pad = size === 'lg' ? 18 : size === 'sm' ? 8 : 12;
  const fontSize = size === 'lg' ? 18 : size === 'sm' ? 13 : 15;
  return (
    <Pressable
      accessibilityRole="button"
      accessibilityLabel={accessibilityLabel ?? title}
      accessibilityState={{ disabled: !!inactive, busy: !!loading }}
      onPress={onPress}
      disabled={inactive}
      style={({ pressed }) => [
        styles.base,
        { backgroundColor: v.bg, borderColor: v.border, paddingVertical: pad, opacity: inactive ? 0.45 : pressed ? 0.85 : 1 },
        style,
      ]}
    >
      <View style={styles.row}>
        {loading ? <ActivityIndicator color={v.fg} size="small" /> : Icon ? <Icon color={v.fg} size={fontSize + 3} /> : null}
        <Text style={[styles.label, { color: v.fg, fontSize }]}>{title}</Text>
      </View>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  base: { borderRadius: radius.md, borderWidth: 1, paddingHorizontal: spacing.lg, alignItems: 'center', justifyContent: 'center' },
  row: { flexDirection: 'row', alignItems: 'center', gap: spacing.sm },
  label: { fontWeight: '700', letterSpacing: 0.2 },
});
