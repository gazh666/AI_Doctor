'use client';

import { useState, useRef, useCallback, useEffect } from 'react';

interface UseVoiceRecorderOptions {
  onRecordingComplete?: (audioBlob: Blob) => void;
  maxDuration?: number; // in seconds (default 10 mins)
}

export function useVoiceRecorder({ 
  onRecordingComplete, 
  maxDuration = 600 
}: UseVoiceRecorderOptions = {}) {
  
  const [isRecording, setIsRecording] = useState(false);
  const [isPaused, setIsPaused] = useState(false);
  const [duration, setDuration] = useState(0);
  const [audioBlob, setAudioBlob] = useState<Blob | null>(null);

  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const timerRef = useRef<NodeJS.Timeout | null>(null);
  const streamRef = useRef<MediaStream | null>(null);

  /**
   * Helper: Determine the best supported mimeType for the current browser.
   * Standard webm works for Chrome/Firefox, while mp4/wav is safer for Safari.
   */
  const getSupportedMimeType = () => {
    const types = [
      'audio/webm;codecs=opus',
      'audio/webm',
      'audio/mp4',
      'audio/ogg;codecs=opus',
      'audio/ogg',
    ];
    for (const type of types) {
      if (MediaRecorder.isTypeSupported(type)) return type;
    }
    return '';
  };

  const startRecording = useCallback(async () => {
    try {
      // 1. Request Microphone Access
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      streamRef.current = stream;

      // 2. Setup MediaRecorder
      const mimeType = getSupportedMimeType();
      const mediaRecorder = mimeType
        ? new MediaRecorder(stream, { mimeType })
        : new MediaRecorder(stream);
      
      mediaRecorderRef.current = mediaRecorder;
      chunksRef.current = [];

      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          chunksRef.current.push(event.data);
        }
      };

      mediaRecorder.onstop = () => {
        if (chunksRef.current.length === 0) {
          console.error('No audio chunks captured from recorder.');
          alert('Recording failed. Please try again and allow microphone access.');
          return;
        }

        const blobType = mediaRecorder.mimeType || mimeType || 'audio/webm';
        const finalBlob = new Blob(chunksRef.current, { type: blobType });
        setAudioBlob(finalBlob);
        
        if (onRecordingComplete) {
          onRecordingComplete(finalBlob);
        }

        // 3. Clean up tracks (removes the "Mic in use" browser indicator)
        stream.getTracks().forEach((track) => track.stop());
      };

      // 4. Start the engine
      mediaRecorder.start(100); // Collect data every 100ms
      setIsRecording(true);
      setIsPaused(false);
      setDuration(0);

      // 5. Manage Timer
      timerRef.current = setInterval(() => {
        setDuration((prev) => {
          if (prev + 1 >= maxDuration) {
            stopRecording();
            return maxDuration;
          }
          return prev + 1;
        });
      }, 1000);

    } catch (error) {
      console.error('Microphone access failed:', error);
      alert('Could not access microphone. Please check your browser permissions.');
    }
  }, [maxDuration, onRecordingComplete]);

  const stopRecording = useCallback(() => {
    if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
      mediaRecorderRef.current.stop();
      setIsRecording(false);
      setIsPaused(false);

      if (timerRef.current) {
        clearInterval(timerRef.current);
        timerRef.current = null;
      }
    }
  }, []);

  const pauseRecording = useCallback(() => {
    if (mediaRecorderRef.current?.state === 'recording') {
      mediaRecorderRef.current.pause();
      setIsPaused(true);
      if (timerRef.current) {
        clearInterval(timerRef.current);
      }
    }
  }, []);

  const resumeRecording = useCallback(() => {
    if (mediaRecorderRef.current?.state === 'paused') {
      mediaRecorderRef.current.resume();
      setIsPaused(false);
      
      timerRef.current = setInterval(() => {
        setDuration((prev) => (prev >= maxDuration ? prev : prev + 1));
      }, 1000);
    }
  }, [maxDuration]);

  const clearRecording = useCallback(() => {
    setAudioBlob(null);
    setDuration(0);
    chunksRef.current = [];
  }, []);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
      if (streamRef.current) {
        streamRef.current.getTracks().forEach(track => track.stop());
      }
    };
  }, []);

  return {
    isRecording,
    isPaused,
    duration,
    audioBlob,
    startRecording,
    stopRecording,
    pauseRecording,
    resumeRecording,
    clearRecording,
    stream: streamRef.current // Useful for WaveSurfer visualizer
  };
}