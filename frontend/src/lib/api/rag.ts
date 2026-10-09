import apiClient from './client';

export interface RagUploadResponse {
  knowledge_base_id: string;
  filename: string;
  size_bytes: number;
  chunks_indexed: number;
  truncated: boolean;
  message: string;
}

export interface RagCitation {
  id: number;
  rank: number;
  title: string;
  source?: string;
  excerpt: string;
}

export interface RagQueryResponse {
  answer: string;
  matched_chunks: number;
  citations: RagCitation[];
}

export interface RagQueryRequest {
  question: string;
  top_k?: number;
}

export const ragAPI = {
  uploadFile: async (file: File): Promise<RagUploadResponse> => {
    const formData = new FormData();
    formData.append('file', file);

    const response = await apiClient.post<RagUploadResponse>('/rag/upload-pdf', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data;
  },

  ask: async (payload: RagQueryRequest): Promise<RagQueryResponse> => {
    const response = await apiClient.post<RagQueryResponse>('/rag/query', payload);
    return response.data;
  },
};
