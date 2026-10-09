'use client';

import { useEffect, useMemo, useState } from 'react';

import { Card } from '@/components/ui/card';
import { BiasCheckResponse, adminAPI } from '@/lib/api/admin';
import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';

const URGENCY_LEVELS = ['EMERGENCY', 'URGENT', 'ROUTINE', 'SELF-CARE', 'UNKNOWN'];

function toStackedUrgency(rows: BiasCheckResponse['gender_urgency' | 'age_urgency']) {
  const grouped: Record<string, Record<string, number | string>> = {};

  rows.forEach((row) => {
    if (!grouped[row.demographic]) {
      grouped[row.demographic] = { demographic: row.demographic };
      URGENCY_LEVELS.forEach((level) => {
        grouped[row.demographic][level] = 0;
      });
    }
    const urgency = (row.urgency_level || 'UNKNOWN').toUpperCase();
    grouped[row.demographic][urgency] = Number(row.count || 0);
  });

  return Object.values(grouped);
}

function toConfidenceList(rows: BiasCheckResponse['gender_confidence' | 'age_confidence']) {
  return rows.map((row) => ({
    ...row,
    confidence_band: row.confidence_band || 'Unknown',
  }));
}

export function BiasMonitor() {
  const [data, setData] = useState<BiasCheckResponse | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const load = async () => {
      setLoading(true);
      try {
        const res = await adminAPI.getBiasCheck();
        setData(res);
      } catch (err) {
        console.error('Failed to load bias check analytics', err);
        setData(null);
      } finally {
        setLoading(false);
      }
    };
    void load();
  }, []);

  const genderUrgencyData = useMemo(() => toStackedUrgency(data?.gender_urgency || []), [data?.gender_urgency]);
  const ageUrgencyData = useMemo(() => toStackedUrgency(data?.age_urgency || []), [data?.age_urgency]);
  const genderConfidenceData = useMemo(
    () => toConfidenceList(data?.gender_confidence || []),
    [data?.gender_confidence],
  );
  const ageConfidenceData = useMemo(() => toConfidenceList(data?.age_confidence || []), [data?.age_confidence]);

  if (loading) {
    return <div>Loading bias analytics...</div>;
  }

  if (!data) {
    return <div>Failed to load bias analytics.</div>;
  }

  return (
    <div className="space-y-6">
      <Card className="p-6">
        <h3 className="text-lg font-semibold mb-3">Urgency Distribution by Gender</h3>
        <ResponsiveContainer width="100%" height={320}>
          <BarChart data={genderUrgencyData}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="demographic" />
            <YAxis allowDecimals={false} />
            <Tooltip />
            <Legend />
            <Bar dataKey="EMERGENCY" stackId="a" fill="#dc2626" />
            <Bar dataKey="URGENT" stackId="a" fill="#f97316" />
            <Bar dataKey="ROUTINE" stackId="a" fill="#22c55e" />
            <Bar dataKey="SELF-CARE" stackId="a" fill="#3b82f6" />
            <Bar dataKey="UNKNOWN" stackId="a" fill="#6b7280" />
          </BarChart>
        </ResponsiveContainer>
      </Card>

      <Card className="p-6">
        <h3 className="text-lg font-semibold mb-3">Urgency Distribution by Age Group</h3>
        <ResponsiveContainer width="100%" height={320}>
          <BarChart data={ageUrgencyData}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="demographic" />
            <YAxis allowDecimals={false} />
            <Tooltip />
            <Legend />
            <Bar dataKey="EMERGENCY" stackId="b" fill="#dc2626" />
            <Bar dataKey="URGENT" stackId="b" fill="#f97316" />
            <Bar dataKey="ROUTINE" stackId="b" fill="#22c55e" />
            <Bar dataKey="SELF-CARE" stackId="b" fill="#3b82f6" />
            <Bar dataKey="UNKNOWN" stackId="b" fill="#6b7280" />
          </BarChart>
        </ResponsiveContainer>
      </Card>

      <Card className="p-6">
        <h3 className="text-lg font-semibold mb-3">Confidence by Gender</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
          {genderConfidenceData.map((item, idx) => (
            <div key={`${item.demographic}-${item.confidence_band}-${idx}`} className="border rounded-md p-3">
              <p className="font-medium">{item.demographic}</p>
              <p className="text-sm text-muted-foreground">Confidence: {item.confidence_band}</p>
              <p className="text-xl font-bold">{item.count}</p>
            </div>
          ))}
        </div>
      </Card>

      <Card className="p-6">
        <h3 className="text-lg font-semibold mb-3">Confidence by Age Group</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
          {ageConfidenceData.map((item, idx) => (
            <div key={`${item.demographic}-${item.confidence_band}-${idx}`} className="border rounded-md p-3">
              <p className="font-medium">{item.demographic}</p>
              <p className="text-sm text-muted-foreground">Confidence: {item.confidence_band}</p>
              <p className="text-xl font-bold">{item.count}</p>
            </div>
          ))}
        </div>
      </Card>
    </div>
  );
}

