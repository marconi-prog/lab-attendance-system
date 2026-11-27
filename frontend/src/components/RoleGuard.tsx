import { Redirect } from 'expo-router';
import type { ReactNode } from 'react';

import { useAuth } from '@/contexts/AuthContext';
import type { UserRole } from '@/types/api';

import { Loading } from './Feedback';

/**
 * Protege um grupo de rotas pelos perfis permitidos; redireciona para o login quando necessário.
 * A interface apenas orienta a navegação: a autorização real é sempre feita pela API.
 */
export function RoleGuard({ roles, children }: { roles: readonly UserRole[]; children: ReactNode }) {
  const { user, loading } = useAuth();
  if (loading) return <Loading />;
  if (!user) return <Redirect href="/login" />;
  if (!roles.includes(user.role)) return <Redirect href={user.role === 'ADMIN' ? '/manager' : '/attendant'} />;
  return <>{children}</>;
}
