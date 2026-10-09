import apiClient from './client';

export interface AdminStats {
  users: {
    total: number;
    active_30_days: number;
  };
  diagnoses: {
    total: number;
    today: number;
  };
  features: {
    chat_sessions: number;
    voice_interactions: number;
    image_analyses: number;
  };
}

interface DistributionResponse {
  severity: Record<string, number>;
  urgency: Record<string, number>;
}

export interface AuditLogRecord {
  id: number;
  session_id: string | null;
  source_endpoint: string;
  decision_type: string;
  input_summary: string | null;
  output_summary: string | null;
  confidence_band: string | null;
  urgency_level: string | null;
  model_name: string;
  model_version: string | null;
  prompt_version: string | null;
  override_applied: boolean;
  clinician_feedback: string | null;
  created_at: string;
}

export interface AuditLogsResponse {
  items: AuditLogRecord[];
  page: number;
  page_size: number;
  total: number;
}

export interface SessionMessage {
  id: number;
  role: string;
  content: string;
  created_at: string;
}

export interface SessionHistoryResponse {
  session_id: string;
  messages: SessionMessage[];
}

export interface BiasCheckRow {
  demographic: string;
  count: number;
}

export interface BiasUrgencyRow extends BiasCheckRow {
  urgency_level: string;
}

export interface BiasConfidenceRow extends BiasCheckRow {
  confidence_band: string;
}

export interface BiasCheckResponse {
  gender_urgency: BiasUrgencyRow[];
  gender_confidence: BiasConfidenceRow[];
  age_urgency: BiasUrgencyRow[];
  age_confidence: BiasConfidenceRow[];
}

export interface TrustedSourceRecord {
  id: number;
  provider: string;
  title: string;
  url: string;
  excerpt: string;
  condition_tags: string[];
  evidence_level: string | null;
  published_at: string | null;
  last_verified_at: string | null;
  is_active: boolean;
  created_at: string | null;
}

export interface TrustedSourceCreatePayload {
  provider: string;
  title: string;
  url: string;
  excerpt: string;
  condition_tags?: string[];
  evidence_level?: string;
  published_at?: string;
  last_verified_at?: string;
  metadata?: Record<string, unknown>;
}

export const adminAPI = {
  getOverview: async (): Promise<AdminStats> => {
    const response = await apiClient.get('/admin/stats/overview');
    return response.data;
  },

  getDiagnosesByDay: async (days: number = 30) => {
    const response = await apiClient.get('/admin/stats/diagnoses-by-day', {
      params: { days },
    });
    return response.data;
  },

  getSeverityDistribution: async () => {
    const response = await apiClient.get<DistributionResponse>('/admin/stats/distribution');
    return response.data.severity;
  },

  getUrgencyDistribution: async () => {
    const response = await apiClient.get<DistributionResponse>('/admin/stats/distribution');
    return response.data.urgency;
  },

  getRecentUsers: async (limit: number = 10) => {
    const response = await apiClient.get('/admin/users/recent', {
      params: { limit },
    });
    return response.data;
  },

  getRecentDiagnoses: async (limit: number = 10) => {
    const response = await apiClient.get('/admin/diagnoses/recent', {
      params: { limit },
    });
    return response.data;
  },

  getAuditLogs: async (params?: {
    page?: number;
    page_size?: number;
    q?: string;
    confidence_band?: string;
    decision_type?: string;
    overridden?: boolean;
  }) => {
    const response = await apiClient.get<AuditLogsResponse>('/admin/audit/logs', { params });
    return response.data;
  },

  getAuditSession: async (sessionId: string) => {
    const response = await apiClient.get<SessionHistoryResponse>(`/admin/audit/sessions/${sessionId}`);
    return response.data;
  },

  updateAuditFeedback: async (
    auditId: number,
    payload: { clinician_feedback: string | null; override_applied: boolean },
  ) => {
    const response = await apiClient.patch(`/admin/audit/${auditId}/feedback`, payload);
    return response.data;
  },

  getBiasCheck: async () => {
    const response = await apiClient.get<BiasCheckResponse>('/admin/analytics/bias-check');
    return response.data;
  },

  seedDemoAudits: async (count: number = 20) => {
    const response = await apiClient.post('/admin/audit/seed-demo', null, {
      params: { count },
    });
    return response.data as { inserted: number; environment: string };
  },

  listTrustedSources: async () => {
    const response = await apiClient.get<TrustedSourceRecord[]>('/rag/sources');
    return response.data;
  },

  createTrustedSource: async (payload: TrustedSourceCreatePayload) => {
    const response = await apiClient.post<TrustedSourceRecord>('/rag/sources', payload);
    return response.data;
  },

  seedDefaultTrustedSources: async () => {
    const response = await apiClient.post('/rag/sources/seed-defaults');
    return response.data as { inserted: number; skipped_existing: number };
  },
};
