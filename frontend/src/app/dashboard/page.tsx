'use client';

import { useAuth } from '@/lib/auth/authContext';
import { UserDashboard } from '@/components/dashboard/UserDashboard';
import { useRouter } from 'next/navigation';
import { useEffect } from 'react';

export default function DashboardRoutePage() {
  const { user, isAuthenticated, loading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!loading && !isAuthenticated) {
      router.push('/login');
      return;
    }

    if (!loading && isAuthenticated && user?.role === 'admin') {
      router.push('/admin');
    }
  }, [isAuthenticated, loading, router, user]);

  if (loading) {
    return <div className="p-8">Loading...</div>;
  }

  if (!isAuthenticated) {
    return null;
  }

  if (user?.role === 'admin') {
    return <div className="p-8">Redirecting to admin dashboard...</div>;
  }

  return (
    <div className="container mx-auto p-6">
      <UserDashboard />
    </div>
  );
}
