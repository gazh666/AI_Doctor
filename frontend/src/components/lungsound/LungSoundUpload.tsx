'use client';

import { useState, useRef } from 'react';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import {
  Upload,
  Loader2,
  AlertCircle,
  X,
  Volume2,
  Activity,
} from 'lucide-react';
import { lungSoundAPI, LungSoundResult } from '@/lib/api/lung-sound';
import { LungSoundWaveSpectrum } from './LungSoundWaveSpectrum';

const MAX_FILE_BYTES = 20 * 1024 * 1024;

const PROB_LABELS = ['normal', 'crackle', 'wheeze', 'both'] as const;
const PROB_BAR_COLORS: Record<string, string> = {
  normal: 'bg-green-500',
  crackle: 'bg-orange-500',
  wheeze: 'bg-yellow-500',
  both: 'bg-red-500',
};

interface LungSoundUploadProps {
  onChange?: (path: string | null, result: LungSoundResult | null) => void;
}

export function LungSoundUpload({ onChange }: LungSoundUploadProps) {
  const [file, setFile] = useState<File | null>(null);
  const [audioUrl, setAudioUrl] = useState<string | null>(null);
  const [analyzing, setAnalyzing] = useState(false);
  const [result, setResult] = useState<LungSoundResult | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selected = e.target.files?.[0];
    if (!selected) return;

    if (!selected.name.toLowerCase().endsWith('.wav')) {
      alert('Please select a .wav lung sound audio file');
      return;
    }
    if (selected.size > MAX_FILE_BYTES) {
      alert('File too large (max 20MB)');
      return;
    }

    if (audioUrl) URL.revokeObjectURL(audioUrl);
    setFile(selected);
    setAudioUrl(URL.createObjectURL(selected));
    setResult(null);
    onChange?.(null, null);
  };

  const handleAnalyze = async () => {
    if (!file) return;

    try {
      setAnalyzing(true);
      const response = await lungSoundAPI.analyze(file);
      setResult(response.result);
      onChange?.(response.lung_sound_path, response.result);
    } catch (error: any) {
      console.error('Lung sound analysis error:', error);
      alert(error.response?.data?.detail || 'Lung sound analysis failed. Please try again.');
    } finally {
      setAnalyzing(false);
    }
  };

  const handleClear = () => {
    if (audioUrl) URL.revokeObjectURL(audioUrl);
    setFile(null);
    setAudioUrl(null);
    setResult(null);
    if (fileInputRef.current) fileInputRef.current.value = '';
    onChange?.(null, null);
  };

  const getLabelClass = (label: string) => {
    const colors: Record<string, string> = {
      normal: 'bg-green-100 text-green-800 border-green-300',
      crackle: 'bg-orange-100 text-orange-800 border-orange-300',
      wheeze: 'bg-yellow-100 text-yellow-800 border-yellow-300',
      both: 'bg-red-100 text-red-800 border-red-300',
    };
    return colors[label] || 'bg-gray-100 text-gray-800 border-gray-300';
  };

  return (
    <Card className="p-6">
      <h3 className="text-lg font-semibold mb-1 flex items-center gap-2">
        <Volume2 className="w-5 h-5" />
        Lung Sound Auscultation (Optional)
      </h3>
      <p className="text-xs text-gray-500 mb-4">
        Upload a .wav lung sound recording for AI-assisted auscultation.
      </p>

      {!file ? (
        <div className="border-2 border-dashed border-gray-300 rounded-lg p-8 text-center hover:border-blue-400 transition-colors">
          <input
            ref={fileInputRef}
            type="file"
            accept=".wav,audio/wav,audio/x-wav"
            onChange={handleFileChange}
            className="hidden"
            id="lung-sound-upload"
          />
          <label htmlFor="lung-sound-upload" className="cursor-pointer flex flex-col items-center gap-3">
            <Upload className="w-16 h-16 text-gray-400" />
            <div>
              <p className="text-sm font-medium text-gray-700">Click to upload lung sound audio</p>
              <p className="text-xs text-gray-500 mt-1">WAV (max 20MB)</p>
            </div>
          </label>
        </div>
      ) : (
        <div className="space-y-4">
          <div className="flex items-center gap-3">
            <Volume2 className="w-6 h-6 text-blue-600 shrink-0" />
            <span className="text-sm font-medium flex-1 truncate">{file.name}</span>
            <Button variant="outline" size="sm" onClick={handleClear} disabled={analyzing}>
              <X className="w-4 h-4 mr-1" />
              Clear
            </Button>
          </div>

          <audio controls src={audioUrl || undefined} className="w-full" />

          <LungSoundWaveSpectrum audioUrl={audioUrl} />

          <Button onClick={handleAnalyze} disabled={analyzing} className="w-full">
            {analyzing ? (
              <>
                <Loader2 className="w-5 h-5 mr-2 animate-spin" />
                Analyzing Lung Sound...
              </>
            ) : (
              <>
                <Activity className="w-5 h-5 mr-2" />
                Analyze Lung Sound
              </>
            )}
          </Button>
        </div>
      )}

      {result && (
        <div className="mt-4 p-4 rounded-lg border space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-sm font-medium">Analysis Result</span>
            <Badge className={getLabelClass(result.label)}>{result.label}</Badge>
          </div>

          {result.probabilities && (
            <div className="space-y-1.5">
              {PROB_LABELS.map((label) => {
                const prob = result.probabilities?.[label] ?? 0;
                return (
                  <div key={label} className="flex items-center gap-2">
                    <span className="w-16 text-xs text-gray-600 capitalize">{label}</span>
                    <div className="flex-1 h-2.5 bg-gray-100 rounded-full overflow-hidden">
                      <div
                        className={`h-full rounded-full ${PROB_BAR_COLORS[label]}`}
                        style={{ width: `${(prob * 100).toFixed(1)}%` }}
                      />
                    </div>
                    <span className="w-12 text-right text-xs font-mono text-gray-700">
                      {(prob * 100).toFixed(1)}%
                    </span>
                  </div>
                );
              })}
            </div>
          )}

          <p className="text-sm text-gray-700">
            Confidence: {(result.confidence * 100).toFixed(1)}%
          </p>
          {result.snr_db !== null && result.snr_db !== undefined && (
            <p className="text-sm text-gray-700">SNR: {result.snr_db.toFixed(1)} dB</p>
          )}
          {result.low_quality && (
            <div className="flex items-center gap-2 text-sm text-amber-700">
              <AlertCircle className="w-4 h-4 shrink-0" />
              Recording quality is too low. Please re-record.
            </div>
          )}
          {!result.low_quality && result.confidence < 0.7 && (
            <div className="flex items-center gap-2 text-sm text-amber-700">
              <AlertCircle className="w-4 h-4 shrink-0" />
              Low auscultation confidence - clinical review advised.
            </div>
          )}
          <p className="text-xs text-gray-400">
            For reference only; does not replace a doctor&apos;s diagnosis.
          </p>
        </div>
      )}
    </Card>
  );
}