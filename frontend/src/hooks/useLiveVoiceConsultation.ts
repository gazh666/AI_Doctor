'use client';

import { useCallback, useEffect, useRef, useState } from 'react';
import {
  LiveSessionConfig,
  LiveVoiceConsultationClient,
  LiveVoiceServerEvent,
} from '@/lib/api/voice';

export interface LiveVoiceMessage {
  role: 'user' | 'assistant' | 'system';
  content: string;
  turnId?: string;
  urgency?: string;
  timestamp: string;
}

type ConnectionState = 'disconnected' | 'connecting' | 'connected' | 'error';

function getSupportedMimeType(): string {
  const candidates = [
    'audio/webm;codecs=opus',
    'audio/webm',
    'audio/mp4',
    'audio/ogg;codecs=opus',
  ];
  for (const candidate of candidates) {
    if (MediaRecorder.isTypeSupported(candidate)) return candidate;
  }
  return '';
}

export function useLiveVoiceConsultation() {
  const clientRef = useRef<LiveVoiceConsultationClient | null>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const mediaStreamRef = useRef<MediaStream | null>(null);
  const activeTurnIdRef = useRef<string | null>(null);
  const manualDisconnectRef = useRef(false);
  const reconnectTimerRef = useRef<number | null>(null);
  const reconnectAttemptsRef = useRef(0);
  const [connectionState, setConnectionState] = useState<ConnectionState>('disconnected');
  const [isRecording, setIsRecording] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [messages, setMessages] = useState<LiveVoiceMessage[]>([]);
  const [error, setError] = useState<string | null>(null);

  const onServerEvent = useCallback((event: LiveVoiceServerEvent) => {
    if (event.type === 'auth.ok') {
      if (event.session_id) setSessionId(event.session_id);
      setConnectionState('connected');
      setError(null);
      return;
    }

    if (event.type === 'turn.transcript') {
      setMessages((prev) => [
        ...prev,
        {
          role: 'user',
          content: event.transcript ?? '',
          turnId: event.turn_id,
          timestamp: event.timestamp ?? new Date().toISOString(),
        },
      ]);
      return;
    }

    if (event.type === 'turn.response') {
      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          content: event.response_text ?? '',
          turnId: event.turn_id,
          urgency: event.urgency,
          timestamp: event.timestamp ?? new Date().toISOString(),
        },
      ]);
      setIsProcessing(false);
      return;
    }

    if (event.type === 'turn.audio' && event.audio) {
      const audio = new Audio(`data:${event.mime_type || 'audio/mpeg'};base64,${event.audio}`);
      void audio.play().catch(() => null);
      return;
    }

    if (event.type === 'turn.error') {
      setError(event.message ?? 'Live voice consultation error.');
      setIsProcessing(false);
      setIsRecording(false);
    }
  }, []);

  const connect = useCallback(async () => {
    const token = localStorage.getItem('access_token');
    if (!token) {
      setConnectionState('error');
      setError('Please login before starting live consultation.');
      return;
    }

    if (clientRef.current) {
      clientRef.current.disconnect();
    }
    manualDisconnectRef.current = false;

    setConnectionState('connecting');
    const client = new LiveVoiceConsultationClient();
    clientRef.current = client;

    try {
      await client.connect(
        token,
        onServerEvent,
        () => {
          setConnectionState((prev) => (prev === 'error' ? prev : 'disconnected'));
          if (manualDisconnectRef.current || reconnectAttemptsRef.current >= 2) return;
          reconnectAttemptsRef.current += 1;
          reconnectTimerRef.current = window.setTimeout(() => {
            void connect();
          }, 1500);
        }
      );
      reconnectAttemptsRef.current = 0;
    } catch (err) {
      setConnectionState('error');
      setError(err instanceof Error ? err.message : 'Failed to connect live consultation.');
    }
  }, [onServerEvent]);

  const configureSession = useCallback((config: LiveSessionConfig) => {
    if (!clientRef.current) return;
    clientRef.current.configureSession({
      ...config,
      sessionId: config.sessionId ?? sessionId ?? undefined,
    });
  }, [sessionId]);

  const startPushToTalk = useCallback(async () => {
    if (!clientRef.current || connectionState !== 'connected' || isRecording) return;
    setError(null);
    setIsProcessing(false);

    const turnId = crypto.randomUUID();
    activeTurnIdRef.current = turnId;
    clientRef.current.startTurn(turnId);

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      mediaStreamRef.current = stream;

      const mimeType = getSupportedMimeType();
      const recorder = mimeType ? new MediaRecorder(stream, { mimeType }) : new MediaRecorder(stream);
      mediaRecorderRef.current = recorder;

      recorder.ondataavailable = (event) => {
        if (!event.data || event.data.size === 0 || !clientRef.current) return;
        void clientRef.current.sendAudioChunk(event.data, recorder.mimeType);
      };

      recorder.onstop = () => {
        setIsRecording(false);
        setIsProcessing(true);
        const turn = activeTurnIdRef.current;
        if (turn && clientRef.current) {
          clientRef.current.endTurn(turn);
        }
        activeTurnIdRef.current = null;
        stream.getTracks().forEach((track) => track.stop());
      };

      recorder.start(250);
      setIsRecording(true);
    } catch (err) {
      setIsRecording(false);
      activeTurnIdRef.current = null;
      setError(err instanceof Error ? err.message : 'Unable to start microphone recording.');
    }
  }, [connectionState, isRecording]);

  const stopPushToTalk = useCallback(() => {
    const recorder = mediaRecorderRef.current;
    if (recorder && recorder.state !== 'inactive') {
      recorder.stop();
    }
  }, []);

  const disconnect = useCallback(() => {
    manualDisconnectRef.current = true;
    if (reconnectTimerRef.current !== null) {
      window.clearTimeout(reconnectTimerRef.current);
      reconnectTimerRef.current = null;
    }
    stopPushToTalk();
    if (mediaStreamRef.current) {
      mediaStreamRef.current.getTracks().forEach((track) => track.stop());
      mediaStreamRef.current = null;
    }
    clientRef.current?.disconnect();
    clientRef.current = null;
    setConnectionState('disconnected');
    setIsRecording(false);
    setIsProcessing(false);
  }, [stopPushToTalk]);

  useEffect(() => {
    return () => {
      manualDisconnectRef.current = true;
      if (reconnectTimerRef.current !== null) {
        window.clearTimeout(reconnectTimerRef.current);
      }
      disconnect();
    };
  }, [disconnect]);

  return {
    connectionState,
    isRecording,
    isProcessing,
    sessionId,
    messages,
    error,
    connect,
    disconnect,
    configureSession,
    startPushToTalk,
    stopPushToTalk,
    clearMessages: () => setMessages([]),
  };
}
