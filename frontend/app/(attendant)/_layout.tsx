import { Slot } from 'expo-router';

import { RoleGuard } from '@/components/RoleGuard';

export default function AttendantLayout() {
  return (
    <RoleGuard role="ATTENDANT">
      <Slot />
    </RoleGuard>
  );
}
