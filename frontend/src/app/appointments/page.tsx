'use client';

import { useAuth } from '@/lib/auth/authContext';
import { AppointmentScheduler } from '@/components/appointments/AppointmentScheduler';
import { useRouter } from 'next/navigation';
import { useEffect } from 'react';

export default function AppointmentsPage() {
  const { isAuthenticated, loading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!loading && !isAuthenticated) {
      router.push('/login');
    }
  }, [isAuthenticated, loading, router]);

  if (loading) {
    return <div className="p-8">Loading...</div>;
  }

  if (!isAuthenticated) {
    return null;
  }

  return (
    <div className="container mx-auto p-6 max-w-4xl">
      <div className="mb-6">
        <h1 className="text-3xl font-bold mb-2">Appointments</h1>
        <p className="text-gray-600">Schedule and manage your clinical consultations.</p>
      </div>
      <AppointmentScheduler />
    </div>
  );
}
