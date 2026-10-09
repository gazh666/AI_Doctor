'use client';

import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Mic, Square, Pause, Play, Trash2, Activity } from 'lucide-react';
import { useVoiceRecorder } from '@/hooks/useVoiceRecorder';
import { useEffect, useRef, useState } from 'react';
import { cn } from 'lib/utils';
import WaveSurfer from 'wavesurfer.js';

interface VoiceRecorderProps {
  onRecordingComplete: (audioBlob: Blob) => void;
  disabled?: boolean;
}

export function VoiceRecorder({ onRecordingComplete, disabled }: VoiceRecorderProps) {
  const {
    isRecording,
    isPaused,
    duration,
    audioBlob,
    startRecording: startHookRecording,
    stopRecording: stopHookRecording,
    pauseRecording: pauseHookRecording,
    resumeRecording: resumeHookRecording,
    clearRecording,
  } = useVoiceRecorder({ onRecordingComplete });

  const [audioUrl, setAudioUrl] = useState<string | null>(null);
  
  // WaveSurfer Refs
  const waveformRef = useRef<HTMLDivElement>(null);
  const wavesurfer = useRef<WaveSurfer | null>(null);

  // Initialize WaveSurfer
  useEffect(() => {
    if (waveformRef.current) {
      wavesurfer.current = WaveSurfer.create({
        container: waveformRef.current,
        waveColor: '#94a3b8',
        progressColor: '#3b82f6',
        height: 60,
        barWidth: 2,
        barGap: 3,
        barRadius: 30,
        cursorWidth: 0,
      });
    }
    return () => wavesurfer.current?.destroy();
  }, []);

  // Sync WaveSurfer with Hook State
  const startRecording = () => {
    startHookRecording();
  };

  const stopRecording = () => {
    stopHookRecording();
  };

  const pauseRecording = () => {
    pauseHookRecording();
  };

  const resumeRecording = () => {
    resumeHookRecording();
  };

  useEffect(() => {
    if (audioBlob) {
      const url = URL.createObjectURL(audioBlob);
      setAudioUrl(url);
      return () => URL.revokeObjectURL(url);
    } else {
      setAudioUrl(null);
    }
  }, [audioBlob]);

  const formatDuration = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  return (
    <Card className="p-6 border-slate-200 shadow-xl overflow-hidden bg-white">
      <div className="space-y-6">
        {!audioBlob ? (
          <div className="flex flex-col items-center gap-6">
            
            {/* Waveform Visualization Area */}
            <div className={cn(
                "w-full h-24 bg-slate-50 rounded-2xl border border-dashed border-slate-200 flex items-center justify-center overflow-hidden transition-all",
                isRecording && "border-blue-200 bg-blue-50/30"
            )}>
                {/* WaveSurfer Target Element */}
                <div ref={waveformRef} className="w-full" />
                
                {!isRecording && (
                    <div className="absolute flex flex-col items-center text-slate-400">
                        <Mic className="w-6 h-6 mb-1" />
                        <span className="text-xs font-medium uppercase tracking-widest">Mic Ready</span>
                    </div>
                )}
            </div>

            {/* Timer Section */}
            <div className="text-center">
              <div className={cn(
                "text-4xl font-mono font-bold transition-colors",
                isRecording ? "text-slate-900" : "text-slate-300"
              )}>
                {formatDuration(duration)}
              </div>
              <p className="text-sm text-slate-500 mt-1 font-medium">
                {isRecording ? (isPaused ? 'Recording Paused' : 'The AI is listening...') : 'Ready to start consultation'}
              </p>
            </div>

            {/* Main Controls */}
            <div className="flex items-center gap-4">
              {!isRecording ? (
                <Button
                  onClick={startRecording}
                  disabled={disabled}
                  size="lg"
                  className="rounded-full px-8 bg-blue-600 hover:bg-blue-700 h-14 shadow-lg shadow-blue-200"
                >
                  <Mic className="mr-2 w-5 h-5" />
                  Start Consultation
                </Button>
              ) : (
                <div className="flex gap-3">
                  <Button
                    onClick={isPaused ? resumeRecording : pauseRecording}
                    variant="outline"
                    size="lg"
                    className="rounded-full h-14 w-14 bg-white border-slate-200"
                  >
                    {isPaused ? <Play className="fill-blue-600 text-blue-600" /> : <Pause className="fill-slate-600 text-slate-600" />}
                  </Button>
                  <Button
                    onClick={stopRecording}
                    variant="destructive"
                    size="lg"
                    className="rounded-full px-8 h-14 shadow-lg shadow-red-200"
                  >
                    <Square className="mr-2 w-5 h-5 fill-current" />
                    Finish
                  </Button>
                </div>
              )}
            </div>
          </div>
        ) : (
          /* Review & Submit Section */
          <div className="space-y-4 animate-in fade-in slide-in-from-bottom-4">
            <div className="bg-slate-50 p-6 rounded-2xl border border-slate-100">
              <div className="flex items-center justify-between mb-4">
                <span className="text-sm font-bold text-slate-700 flex items-center gap-2 uppercase tracking-wide">
                  <Activity size={16} className="text-blue-500" />
                  Review Recording
                </span>
                <Badge variant="secondary" className="font-mono">{formatDuration(duration)}</Badge>
              </div>
              
              <audio src={audioUrl!} controls className="w-full h-10 accent-blue-600" />
            </div>

            <div className="flex gap-3">
              <Button
                onClick={clearRecording}
                variant="outline"
                className="w-full rounded-xl h-12 text-slate-600 border-slate-200 hover:bg-slate-50"
              >
                <Trash2 className="mr-2 w-4 h-4" />
                Discard
              </Button>
            </div>
          </div>
        )}
      </div>
    </Card>
  );
}

// Helper Badge component if you don't have it in your UI folder
function Badge({ children, variant, className }: any) {
    return (
        <span className={cn(
            "px-2.5 py-0.5 rounded-full text-xs font-semibold",
            variant === 'secondary' ? "bg-slate-100 text-slate-900" : "bg-blue-100 text-blue-900",
            className
        )}>
            {children}
        </span>
    );
}