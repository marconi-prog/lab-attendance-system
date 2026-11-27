import { Slot } from 'expo-router';

import { RoleGuard } from '@/components/RoleGuard';

// O gestor também atende (somente nos guichês autorizados a ele).
const ROLES = ['ATTENDANT', 'ADMIN'] as const;

export default function AttendantLayout() {
  return (
    <RoleGuard roles={ROLES}>
      <Slot />
    </RoleGuard>
  );
}
