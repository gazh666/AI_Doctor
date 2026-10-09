'use client';

import { useEffect, useState } from 'react';
import { Card } from '@/components/ui/card';
import { Activity, FileText, Mic, Image as ImageIcon } from 'lucide-react';
import { userAPI, UserDashboard as DashboardData } from '../../lib/api/users';
import { format } from 'date-fns';

export function UserDashboard() {
  const [dashboard, setDashboard] = useState<DashboardData | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadDashboard();

    // Keep dashboard metrics fresh when user returns to tab or stays on page.
    const onFocus = () => {
      loadDashboard();
    };

    const onVisibilityChange = () => {
      if (!document.hidden) {
        loadDashboard();
      }
    };

    window.addEventListener('focus', onFocus);
    document.addEventListener('visibilitychange', onVisibilityChange);
    const intervalId = window.setInterval(loadDashboard, 30000);

    return () => {
      window.removeEventListener('focus', onFocus);
      document.removeEventListener('visibilitychange', onVisibilityChange);
      window.clearInterval(intervalId);
    };
  }, []);

  const loadDashboard = async () => {
    try {
      const data = await userAPI.getDashboard();
      setDashboard(data);
    } catch (error) {
      console.error('Failed to load dashboard:', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return <div>Loading dashboard...</div>;
  }

  if (!dashboard) {
    return <div>Failed to load dashboard</div>;
  }

  const stats = [
    {
      title: 'Total Diagnoses',
      value: dashboard.total_diagnoses,
      icon: FileText,
      color: 'text-blue-600',
    },
    {
      title: 'Chat Sessions',
      value: dashboard.total_chat_sessions,
      icon: Activity,
      color: 'text-green-600',
    },
    {
      title: 'Voice Interactions',
      value: dashboard.total_voice_interactions,
      icon: Mic,
      color: 'text-purple-600',
    },
    {
      title: 'Image Analyses',
      value: dashboard.total_image_analyses,
      icon: ImageIcon,
      color: 'text-orange-600',
    },
  ];

  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-bold">Dashboard</h2>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {stats.map((stat) => (
          <Card key={stat.title} className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-600">{stat.title}</p>
                <p className="text-3xl font-bold mt-2">{stat.value}</p>
              </div>
              <stat.icon className={`w-12 h-12 ${stat.color}`} />
            </div>
          </Card>
        ))}
      </div>

      {/* Recent Diagnoses */}
      <Card className="p-6">
        <h3 className="text-lg font-semibold mb-4">Recent Diagnoses</h3>

        {dashboard.recent_diagnoses.length === 0 ? (
          <p className="text-gray-600">No diagnoses yet</p>
        ) : (
          <div className="space-y-3">
            {dashboard.recent_diagnoses.map((diagnosis) => (
              <div
                key={diagnosis.id}
                className="p-4 border rounded-lg hover:bg-gray-50"
              >
                <div className="flex justify-between items-start">
                  <div>
                    <p className="font-medium">{diagnosis.diagnosis}</p>
                    <p className="text-sm text-gray-600 mt-1">
                      Severity: {diagnosis.severity} | Confidence: {(diagnosis.confidence * 100).toFixed(0)}%
                    </p>
                  </div>
                  <span className="text-xs text-gray-500">
                    {format(new Date(diagnosis.created_at), 'MMM dd, yyyy')}
                  </span>
                </div>
              </div>
            ))}
          </div>
        )}
      </Card>

      {dashboard.last_activity && (
        <p className="text-sm text-gray-600">
          Last activity: {format(new Date(dashboard.last_activity), 'PPpp')}
        </p>
      )}
    </div>
  );
}