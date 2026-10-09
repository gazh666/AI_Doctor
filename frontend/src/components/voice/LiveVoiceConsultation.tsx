'use client';

import { useMemo, useState } from 'react';
import { Mic, PhoneOff, Radio, Loader2 } from 'lucide-react';
import { useLiveVoiceConsultation } from '@/hooks/useLiveVoiceConsultation';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';

export function LiveVoiceConsultation() {
  const [language, setLanguage] = useState('en');
  const [age, setAge] = useState('');
  const [gender, setGender] = useState('');
  const [medicalHistory, setMedicalHistory] = useState('');

  const {
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
  } = useLiveVoiceConsultation();

  const connectionLabel = useMemo(() => {
    if (connectionState === 'connecting') return 'Connecting...';
    if (connectionState === 'connected') return 'Connected';
    if (connectionState === 'error') return 'Connection Error';
    return 'Disconnected';
  }, [connectionState]);

  const saveSessionContext = () => {
    configureSession({
      sessionId: sessionId ?? undefined,
      language,
      age: age ? Number(age) : undefined,
      gender: gender || undefined,
      medicalHistory: medicalHistory || undefined,
    });
  };

  return (
    <div className="space-y-6">
      <Card className="p-6 border-slate-100 shadow-sm">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-bold text-slate-900">Live Voice Consultancy</h3>
          <span className="text-xs font-semibold uppercase tracking-wide text-slate-500">{connectionLabel}</span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-5">
          <div className="space-y-2">
            <Label>Language</Label>
            <Select value={language} onValueChange={setLanguage}>
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="en">English</SelectItem>
                <SelectItem value="hi">Hindi</SelectItem>
                <SelectItem value="bn">Bengali</SelectItem>
                <SelectItem value="ta">Tamil</SelectItem>
              </SelectContent>
            </Select>
          </div>

          <div className="space-y-2">
            <Label>Age</Label>
            <Input type="number" value={age} onChange={(e) => setAge(e.target.value)} placeholder="e.g. 42" />
          </div>

          <div className="space-y-2">
            <Label>Gender</Label>
            <Input value={gender} onChange={(e) => setGender(e.target.value)} placeholder="e.g. Female" />
          </div>

          <div className="space-y-2">
            <Label>Medical History</Label>
            <Input
              value={medicalHistory}
              onChange={(e) => setMedicalHistory(e.target.value)}
              placeholder="e.g. Diabetes, hypertension"
            />
          </div>
        </div>

        <div className="flex flex-wrap gap-3">
          <Button
            onClick={() => {
              void connect();
            }}
            disabled={connectionState === 'connecting' || connectionState === 'connected'}
          >
            <Radio className="mr-2 h-4 w-4" />
            Connect Live
          </Button>
          <Button
            variant="outline"
            onClick={saveSessionContext}
            disabled={connectionState !== 'connected'}
          >
            Save Context
          </Button>
          <Button variant="destructive" onClick={disconnect} disabled={connectionState === 'disconnected'}>
            <PhoneOff className="mr-2 h-4 w-4" />
            End Session
          </Button>
        </div>
      </Card>

      <Card className="p-6 border-slate-100 shadow-sm">
        <div className="flex items-center justify-between mb-4">
          <h4 className="font-semibold text-slate-900">Push To Talk</h4>
          {isProcessing && (
            <span className="text-sm text-slate-500 flex items-center">
              <Loader2 className="h-4 w-4 animate-spin mr-2" />
              Doctor is responding...
            </span>
          )}
        </div>

        <Button
          size="lg"
          className={`w-full h-14 ${isRecording ? 'bg-red-600 hover:bg-red-700' : 'bg-blue-600 hover:bg-blue-700'}`}
          disabled={connectionState !== 'connected'}
          onMouseDown={() => {
            void startPushToTalk();
          }}
          onMouseUp={stopPushToTalk}
          onMouseLeave={() => {
            if (isRecording) stopPushToTalk();
          }}
          onTouchStart={() => {
            void startPushToTalk();
          }}
          onTouchEnd={stopPushToTalk}
        >
          <Mic className="mr-2 h-5 w-5" />
          {isRecording ? 'Release To Send' : 'Hold To Talk'}
        </Button>

        {error && <p className="text-sm text-red-600 mt-4">{error}</p>}
      </Card>

      <Card className="p-6 border-slate-100 shadow-sm">
        <h4 className="font-semibold text-slate-900 mb-4">Conversation</h4>
        <div className="space-y-3 max-h-80 overflow-y-auto pr-1">
          {messages.length === 0 && (
            <p className="text-sm text-slate-500">Start live consultation and hold the mic button to speak.</p>
          )}
          {messages.map((message, idx) => (
            <div
              key={`${message.turnId || 'system'}-${idx}`}
              className={`rounded-xl px-4 py-3 text-sm ${
                message.role === 'assistant'
                  ? 'bg-blue-50 text-blue-900 border border-blue-100'
                  : 'bg-slate-50 text-slate-800 border border-slate-100'
              }`}
            >
              <p className="font-semibold text-xs uppercase tracking-wide mb-1">
                {message.role === 'assistant' ? 'AI Doctor' : 'Patient'}
              </p>
              <p>{message.content}</p>
              {message.urgency && (
                <p className="mt-2 text-[11px] uppercase tracking-wide opacity-80">Urgency: {message.urgency}</p>
              )}
            </div>
          ))}
        </div>
      </Card>
    </div>
  );
}
