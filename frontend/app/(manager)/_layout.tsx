import { Slot } from 'expo-router';

import { RoleGuard } from '@/components/RoleGuard';

export default function ManagerGroupLayout() {
  return (
    <RoleGuard role="ADMIN">
      <Slot />
    </RoleGuard>
  );
}
