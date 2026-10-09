import apiClient from './client';
import jsPDF from 'jspdf';

export interface DiagnosisHistory {
  id: number;
  diagnosis: string;
  confidence: number;
  severity: string;
  urgency_level: string;
  created_at: string;
}

export interface UserDashboard {
  total_diagnoses: number;
  recent_diagnoses: DiagnosisHistory[];
  total_chat_sessions: number;
  total_voice_interactions: number;
  total_image_analyses: number;
  last_activity: string | null;
}

const downloadBlobAsFile = (blob: Blob, filename: string) => {
  const url = window.URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.setAttribute('download', filename);
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.URL.revokeObjectURL(url);
};

const generateFallbackDiagnosisPdf = (diagnosis: DiagnosisHistory) => {
  const doc = new jsPDF();
  const pageWidth = doc.internal.pageSize.getWidth();
  const margin = 14;
  const contentWidth = pageWidth - margin * 2;
  let y = 18;

  const ensurePage = (extraHeight: number = 8) => {
    if (y + extraHeight > 280) {
      doc.addPage();
      y = 18;
    }
  };

  const writeWrapped = (text: string, fontSize: number = 11) => {
    const lines = doc.splitTextToSize(text, contentWidth);
    doc.setFontSize(fontSize);
    for (const line of lines) {
      ensurePage(7);
      doc.text(line, margin, y);
      y += 6;
    }
  };

  doc.setFontSize(16);
  doc.text('Rural AI Doctor - Diagnosis Report', margin, y);
  y += 10;

  doc.setFontSize(10);
  doc.text(`Report ID: ${diagnosis.id}`, margin, y);
  y += 6;
  doc.text(`Date: ${new Date(diagnosis.created_at).toLocaleString()}`, margin, y);
  y += 6;
  doc.text(`Severity: ${diagnosis.severity}`, margin, y);
  y += 6;
  doc.text(`Urgency: ${diagnosis.urgency_level}`, margin, y);
  y += 6;
  doc.text(`Confidence: ${(diagnosis.confidence * 100).toFixed(0)}%`, margin, y);
  y += 10;

  doc.setFontSize(12);
  doc.text('Diagnosis', margin, y);
  y += 7;
  writeWrapped(diagnosis.diagnosis || 'No diagnosis text available.');

  y += 8;
  writeWrapped(
    'Disclaimer: This AI analysis is for informational purposes only and does not replace professional medical advice.',
    9
  );

  doc.save(`diagnosis_report_${diagnosis.id}.pdf`);
};

export const userAPI = {
  getDashboard: async (): Promise<UserDashboard> => {
    const response = await apiClient.get('/users/dashboard');
    return response.data;
  },

  getHistory: async (skip: number = 0, limit: number = 10): Promise<DiagnosisHistory[]> => {
    const response = await apiClient.get('/users/history/diagnoses', {
      params: { skip, limit },
    });
    return response.data;
  },

  deleteDiagnosis: async (diagnosisId: number) => {
    const response = await apiClient.delete(`/users/history/diagnosis/${diagnosisId}`);
    return response.data;
  },

  downloadPDF: async (diagnosisId: number, diagnosisData?: DiagnosisHistory) => {
    try {
      const response = await apiClient.get(`/reports/diagnosis/${diagnosisId}/pdf`, {
        responseType: 'blob',
      });

      downloadBlobAsFile(new Blob([response.data]), `diagnosis_report_${diagnosisId}.pdf`);
    } catch (error) {
      if (diagnosisData) {
        // Fallback to client-side PDF when backend PDF endpoint is unavailable.
        generateFallbackDiagnosisPdf(diagnosisData);
        return;
      }
      throw error;
    }
  },
};