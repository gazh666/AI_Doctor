'use client';

import { useEffect } from 'react';
import { CompleteDiagnosis } from '@/components/agents/CompleteDiagnosis';
import { useAuth } from '@/lib/auth/authContext';
import { useRouter } from 'next/navigation';

export default function DiagnosisPage() {
  const { isAuthenticated, loading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!loading && !isAuthenticated) {
      router.push('/login?next=/diagnosis');
    }
  }, [isAuthenticated, loading, router]);

  if (loading) {
    return <div className="p-8">Loading...</div>;
  }

  if (!isAuthenticated) {
    return null;
  }

  return (
    <div className="container mx-auto p-6 max-w-5xl">
      <div className="mb-8">
        <h1 className="text-3xl font-bold mb-2">Multi-Agent Diagnosis System 🤖</h1>
        <p className="text-gray-600">
          Comprehensive medical assessment using AI agent collaboration
        </p>
      </div>

      <CompleteDiagnosis />
    </div>
  );
}
