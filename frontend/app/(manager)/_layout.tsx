import { Slot } from 'expo-router';

import { RoleGuard } from '@/components/RoleGuard';

const ROLES = ['ADMIN'] as const;

export default function ManagerGroupLayout() {
  return (
    <RoleGuard roles={ROLES}>
      <Slot />
    </RoleGuard>
  );
}
