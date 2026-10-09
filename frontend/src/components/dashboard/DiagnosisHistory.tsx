'use client';

import { useEffect, useState } from 'react';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Download, Trash2, Eye } from 'lucide-react';
import { userAPI, DiagnosisHistory as DiagnosisItem } from '../../lib/api/users';
import { format } from 'date-fns';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '../ui/dialog';

export function DiagnosisHistory() {
  const [diagnoses, setDiagnoses] = useState<DiagnosisItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedDiagnosis, setSelectedDiagnosis] = useState<DiagnosisItem | null>(null);
  const [showDetails, setShowDetails] = useState(false);

  useEffect(() => {
    loadHistory();
  }, []);

  const loadHistory = async () => {
    try {
      const data = await userAPI.getHistory();
      setDiagnoses(data);
    } catch (error) {
      console.error('Failed to load history:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleDownload = async (diagnosis: DiagnosisItem) => {
    try {
      await userAPI.downloadPDF(diagnosis.id, diagnosis);
    } catch (error) {
      console.error('Download failed:', error);
      alert('Failed to download PDF');
    }
  };

  const handleDelete = async (diagnosisId: number) => {
    if (!confirm('Are you sure you want to delete this diagnosis?')) {
      return;
    }

    try {
      await userAPI.deleteDiagnosis(diagnosisId);
      setDiagnoses(diagnoses.filter((d) => d.id !== diagnosisId));
    } catch (error) {
      console.error('Delete failed:', error);
      alert('Failed to delete diagnosis');
    }
  };

  const getSeverityColor = (severity: string) => {
    const colors: Record<string, string> = {
      normal: 'bg-green-100 text-green-800',
      mild: 'bg-yellow-100 text-yellow-800',
      moderate: 'bg-orange-100 text-orange-800',
      severe: 'bg-red-100 text-red-800',
      critical: 'bg-red-200 text-red-900',
    };
    return colors[severity?.toLowerCase()] || 'bg-gray-100 text-gray-800';
  };

  const getUrgencyColor = (urgency: string) => {
    const colors: Record<string, string> = {
      EMERGENCY: 'bg-red-100 text-red-800 border-red-300',
      URGENT: 'bg-orange-100 text-orange-800 border-orange-300',
      ROUTINE: 'bg-green-100 text-green-800 border-green-300',
    };
    return colors[urgency] || 'bg-gray-100 text-gray-800 border-gray-300';
  };

  if (loading) {
    return <div>Loading history...</div>;
  }

  return (
    <div className="space-y-4">
      <div className="flex justify-between items-center">
        <h2 className="text-2xl font-bold">Diagnosis History</h2>
        <p className="text-sm text-gray-600">{diagnoses.length} total records</p>
      </div>

      {diagnoses.length === 0 ? (
        <Card className="p-8 text-center">
          <p className="text-gray-600">No diagnosis history yet</p>
        </Card>
      ) : (
        <div className="space-y-3">
          {diagnoses.map((diagnosis) => (
            <Card key={diagnosis.id} className="p-6">
              <div className="flex justify-between items-start">
                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-2">
                    <Badge className={getUrgencyColor(diagnosis.urgency_level)}>
                      {diagnosis.urgency_level}
                    </Badge>
                    <Badge className={getSeverityColor(diagnosis.severity)}>
                      {diagnosis.severity}
                    </Badge>
                  </div>

                  <h3 className="text-lg font-semibold mb-1">{diagnosis.diagnosis}</h3>

                  <p className="text-sm text-gray-600">
                    Confidence: {(diagnosis.confidence * 100).toFixed(0)}%
                  </p>

                  <p className="text-xs text-gray-500 mt-2">
                    {format(new Date(diagnosis.created_at), 'PPpp')}
                  </p>
                </div>

                <div className="flex gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => {
                      setSelectedDiagnosis(diagnosis);
                      setShowDetails(true);
                    }}
                  >
                    <Eye className="w-4 h-4" />
                  </Button>

                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => handleDownload(diagnosis)}
                    className="shrink-0"
                  >
                    <Download className="w-4 h-4 mr-2" />
                    Report
                  </Button>

                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => handleDelete(diagnosis.id)}
                  >
                    <Trash2 className="w-4 h-4 text-red-600" />
                  </Button>
                </div>
              </div>
            </Card>
          ))}
        </div>
      )}

      {/* Details Dialog */}
      <Dialog open={showDetails} onOpenChange={setShowDetails}>
        <DialogContent className="max-w-2xl max-h-[80vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>Diagnosis Details</DialogTitle>
          </DialogHeader>

          {selectedDiagnosis && (
            <div className="space-y-4">
              <div>
                <h4 className="font-semibold mb-1">Diagnosis</h4>
                <p className="whitespace-pre-wrap wrap-break-word">{selectedDiagnosis.diagnosis}</p>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <h4 className="font-semibold mb-1">Severity</h4>
                  <Badge className={getSeverityColor(selectedDiagnosis.severity)}>
                    {selectedDiagnosis.severity}
                  </Badge>
                </div>

                <div>
                  <h4 className="font-semibold mb-1">Urgency</h4>
                  <Badge className={getUrgencyColor(selectedDiagnosis.urgency_level)}>
                    {selectedDiagnosis.urgency_level}
                  </Badge>
                </div>
              </div>

              <div>
                <h4 className="font-semibold mb-1">Confidence</h4>
                <p>{(selectedDiagnosis.confidence * 100).toFixed(0)}%</p>
              </div>

              <div>
                <h4 className="font-semibold mb-1">Date</h4>
                <p>{format(new Date(selectedDiagnosis.created_at), 'PPpp')}</p>
              </div>

              <div className="flex gap-2 pt-4">
                <Button onClick={() => handleDownload(selectedDiagnosis)}>
                  <Download className="w-4 h-4 mr-2" />
                  Download Report (PDF)
                </Button>
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}