'use client';

import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import { ScrollArea } from '@/components/ui/scroll-area';
import {
  Loader2,
  Stethoscope,
  AlertTriangle,
  CheckCircle,
  FileText,
  Activity,
  PhoneCall,
  ExternalLink
} from 'lucide-react';
import { agentsAPI, DiagnosisResponse } from '@/lib/api/agents';
import { LungSoundUpload } from '@/components/lungsound/LungSoundUpload';
import { LungSoundResult } from '@/lib/api/lung-sound';

function tokenize(text: string): string[] {
  return text
    .toLowerCase()
    .replace(/[^a-z0-9\s]/g, ' ')
    .split(/\s+/)
    .filter((token) => token.length >= 5);
}

function getCitationRanks(text: string, citations: DiagnosisResponse['citations']): number[] {
  if (!citations || citations.length === 0) {
    return [];
  }

  const tokens = new Set(tokenize(text));
  const scored = citations
    .map((citation) => {
      const sourceText = `${citation.title} ${citation.excerpt}`.toLowerCase();
      let score = 0;
      tokens.forEach((token) => {
        if (sourceText.includes(token)) {
          score += 1;
        }
      });
      return { rank: citation.rank, score };
    })
    .filter((item) => item.score > 0)
    .sort((a, b) => b.score - a.score)
    .slice(0, 2)
    .map((item) => item.rank);

  if (scored.length > 0) {
    return scored;
  }

  // Fallback to top source when no lexical overlap is detected.
  return [citations[0].rank];
}

async function getCurrentLocation(): Promise<{ lat: number; lng: number } | undefined> {
  if (typeof window === 'undefined' || !navigator.geolocation) {
    return undefined;
  }
  return new Promise((resolve) => {
    navigator.geolocation.getCurrentPosition(
      (position) => resolve({ lat: position.coords.latitude, lng: position.coords.longitude }),
      () => resolve(undefined),
      { enableHighAccuracy: true, timeout: 5000, maximumAge: 60000 }
    );
  });
}

function buildDirectionsUrl(destinationLat: number, destinationLng: number, origin?: { lat: number; lng: number }) {
  const base = 'https://www.google.com/maps/dir/?api=1';
  if (origin) {
    return `${base}&origin=${origin.lat},${origin.lng}&destination=${destinationLat},${destinationLng}`;
  }
  return `${base}&destination=${destinationLat},${destinationLng}`;
}

export function CompleteDiagnosis() {
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<DiagnosisResponse | null>(null);
  const [showSources, setShowSources] = useState(false);
  const [mode, setMode] = useState<'pipeline' | 'agentic'>('pipeline');
  const hasCitations = Boolean(result?.citations && result.citations.length > 0);

  // Form state
  const [symptoms, setSymptoms] = useState('');
  const [age, setAge] = useState('');
  const [gender, setGender] = useState('');
  const [medicalHistory, setMedicalHistory] = useState('');
  const [temperature, setTemperature] = useState('');
  const [heartRate, setHeartRate] = useState('');
  const [bloodPressure, setBloodPressure] = useState('');
  const [lungSoundPath, setLungSoundPath] = useState<string | null>(null);
  const [lungSoundResult, setLungSoundResult] = useState<LungSoundResult | null>(null);

  const handleDiagnose = async () => {
    if (!symptoms.trim()) {
      alert('Please describe symptoms');
      return;
    }

    try {
      setLoading(true);

      const vitals: Record<string, any> = {};
      if (temperature) vitals.temperature = parseFloat(temperature);
      if (heartRate) vitals.heart_rate = parseInt(heartRate);
      if (bloodPressure) vitals.blood_pressure = bloodPressure;
      const userLocation = await getCurrentLocation();

      const payload = {
        symptoms: symptoms.trim(),
        age: age ? parseInt(age) : undefined,
        gender: gender || undefined,
        medical_history: medicalHistory || undefined,
        vitals: Object.keys(vitals).length > 0 ? vitals : undefined,
        user_location: userLocation,
        lung_sound_path: lungSoundPath || undefined,
        lung_sound_result: lungSoundResult || undefined,
      };

      const response = mode === 'agentic'
        ? await agentsAPI.agenticDiagnose(payload)
        : await agentsAPI.diagnose(payload);

      setResult(response);
      setShowSources(false);
    } catch (error: any) {
      console.error('Diagnosis error:', error);
      alert(error.response?.data?.detail || 'Diagnosis failed');
    } finally {
      setLoading(false);
    }
  };

  const getUrgencyColor = (urgency: string) => {
    const colors: Record<string, string> = {
      EMERGENCY: 'bg-red-100 text-red-800 border-red-300',
      URGENT: 'bg-orange-100 text-orange-800 border-orange-300',
      ROUTINE: 'bg-green-100 text-green-800 border-green-300',
    };
    return colors[urgency] || 'bg-gray-100 text-gray-800 border-gray-300';
  };

  const getProviderBadgeClass = (provider?: string) => {
    const key = (provider || '').toLowerCase();
    if (key === 'pubmed') return 'bg-blue-100 text-blue-800 border-blue-300';
    if (key === 'openfda') return 'bg-emerald-100 text-emerald-800 border-emerald-300';
    if (key === 'medlineplus') return 'bg-indigo-100 text-indigo-800 border-indigo-300';
    if (key === 'clinicaltrials') return 'bg-purple-100 text-purple-800 border-purple-300';
    if (key === 'localrag') return 'bg-amber-100 text-amber-800 border-amber-300';
    return 'bg-gray-100 text-gray-800 border-gray-300';
  };

  const renderCitationAnchors = (text: string) => {
    if (!result?.citations || result.citations.length === 0) {
      return null;
    }
    const ranks = getCitationRanks(text, result.citations);
    if (ranks.length === 0) {
      return null;
    }
    return (
      <span className="ml-1 text-[11px] font-semibold text-blue-700">
        {ranks.map((rank) => (
          <span key={rank} className="mr-1">[{rank}]</span>
        ))}
      </span>
    );
  };

  const emergencyInfo = result?.status === 'CRITICAL' ? result.emergency_info : undefined;
  const nearestFacility = emergencyInfo?.nearby_facilities?.[0];
  const mapDirections = nearestFacility
    ? buildDirectionsUrl(
      nearestFacility.coordinates.lat,
      nearestFacility.coordinates.lng,
      emergencyInfo?.user_location
    )
    : null;

  return (
    <div className="space-y-6">
      {/* Input Form */}
      <Card className="p-6">
        <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
          <Stethoscope className="w-5 h-5" />
          Complete Medical Assessment
        </h3>

        <div className="space-y-4">
          {/* Symptoms */}
          <div>
            <Label htmlFor="symptoms">Symptoms *</Label>
            <Textarea
              id="symptoms"
              placeholder="Describe all symptoms in detail..."
              value={symptoms}
              onChange={(e) => setSymptoms(e.target.value)}
              rows={4}
              disabled={loading}
            />
          </div>

          {/* Patient Info */}
          <div className="grid grid-cols-2 gap-4">
            <div>
              <Label htmlFor="age">Age</Label>
              <Input
                id="age"
                type="number"
                placeholder="e.g., 35"
                value={age}
                onChange={(e) => setAge(e.target.value)}
                disabled={loading}
              />
            </div>
            <div>
              <Label htmlFor="gender">Gender</Label>
              <Input
                id="gender"
                placeholder="e.g., Male/Female"
                value={gender}
                onChange={(e) => setGender(e.target.value)}
                disabled={loading}
              />
            </div>
          </div>

          {/* Vitals */}
          <div className="grid grid-cols-3 gap-4">
            <div>
              <Label htmlFor="temp">Temperature (°F)</Label>
              <Input
                id="temp"
                type="number"
                step="0.1"
                placeholder="98.6"
                value={temperature}
                onChange={(e) => setTemperature(e.target.value)}
                disabled={loading}
              />
            </div>
            <div>
              <Label htmlFor="hr">Heart Rate (bpm)</Label>
              <Input
                id="hr"
                type="number"
                placeholder="72"
                value={heartRate}
                onChange={(e) => setHeartRate(e.target.value)}
                disabled={loading}
              />
            </div>
            <div>
              <Label htmlFor="bp">Blood Pressure</Label>
              <Input
                id="bp"
                placeholder="120/80"
                value={bloodPressure}
                onChange={(e) => setBloodPressure(e.target.value)}
                disabled={loading}
              />
            </div>
          </div>

          {/* Medical History */}
          <div>
            <Label htmlFor="history">Medical History</Label>
            <Textarea
              id="history"
              placeholder="Previous conditions, medications, allergies..."
              value={medicalHistory}
              onChange={(e) => setMedicalHistory(e.target.value)}
              rows={2}
              disabled={loading}
            />
          </div>

          {/* Lung Sound Auscultation */}
          <LungSoundUpload
            onChange={(path, soundResult) => {
              setLungSoundPath(path);
              setLungSoundResult(soundResult);
            }}
          />

          {/* Agent Mode Toggle */}
          <div className="rounded-lg border p-3 bg-gray-50">
            <p className="text-sm font-medium mb-2">Diagnosis Mode</p>
            <div className="grid grid-cols-2 gap-2">
              <Button
                type="button"
                variant={mode === 'pipeline' ? 'default' : 'outline'}
                onClick={() => setMode('pipeline')}
                disabled={loading}
              >
                Pipeline (Fixed Graph)
              </Button>
              <Button
                type="button"
                variant={mode === 'agentic' ? 'default' : 'outline'}
                onClick={() => setMode('agentic')}
                disabled={loading}
              >
                Autonomous Agent
              </Button>
            </div>
            <p className="text-xs text-gray-500 mt-2">
              {mode === 'agentic'
                ? 'Tool harness + ReAct loop: the model decides which tools to call.'
                : 'Deterministic multi-node LangGraph pipeline.'}
            </p>
          </div>

          {/* Submit Button */}
          <Button
            onClick={handleDiagnose}
            disabled={loading || !symptoms.trim()}
            className="w-full"
            size="lg"
          >
            {loading ? (
              <>
                <Loader2 className="w-5 h-5 mr-2 animate-spin" />
                {mode === 'agentic'
                  ? 'Running Autonomous Agent...'
                  : 'Running Multi-Agent Analysis...'}
              </>
            ) : (
              <>
                <Activity className="w-5 h-5 mr-2" />
                {mode === 'agentic' ? 'Run Autonomous Diagnosis' : 'Run Complete Diagnosis'}
              </>
            )}
          </Button>
        </div>
      </Card>

      {/* Workflow Steps */}
      {loading && (
        <Card className="p-4">
          <h4 className="font-semibold mb-3">Agent Workflow Progress</h4>
          <div className="space-y-2">
            <div className="flex items-center gap-2 text-sm">
              <Loader2 className="w-4 h-4 animate-spin text-blue-600" />
              <span>Running multi-agent analysis...</span>
            </div>
          </div>
        </Card>
      )}

      {/* Results */}
      {result && (
        <div className="space-y-4">
          {emergencyInfo && (
            <Card className="p-4 border-2 border-red-500 bg-red-50 space-y-3">
              <div className="flex items-start gap-2 text-red-900">
                <AlertTriangle className="w-6 h-6 mt-0.5" />
                <div>
                  <h4 className="font-semibold">CRITICAL Emergency Escalation Active</h4>
                  {emergencyInfo.red_flags && emergencyInfo.red_flags.length > 0 && (
                    <p className="text-sm mt-1">
                      Red Flags: {emergencyInfo.red_flags.join(', ')}
                    </p>
                  )}
                </div>
              </div>

              {nearestFacility && (
                <div className="rounded-lg border border-red-200 bg-white p-3">
                  <p className="text-sm font-semibold text-red-900">{nearestFacility.name}</p>
                  <p className="text-sm text-gray-700">
                    Distance: {nearestFacility.distance_km} km | Contact: {nearestFacility.contact_number}
                  </p>
                  <div className="mt-3 flex gap-2 flex-wrap">
                    <Button asChild className="bg-red-600 hover:bg-red-700">
                      <a href={`tel:${nearestFacility.contact_number.replace(/\s+/g, '')}`}>
                        <PhoneCall className="w-4 h-4 mr-2" />
                        Call Now
                      </a>
                    </Button>
                    {mapDirections && (
                      <Button asChild variant="outline">
                        <a href={mapDirections} target="_blank" rel="noreferrer">
                          <ExternalLink className="w-4 h-4 mr-2" />
                          Open Maps
                        </a>
                      </Button>
                    )}
                  </div>
                </div>
              )}

              {mapDirections && (
                <div className="rounded-lg overflow-hidden border border-red-200 bg-white">
                  <iframe
                    title="Emergency route map"
                    src={mapDirections}
                    className="w-full h-64"
                    loading="lazy"
                    referrerPolicy="no-referrer-when-downgrade"
                  />
                </div>
              )}

              {emergencyInfo.first_aid_instructions && emergencyInfo.first_aid_instructions.length > 0 && (
                <div className="rounded-lg border border-red-200 bg-white p-3">
                  <p className="text-sm font-semibold text-red-900">First Aid Instructions</p>
                  <ul className="mt-1 text-sm text-gray-800 list-disc list-inside">
                    {emergencyInfo.first_aid_instructions.map((item, idx) => (
                      <li key={`${item}-${idx}`}>{item}</li>
                    ))}
                  </ul>
                </div>
              )}
            </Card>
          )}

          {/* Urgency Alert */}
          <Card className={`p-4 border-2 ${getUrgencyColor(result.urgency_level)}`}>
            <div className="flex items-center gap-3">
              {result.urgency_level === 'EMERGENCY' && (
                <AlertTriangle className="w-6 h-6" />
              )}
              {result.urgency_level === 'ROUTINE' && (
                <CheckCircle className="w-6 h-6" />
              )}
              <div>
                <h4 className="font-semibold">
                  Urgency Level: {result.urgency_level}
                </h4>
                {result.urgency_level === 'EMERGENCY' && (
                  <p className="text-sm mt-1">
                    ⚠️ Seek immediate medical attention
                  </p>
                )}
              </div>
            </div>
          </Card>

          {/* Diagnosis */}
          <Card className="p-6">
            <div className="flex items-start justify-between mb-4">
              <h3 className="text-lg font-semibold">Diagnosis</h3>
              <Badge variant="secondary">
                {(result.confidence * 100).toFixed(0)}% Confidence
              </Badge>
            </div>

            <div className="space-y-4">
              <div>
                <h4 className="font-medium mb-2">Primary Diagnosis</h4>
                <p className="text-lg text-gray-900">{result.diagnosis}</p>
              </div>

              {result.differential_diagnoses.length > 0 && (
                <div>
                  <h4 className="font-medium mb-2">Differential Diagnoses</h4>
                  <ul className="space-y-1">
                    {result.differential_diagnoses.map((dx, idx) => (
                      <li key={idx} className="text-sm text-gray-700">
                        • {dx}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          </Card>

          {/* Treatment Plan */}
          {result.treatment_plan && (
            <Card className="p-6">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-lg font-semibold">Treatment Plan</h3>
                <Button variant="outline" size="sm" onClick={() => setShowSources(!showSources)}>
                  {showSources ? 'Hide Sources' : 'View Source'}
                </Button>
              </div>

              {showSources && (
                <div className="mb-4 p-4 border rounded-lg bg-amber-50/50 space-y-3">
                  <p className="text-sm font-medium text-amber-800">Grounded Medical Sources</p>
                  {hasCitations ? (
                    result.citations.map((citation) => (
                      <div key={citation.id} className="p-3 bg-white rounded border">
                        <div className="flex items-center gap-2">
                          <p className="text-sm font-semibold">
                            [{citation.rank}] {citation.title}
                          </p>
                          {citation.provider && (
                            <Badge variant="outline" className={getProviderBadgeClass(citation.provider)}>
                              {citation.provider}
                            </Badge>
                          )}
                        </div>
                        {citation.source && (
                          <p className="text-xs text-gray-500 mt-1">
                            Source:{' '}
                            {citation.source.startsWith('http') ? (
                              <a
                                href={citation.source}
                                target="_blank"
                                rel="noreferrer"
                                className="text-blue-600 hover:underline"
                              >
                                {citation.source}
                              </a>
                            ) : (
                              citation.source
                            )}
                          </p>
                        )}
                        <p className="text-xs text-gray-700 mt-2">{citation.excerpt}</p>
                      </div>
                    ))
                  ) : (
                    <div className="p-3 bg-white rounded border text-sm text-amber-900">
                      No grounded source was found for this diagnosis. Try adding more specific symptoms or use the RAG page to upload relevant clinical documents.
                    </div>
                  )}
                </div>
              )}

              <div className="space-y-4">
                {/* Medications */}
                {result.treatment_plan.medications && result.treatment_plan.medications.length > 0 && (
                  <div>
                    <h4 className="font-medium mb-2">💊 Medications</h4>
                    <div className="space-y-2">
                      {result.treatment_plan.medications.map((med, idx) => (
                        <div key={idx} className="p-3 bg-blue-50 rounded-lg">
                          <p className="font-medium">
                            {med.name}
                            {renderCitationAnchors(`${med.name} ${med.dosage} ${med.frequency} ${med.duration}`)}
                          </p>
                          <p className="text-sm text-gray-600">
                            {med.dosage} - {med.frequency} for {med.duration}
                          </p>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Non-Pharmacological */}
                {result.treatment_plan.non_pharmacological && (
                  <div>
                    <h4 className="font-medium mb-2">🏥 General Care</h4>
                    <ul className="space-y-1">
                      {result.treatment_plan.non_pharmacological.map((item, idx) => (
                        <li key={idx} className="text-sm">
                          • {item}
                          {renderCitationAnchors(item)}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}

                {/* Red Flags */}
                {result.treatment_plan.red_flags && result.treatment_plan.red_flags.length > 0 && (
                  <div className="p-4 bg-red-50 border border-red-200 rounded-lg">
                    <h4 className="font-medium text-red-900 mb-2">
                      ⚠️ Warning Signs - Seek Immediate Care If:
                    </h4>
                    <ul className="space-y-1">
                      {result.treatment_plan.red_flags.map((flag, idx) => (
                        <li key={idx} className="text-sm text-red-800">
                          • {flag}
                          {renderCitationAnchors(flag)}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            </Card>
          )}

          {/* Final Report */}
          <Card className="p-6">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold flex items-center gap-2">
                <FileText className="w-5 h-5" />
                Complete Medical Report
              </h3>
              <Button
                variant="outline"
                size="sm"
                onClick={() => {
                  const blob = new Blob([result.final_report], { type: 'text/plain' });
                  const url = URL.createObjectURL(blob);
                  const a = document.createElement('a');
                  a.href = url;
                  a.download = 'medical-report.txt';
                  a.click();
                }}
              >
                Download Report
              </Button>
            </div>

            <ScrollArea className="h-96 border rounded-lg p-4 bg-gray-50">
              <pre className="text-sm whitespace-pre-wrap font-mono">
                {result.final_report}
              </pre>
            </ScrollArea>
          </Card>

          {/* Workflow Steps */}
          <details>
            <summary className="cursor-pointer text-sm font-medium text-blue-600 hover:text-blue-700">
              View Agent Workflow Steps
            </summary>
            <Card className="p-4 mt-2">
              <ol className="space-y-2">
                {result.workflow_steps.map((step, idx) => (
                  <li key={idx} className="text-sm flex items-start gap-2">
                    <span className="font-semibold text-gray-500">{idx + 1}.</span>
                    <span>{step}</span>
                  </li>
                ))}
              </ol>
            </Card>
          </details>
        </div>
      )}
    </div>
  );
}
