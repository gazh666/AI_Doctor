'use client';

import { useEffect, useRef, useState } from 'react';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Badge } from '@/components/ui/badge';
// Added Stethoscope from lucide-react
import { 
  Loader2, 
  Volume2, 
  AlertTriangle, 
  CheckCircle, 
  Stethoscope 
} from 'lucide-react'; 
import { VoiceRecorder } from './VoiceRecorder';
import { voiceAPI, VoiceDiagnosisResponse } from '@/lib/api/voice';
import { cn } from 'lib/utils';

export function VoiceDiagnosis() {
  const [audioBlob, setAudioBlob] = useState<Blob | null>(null);
  const [processing, setProcessing] = useState(false);
  const [result, setResult] = useState<VoiceDiagnosisResponse | null>(null);
  const [playingAudio, setPlayingAudio] = useState(false);
  const [audioLoading, setAudioLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const playbackAudioRef = useRef<HTMLAudioElement | null>(null);
  const playbackWatchdogRef = useRef<number | null>(null);

  const [language, setLanguage] = useState('en');
  const [age, setAge] = useState('');
  const [gender, setGender] = useState('');
  const [medicalHistory, setMedicalHistory] = useState('');

  const handleRecordingComplete = (blob: Blob) => {
    stopAudioPlayback();
    setAudioBlob(blob);
    setError(null);
    setResult(null); // Clear old results when new audio is recorded
  };

  const clearPlaybackWatchdog = () => {
    if (playbackWatchdogRef.current !== null) {
      window.clearTimeout(playbackWatchdogRef.current);
      playbackWatchdogRef.current = null;
    }
  };

  const resetPlaybackState = () => {
    clearPlaybackWatchdog();
    setPlayingAudio(false);
    setAudioLoading(false);
    playbackAudioRef.current = null;
  };

  const stopAudioPlayback = () => {
    clearPlaybackWatchdog();
    const currentAudio = playbackAudioRef.current;
    if (currentAudio) {
      currentAudio.pause();
      currentAudio.currentTime = 0;
      currentAudio.onplay = null;
      currentAudio.onended = null;
      currentAudio.onpause = null;
      currentAudio.onerror = null;
      currentAudio.onabort = null;
      currentAudio.onstalled = null;
      playbackAudioRef.current = null;
    }
    setPlayingAudio(false);
    setAudioLoading(false);
  };

  useEffect(() => {
    return () => {
      stopAudioPlayback();
    };
  }, []);

  const handleSubmit = async () => {
    if (!audioBlob) return;

    if (!age || !gender.trim()) {
      setError('Age and gender are required for voice diagnosis.');
      return;
    }

    try {
      setError(null);
      setProcessing(true);
      
      // Ensure age is passed as a number or undefined, not an empty string
      const ageValue = age ? parseInt(age) : undefined;

      const response = await voiceAPI.voiceDiagnosis(
        audioBlob,
        language,
        ageValue,
        gender || undefined,
        medicalHistory || undefined
      );

      setResult(response);
      
      if (response.audio_response) {
        playAudioResponse(response.audio_response);
      }
      
    } catch (error: any) {
      const detail = error?.response?.data?.detail;
      const message = typeof detail === 'string' ? detail : 'Voice diagnosis failed. Please try again.';
      console.error('Diagnosis failed:', error);
      setError(message);
    } finally {
      setProcessing(false);
    }
  };

  const playAudioResponse = (base64Data?: string) => {
    const data = base64Data || result?.audio_response;
    if (!data) {
      setError('Audio summary is unavailable for this diagnosis.');
      return;
    }

    stopAudioPlayback();
    setAudioLoading(true);
    const audio = new Audio(`data:audio/mpeg;base64,${data}`);
    playbackAudioRef.current = audio;

    const onPlaybackFinished = () => {
      resetPlaybackState();
    };

    audio.onplay = () => {
      setAudioLoading(false);
      setPlayingAudio(true);
    };
    audio.onended = onPlaybackFinished;
    audio.onpause = onPlaybackFinished;
    audio.onerror = () => {
      setError('Unable to play the voice summary. Please try again.');
      onPlaybackFinished();
    };
    audio.onabort = onPlaybackFinished;
    audio.onstalled = onPlaybackFinished;

    // Safety reset if the browser never transitions out of loading/playback.
    playbackWatchdogRef.current = window.setTimeout(() => {
      if (playbackAudioRef.current === audio) {
        onPlaybackFinished();
      }
    }, 45000);

    audio.play().catch((e) => {
      console.error('Playback blocked:', e);
      setError('Playback is blocked by your browser. Tap again to retry.');
      onPlaybackFinished();
    });
  };

  return (
    <div className="max-w-3xl mx-auto space-y-6 pb-20">
      <Card className="p-6 border-slate-100 shadow-sm">
        <div className="flex items-center gap-2 mb-6 text-slate-900">
          <div className="p-2 bg-blue-50 rounded-lg text-blue-600">
             <Stethoscope size={20} />
          </div>
          <h3 className="text-lg font-bold">Patient Context</h3>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div className="space-y-2">
            <Label>Preferred Language</Label>
            <Select value={language} onValueChange={setLanguage}>
              <SelectTrigger className="bg-slate-50">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="en">English (Global)</SelectItem>
                <SelectItem value="hi">Hindi (हिंदी)</SelectItem>
                <SelectItem value="bn">Bengali (বাংলা)</SelectItem>
                <SelectItem value="ta">Tamil (தமிழ்)</SelectItem>
              </SelectContent>
            </Select>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label>Age</Label>
              <Input 
                type="number" 
                value={age} 
                onChange={(e) => setAge(e.target.value)} 
                className="bg-slate-50" 
                placeholder="e.g. 45"
              />
            </div>
            <div className="space-y-2">
              <Label>Gender</Label>
              <Input 
                value={gender} 
                onChange={(e) => setGender(e.target.value)} 
                className="bg-slate-50" 
                placeholder="e.g. Male"
              />
            </div>
          </div>

          <div className="md:col-span-2 space-y-2">
            <Label>Medical History & Allergies</Label>
            <Textarea 
              value={medicalHistory} 
              onChange={(e) => setMedicalHistory(e.target.value)} 
              className="bg-slate-50 resize-none h-24"
              placeholder="e.g. Hypertension, Penicillin allergy..."
            />
          </div>
        </div>
      </Card>

      <VoiceRecorder onRecordingComplete={handleRecordingComplete} disabled={processing} />

      {error && (
        <Card className="p-4 border-red-200 bg-red-50">
          <p className="text-sm text-red-700">{error}</p>
        </Card>
      )}

      {audioBlob && !result && (
        <Button 
            onClick={handleSubmit} 
            disabled={processing} 
            size="lg"
            className="w-full h-16 text-lg font-bold shadow-lg bg-blue-600 hover:bg-blue-700 transition-all"
        >
          {processing ? (
            <><Loader2 className="mr-3 animate-spin" /> The Doctor is Thinking...</>
          ) : (
            <><CheckCircle className="mr-3" /> Analyze Voice Report</>
          )}
        </Button>
      )}

      {result && (
        <div className="space-y-6 animate-in fade-in slide-in-from-bottom-6 duration-700">
          <div className={cn(
              "p-4 rounded-2xl border-2 flex items-center gap-4",
              result.diagnosis_result.urgency === 'EMERGENCY' 
                ? "bg-red-50 border-red-200 text-red-900" 
                : "bg-green-50 border-green-200 text-green-900"
          )}>
            <div className={cn(
                "p-3 rounded-full",
                result.diagnosis_result.urgency === 'EMERGENCY' ? "bg-red-500 text-white" : "bg-green-500 text-white"
            )}>
                {result.diagnosis_result.urgency === 'EMERGENCY' ? <AlertTriangle /> : <CheckCircle />}
            </div>
            <div>
                <p className="text-xs font-black uppercase tracking-widest opacity-70">Triage Status</p>
                <p className="text-lg font-bold">{result.diagnosis_result.urgency} CARE REQUIRED</p>
            </div>
          </div>

          <Card className="p-8 space-y-6 shadow-md border-slate-100">
            <div className="flex justify-between items-start">
                <div className="space-y-1">
                    <h4 className="text-sm font-bold text-slate-400 uppercase">Primary Diagnosis</h4>
                    <p className="text-2xl font-black text-slate-900">{result.diagnosis_result.diagnosis}</p>
                </div>
                <Badge variant="outline" className="text-blue-600 border-blue-100 bg-blue-50">
                    {(result.diagnosis_result.confidence * 100).toFixed(0)}% Match
                </Badge>
            </div>

            <div className="space-y-4 pt-4 border-t border-slate-100">
                <h4 className="font-bold text-slate-900">Treatment & Immediate Steps</h4>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                    {result.diagnosis_result.treatment_summary.map((step, i) => (
                        <div key={i} className="flex gap-3 p-3 bg-slate-50 rounded-xl text-sm text-slate-700">
                            <span className="text-blue-500 font-bold">{i + 1}.</span>
                            {step}
                        </div>
                    ))}
                </div>
            </div>

            <Button 
                variant="secondary" 
                onClick={() => {
                  if (playingAudio || audioLoading) {
                    stopAudioPlayback();
                    return;
                  }
                  playAudioResponse();
                }}
                disabled={!result.audio_response && !playingAudio && !audioLoading}
                className="w-full h-14 rounded-xl font-bold bg-slate-100 hover:bg-slate-200"
            >
                {(playingAudio || audioLoading) ? <Loader2 className="animate-spin mr-2"/> : <Volume2 className="mr-2"/>}
                {(playingAudio || audioLoading) ? 'Stop Audio Summary' : 'Listen to Audio Summary'}
            </Button>
          </Card>
        </div>
      )}
    </div>
  );
}