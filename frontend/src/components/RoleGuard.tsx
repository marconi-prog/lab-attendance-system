import { Redirect } from 'expo-router';
import type { ReactNode } from 'react';

import { useAuth } from '@/contexts/AuthContext';
import type { UserRole } from '@/types/api';

import { Loading } from './Feedback';

/** Protege um grupo de rotas por perfil; redireciona para o login quando necessário. */
export function RoleGuard({ role, children }: { role: UserRole; children: ReactNode }) {
  const { user, loading } = useAuth();
  if (loading) return <Loading />;
  if (!user) return <Redirect href="/login" />;
  if (user.role !== role) return <Redirect href={user.role === 'ADMIN' ? '/manager' : '/attendant'} />;
  return <>{children}</>;
}
