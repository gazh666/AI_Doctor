'use client';

import { useEffect } from 'react';
import { RagWorkspace } from '@/components/rag/RagWorkspace';
import { useAuth } from '@/lib/auth/authContext';
import { useRouter } from 'next/navigation';

export default function RagPage() {
  const { isAuthenticated, loading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!loading && !isAuthenticated) {
      router.push('/login?next=/rag');
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
        <h1 className="text-3xl font-bold mb-2">RAG Report Assistant</h1>
        <p className="text-gray-600">
          Upload your own medical PDF, TXT, MD, or CSV report, store it in your knowledge base, and ask grounded questions with citations.
        </p>
      </div>

      <RagWorkspace />
    </div>
  );
}
