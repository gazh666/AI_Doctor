'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { ClinicalOpsConsole } from '@/components/ops/ClinicalOpsConsole';
import { useAuth } from '@/lib/auth/authContext';

export default function ClinicalOpsPage() {
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
    <div className="container mx-auto p-6 max-w-6xl space-y-4">
      <div>
        <h1 className="text-3xl font-bold">Clinical Ops Console</h1>
        <p className="text-gray-600">
          Validate triage, follow-ups, medication safety, sync, and audit flows from one place.
        </p>
      </div>
      <ClinicalOpsConsole />
    </div>
  );
}
