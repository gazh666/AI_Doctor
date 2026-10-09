import apiClient from './client';
import { getApiBaseUrl } from './base-url';

export interface TranscriptionResponse {
  transcription_id: number;
  text: string;
  language: string;
  confidence: number;
  duration_seconds: number;
  session_id: string;
  created_at: string;
}

export interface VoiceDiagnosisResponse {
  transcription: string;
  diagnosis_result: {
    diagnosis: string;
    confidence: number;
    urgency: 'ROUTINE' | 'URGENT' | 'EMERGENCY';
    treatment_summary: string[];
    full_report: string;
  };
  audio_response?: string;
}

export type LiveClientEventType =
  | 'auth'
  | 'session.configure'
  | 'turn.start'
  | 'turn.audio_chunk'
  | 'turn.end'
  | 'ping';

export type LiveServerEventType =
  | 'auth.ok'
  | 'turn.transcript'
  | 'turn.response'
  | 'turn.audio'
  | 'turn.error'
  | 'pong';

export interface LiveVoiceClientEvent {
  type: LiveClientEventType;
  token?: string;
  session_id?: string;
  turn_id?: string;
  language?: string;
  age?: number;
  gender?: string;
  medical_history?: string;
  audio?: string;
  mime_type?: string;
  timestamp?: string;
}

export interface LiveVoiceServerEvent {
  type: LiveServerEventType;
  session_id?: string;
  turn_id?: string;
  transcript?: string;
  response_text?: string;
  urgency?: 'ROUTINE' | 'URGENT' | 'EMERGENCY';
  red_flags?: string[];
  audio?: string;
  mime_type?: string;
  message?: string;
  timestamp?: string;
}

export interface LiveSessionConfig {
  sessionId?: string;
  language?: string;
  age?: number;
  gender?: string;
  medicalHistory?: string;
}

export function getVoiceLiveWebSocketUrl(): string {
  const apiBase = getApiBaseUrl();
  const url = new URL(apiBase);
  url.protocol = url.protocol === 'https:' ? 'wss:' : 'ws:';
  url.pathname = `${url.pathname.replace(/\/$/, '')}/voice/live`;
  return url.toString();
}

function blobToBase64(blob: Blob): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onloadend = () => {
      const result = reader.result;
      if (typeof result !== 'string') {
        reject(new Error('Failed to encode audio chunk.'));
        return;
      }
      const base64 = result.split(',')[1];
      if (!base64) {
        reject(new Error('Encoded chunk is empty.'));
        return;
      }
      resolve(base64);
    };
    reader.onerror = () => reject(new Error('Unable to read audio chunk.'));
    reader.readAsDataURL(blob);
  });
}

export class LiveVoiceConsultationClient {
  private ws: WebSocket | null = null;
  private onEvent: ((event: LiveVoiceServerEvent) => void) | null = null;
  private onClose: (() => void) | null = null;

  connect(
    accessToken: string,
    onEvent: (event: LiveVoiceServerEvent) => void,
    onClose?: () => void
  ): Promise<void> {
    this.onEvent = onEvent;
    this.onClose = onClose ?? null;

    return new Promise((resolve, reject) => {
      const ws = new WebSocket(getVoiceLiveWebSocketUrl());
      this.ws = ws;

      ws.onopen = () => {
        ws.send(
          JSON.stringify({
            type: 'auth',
            token: `Bearer ${accessToken}`,
          } satisfies LiveVoiceClientEvent)
        );
      };

      ws.onmessage = (event) => {
        const parsed = JSON.parse(event.data) as LiveVoiceServerEvent;
        this.onEvent?.(parsed);
        if (parsed.type === 'auth.ok') {
          resolve();
        }
      };

      ws.onerror = () => {
        reject(new Error('Unable to connect to live voice consultation.'));
      };

      ws.onclose = () => {
        this.ws = null;
        this.onClose?.();
      };
    });
  }

  configureSession(config: LiveSessionConfig): void {
    this.send({
      type: 'session.configure',
      session_id: config.sessionId,
      language: config.language,
      age: config.age,
      gender: config.gender,
      medical_history: config.medicalHistory,
    });
  }

  startTurn(turnId: string): void {
    this.send({
      type: 'turn.start',
      turn_id: turnId,
    });
  }

  async sendAudioChunk(chunk: Blob, mimeType?: string): Promise<void> {
    const audio = await blobToBase64(chunk);
    this.send({
      type: 'turn.audio_chunk',
      audio,
      mime_type: mimeType ?? chunk.type ?? 'audio/webm',
    });
  }

  endTurn(turnId: string): void {
    this.send({
      type: 'turn.end',
      turn_id: turnId,
    });
  }

  ping(): void {
    this.send({ type: 'ping' });
  }

  disconnect(): void {
    this.ws?.close();
    this.ws = null;
  }

  private send(payload: LiveVoiceClientEvent): void {
    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
      throw new Error('Live voice socket is not connected.');
    }
    this.ws.send(JSON.stringify(payload));
  }
}

export const voiceAPI = {
  transcribe: async (
    audioFile: File | Blob,
    language?: string,
    sessionId?: string
  ): Promise<TranscriptionResponse> => {
    const formData = new FormData();
    formData.append('file', audioFile, 'recording.wav');

    if (language && language !== 'string') formData.append('language', language);
    if (sessionId && sessionId !== 'string') formData.append('session_id', sessionId);

    const response = await apiClient.post('/voice/transcribe', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return response.data;
  },

  textToSpeech: async (text: string, language: string = 'en', slow: boolean = false): Promise<Blob> => {
    const response = await apiClient.post(
      '/voice/speak',
      { text, language, slow },
      { responseType: 'blob' }
    );
    return response.data;
  },

  voiceDiagnosis: async (
    audioFile: File | Blob,
    language: string = 'en',
    age?: number,
    gender?: string,
    medicalHistory?: string
  ): Promise<VoiceDiagnosisResponse> => {
    const formData = new FormData();
    formData.append('audio', audioFile, 'consultation.webm');
    formData.append('language', language || 'en');

    if (age !== undefined && age !== null) {
      formData.append('age', String(age));
    }
    if (gender && gender.trim() !== '') {
      formData.append('gender', gender);
    }
    if (medicalHistory && medicalHistory.trim() !== '') {
      formData.append('medical_history', medicalHistory);
    }

    const response = await apiClient.post('/voice/diagnose', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return response.data;
  },

  getHistory: async (sessionId: string): Promise<any> => {
    const response = await apiClient.get(`/voice/history/${sessionId}`);
    return response.data;
  },
};
