'use client';

import { useAuth } from '@/lib/auth/authContext';
import { DataExport } from '@/components/export/DataExport';
import { useRouter } from 'next/navigation';
import { useEffect } from 'react';

export default function ExportPage() {
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
    <div className="container mx-auto p-6 max-w-2xl">
      <div className="mb-6">
        <h1 className="text-3xl font-bold mb-2">Export Data</h1>
        <p className="text-gray-600">Download your diagnosis records in CSV, Excel, or JSON format.</p>
      </div>
      <DataExport />
    </div>
  );
}
