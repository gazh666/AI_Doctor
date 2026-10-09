"use client";

import React, { useEffect, useRef, useState } from 'react';
import WaveSurfer from 'wavesurfer.js';
import RecordPlugin from 'wavesurfer.js/dist/plugins/record.esm.js';
import { Mic, Square, Loader2 } from 'lucide-react';
import { getApiBaseUrl } from '@/lib/api/base-url';

// Define the response shape based on your voice schema
interface VoiceDiagnosisResponse {
  transcription: string;
  diagnosis_result: {
    diagnosis: string;
    urgency: string;
    full_report: string;
  };
  audio_response?: string;
}

export function VoiceDiagnosis() {
  const waveformRef = useRef<HTMLDivElement>(null);
  const wavesurfer = useRef<WaveSurfer | null>(null);
  const recordPlugin = useRef<any>(null);
  const mediaRecorder = useRef<MediaRecorder | null>(null);
  const audioChunks = useRef<Blob[]>([]);
  
  const [isRecording, setIsRecording] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);

  useEffect(() => {
    if (waveformRef.current) {
      // 1. Initialize Wavesurfer instance
      wavesurfer.current = WaveSurfer.create({
        container: waveformRef.current,
        waveColor: '#3b82f6', // Professional blue for rural clinic UI
        progressColor: '#1d4ed8',
        height: 80,
        barWidth: 2,
        barGap: 3,
        barRadius: 30,
      });

      // 2. Register the Record Plugin for live mic visualization
      recordPlugin.current = wavesurfer.current.registerPlugin(RecordPlugin.create());
    }
    return () => wavesurfer.current?.destroy();
  }, []);

  const startConsultation = async () => {
    try {
      setIsRecording(true);
      audioChunks.current = [];
      
      // Start visual waveform
      recordPlugin.current.startMic();

      // Start actual data recording for the backend
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      mediaRecorder.current = new MediaRecorder(stream);
      
      mediaRecorder.current.ondataavailable = (e) => audioChunks.current.push(e.data);
      mediaRecorder.current.onstop = async () => {
        const audioBlob = new Blob(audioChunks.current, { type: 'audio/wav' });
        await sendToBackend(audioBlob);
      };
      mediaRecorder.current.start();
    } catch (err) {
      console.error("Mic access denied", err);
      setIsRecording(false);
    }
  };

  const stopConsultation = () => {
    setIsRecording(false);
    recordPlugin.current.stopMic(); // Stop visualizer
    mediaRecorder.current?.stop(); // Trigger onstop to send data
  };

  const sendToBackend = async (blob: Blob) => {
    setIsProcessing(true);
    const formData = new FormData();
    // Maps to Endpoint 3: /api/v1/voice/diagnose
    formData.append('audio_file', blob, 'consultation.wav');

    try {
      const API_BASE_URL = getApiBaseUrl();
      const response = await fetch(`${API_BASE_URL}/voice/diagnose`, {
        method: 'POST',
        body: formData,
      });
      const data: VoiceDiagnosisResponse = await response.json();
      
      // Play the AI voice summary (gTTS) returned as base64
      if (data.audio_response) {
        new Audio(`data:audio/mpeg;base64,${data.audio_response}`).play();
      }
    } catch (error) {
      console.error("API Error", error);
    } finally {
      setIsProcessing(false);
    }
  };

  return (
    <div className="bg-white p-8 rounded-3xl border border-slate-200 shadow-xl">
      {/* Waveform Target */}
      <div ref={waveformRef} className="mb-8 bg-slate-50 rounded-2xl overflow-hidden" />
      
      <div className="flex flex-col items-center gap-6">
        {!isRecording ? (
          <button 
            onClick={startConsultation}
            disabled={isProcessing}
            className="flex items-center gap-3 bg-blue-600 hover:bg-blue-700 text-white px-8 py-4 rounded-2xl font-bold transition-all disabled:opacity-50"
          >
            {isProcessing ? <Loader2 className="animate-spin" /> : <Mic />}
            {isProcessing ? "Processing..." : "Start Consultation"}
          </button>
        ) : (
          <button 
            onClick={stopConsultation}
            className="flex items-center gap-3 bg-red-600 hover:bg-red-700 text-white px-8 py-4 rounded-2xl font-bold animate-pulse"
          >
            <Square /> Stop & Diagnose
          </button>
        )}
      </div>
    </div>
  );
}