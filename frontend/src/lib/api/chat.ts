import apiClient from './client';

export interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
}

export interface ChatRequest {
  messages: ChatMessage[];
  session_id?: string;
  system_prompt?: string;
  user_location?: {
    lat: number;
    lng: number;
  };
}

export interface ChatInputModalities {
  image?: {
    filename?: string;
    image_type?: string;
    severity?: string;
    confidence?: number;
  };
  audio?: {
    filename?: string;
    transcription?: string;
  };
}

export interface ChatResponse {
  message: string;
  session_id: string;
  timestamp: string;
  metadata?: {
    status?: 'CRITICAL' | 'OK';
    red_flags?: string[];
    user_location?: { lat: number; lng: number };
    nearby_facilities?: Array<{
      name: string;
      distance_km: number;
      contact_number: string;
      coordinates: { lat: number; lng: number };
    }>;
    first_aid_instructions?: string[];
    input_modalities?: ChatInputModalities;
  };
}

export interface SymptomAnalysisRequest {
  symptoms: string;
  age?: number;
  gender?: string;
}

export interface SymptomAnalysisResponse {
  analysis: string;
  severity: string;
  possible_conditions: string[];
  recommendations: string;
}

export const chatAPI = {
  sendMessage: async (request: ChatRequest | FormData): Promise<ChatResponse> => {
    const response = await apiClient.post('/chat/chat', request);
    return response.data;
  },

  analyzeSymptoms: async (request: SymptomAnalysisRequest): Promise<SymptomAnalysisResponse> => {
    const response = await apiClient.post('/chat/analyze-symptoms', request);
    return response.data;
  },

  getChatHistory: async (sessionId: string) => {
    const response = await apiClient.get(`/chat/history/${sessionId}`);
    return response.data;
  },
};
