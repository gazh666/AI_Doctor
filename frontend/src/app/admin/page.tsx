'use client';

import { AdminDashboard } from '@/components/admin/AdminDashboard';
import { TrustedSourcesManager } from '@/components/admin/TrustedSourcesManager';
import { AuditLogTable } from '@/components/admin/audit/AuditLogTable';
import { BiasMonitor } from '@/components/admin/audit/BiasMonitor';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { useAuth } from '@/lib/auth/authContext';
import { useRouter } from 'next/navigation';
import { useEffect } from 'react';

export default function AdminPage() {
  const { user, isAuthenticated, loading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!loading && (!isAuthenticated || user?.role !== 'admin')) {
      router.push('/login');
    }
  }, [isAuthenticated, user, loading, router]);

  if (loading) {
    return <div className="p-8">Loading...</div>;
  }

  if (!isAuthenticated || user?.role !== 'admin') {
    return null;
  }

  return (
    <div className="container mx-auto p-6">
      <Tabs defaultValue="overview" className="space-y-6">
        <TabsList>
          <TabsTrigger value="overview">Overview</TabsTrigger>
          <TabsTrigger value="audit-logs">AI Audit Logs</TabsTrigger>
          <TabsTrigger value="bias-monitoring">Bias Monitoring</TabsTrigger>
          <TabsTrigger value="trusted-sources">Trusted Sources</TabsTrigger>
        </TabsList>

        <TabsContent value="overview">
          <AdminDashboard />
        </TabsContent>

        <TabsContent value="audit-logs">
          <AuditLogTable />
        </TabsContent>

        <TabsContent value="bias-monitoring">
          <BiasMonitor />
        </TabsContent>

        <TabsContent value="trusted-sources">
          <TrustedSourcesManager />
        </TabsContent>
      </Tabs>
    </div>
  );
}
