'use client';

import { useEffect, useState } from 'react';
import { Card } from '@/components/ui/card';
import { Users, FileText, Activity, TrendingUp } from 'lucide-react';
import { adminAPI, AdminStats } from '@/lib/api/admin';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, PieChart, Pie, Cell } from 'recharts';

export function AdminDashboard() {
  const [stats, setStats] = useState<AdminStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [diagnosesData, setDiagnosesData] = useState<any[]>([]);
  const [severityData, setSeverityData] = useState<any[]>([]);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      const [overview, diagnoses, severity] = await Promise.all([
        adminAPI.getOverview(),
        adminAPI.getDiagnosesByDay(30),
        adminAPI.getSeverityDistribution(),
      ]);

      setStats(overview);
      setDiagnosesData(diagnoses);

      // Transform severity data for pie chart
      const severityArray = Object.entries(severity).map(([name, value]) => ({
        name,
        value,
      }));
      setSeverityData(severityArray);
    } catch (error) {
      console.error('Failed to load admin data:', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return <div>Loading admin dashboard...</div>;
  }

  if (!stats) {
    return <div>Failed to load dashboard</div>;
  }

  const statCards = [
    {
      title: 'Total Users',
      value: stats.users.total,
      subtitle: `${stats.users.active_30_days} active (30 days)`,
      icon: Users,
      color: 'text-blue-600',
    },
    {
      title: 'Total Diagnoses',
      value: stats.diagnoses.total,
      subtitle: `${stats.diagnoses.today} today`,
      icon: FileText,
      color: 'text-green-600',
    },
    {
      title: 'Chat Sessions',
      value: stats.features.chat_sessions,
      subtitle: 'All time',
      icon: Activity,
      color: 'text-purple-600',
    },
    {
      title: 'Voice Interactions',
      value: stats.features.voice_interactions,
      subtitle: 'All time',
      icon: TrendingUp,
      color: 'text-orange-600',
    },
  ];

  const COLORS = ['#0088FE', '#00C49F', '#FFBB28', '#FF8042', '#8884D8'];

  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-bold">Admin Dashboard</h2>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {statCards.map((stat) => (
          <Card key={stat.title} className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-600">{stat.title}</p>
                <p className="text-3xl font-bold mt-2">{stat.value}</p>
                <p className="text-xs text-gray-500 mt-1">{stat.subtitle}</p>
              </div>
              <stat.icon className={`w-12 h-12 ${stat.color}`} />
            </div>
          </Card>
        ))}
      </div>

      {/* Diagnoses Over Time */}
      <Card className="p-6">
        <h3 className="text-lg font-semibold mb-4">Diagnoses (Last 30 Days)</h3>
        <ResponsiveContainer width="100%" height={300}>
          <LineChart data={diagnosesData}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="date" />
            <YAxis />
            <Tooltip />
            <Line type="monotone" dataKey="count" stroke="#8884d8" strokeWidth={2} />
          </LineChart>
        </ResponsiveContainer>
      </Card>

      {/* Severity Distribution */}
      <Card className="p-6">
        <h3 className="text-lg font-semibold mb-4">Severity Distribution</h3>
        <ResponsiveContainer width="100%" height={300}>
          <PieChart>
            <Pie
              data={severityData}
              cx="50%"
              cy="50%"
              labelLine={false}
              label={({ name, percent }) => `${name}: ${(percent * 100).toFixed(0)}%`}
              outerRadius={100}
              fill="#8884d8"
              dataKey="value"
            >
              {severityData.map((entry, index) => (
                <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
              ))}
            </Pie>
            <Tooltip />
          </PieChart>
        </ResponsiveContainer>
      </Card>
    </div>
  );
}