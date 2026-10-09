'use client';

import { useMemo, useState } from 'react';
import { formatISO } from 'date-fns';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Textarea } from '@/components/ui/textarea';
import apiClient from '@/lib/api/client';

type JsonValue = Record<string, unknown> | Array<unknown> | string | number | boolean | null;

function pretty(value: JsonValue): string {
  return JSON.stringify(value, null, 2);
}

export function ClinicalOpsConsole() {
  const [busy, setBusy] = useState(false);
  const [output, setOutput] = useState<string>('Run a flow to inspect live API responses.');

  const [triageSymptoms, setTriageSymptoms] = useState('Severe chest pain and shortness of breath');
  const [triageAge, setTriageAge] = useState('52');
  const [triageAssessmentId, setTriageAssessmentId] = useState('');
  const [triageEscalationReason, setTriageEscalationReason] = useState('Red-flag symptoms observed during triage.');

  const [followupPatientId, setFollowupPatientId] = useState('');
  const [followupDiagnosisId, setFollowupDiagnosisId] = useState('');
  const [followupDueAt, setFollowupDueAt] = useState(formatISO(new Date()));
  const [followupId, setFollowupId] = useState('');

  const [medications, setMedications] = useState('warfarin, aspirin');
  const [allergies, setAllergies] = useState('');
  const [conditions, setConditions] = useState('asthma');
  const [pregnant, setPregnant] = useState(false);
  const [medCondition, setMedCondition] = useState('hypertension');

  const [syncDeviceId, setSyncDeviceId] = useState('mobile-clinic-01');
  const [syncEntityType, setSyncEntityType] = useState('triage');
  const [syncEntityId, setSyncEntityId] = useState('triage-001');
  const [syncClientUpdatedAt, setSyncClientUpdatedAt] = useState(formatISO(new Date()));
  const [conflictEventId, setConflictEventId] = useState('');

  const [auditSessionId, setAuditSessionId] = useState('');
  const [auditId, setAuditId] = useState('');
  const [overrideReason, setOverrideReason] = useState('Clinician overrode recommendation due to physical exam findings.');

  const medicationList = useMemo(
    () => medications.split(',').map((s) => s.trim()).filter(Boolean),
    [medications]
  );

  const allergyList = useMemo(
    () => allergies.split(',').map((s) => s.trim()).filter(Boolean),
    [allergies]
  );

  const conditionList = useMemo(
    () => conditions.split(',').map((s) => s.trim()).filter(Boolean),
    [conditions]
  );

  const run = async (fn: () => Promise<unknown>) => {
    try {
      setBusy(true);
      const data = await fn();
      setOutput(pretty(data as JsonValue));
    } catch (error: any) {
      const detail = error?.response?.data ?? { message: error?.message ?? 'Request failed' };
      setOutput(pretty(detail));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="space-y-6">
      <Tabs defaultValue="triage" className="w-full">
        <TabsList className="grid grid-cols-5 w-full">
          <TabsTrigger value="triage">Triage</TabsTrigger>
          <TabsTrigger value="followups">Follow-Ups</TabsTrigger>
          <TabsTrigger value="medications">Medication</TabsTrigger>
          <TabsTrigger value="sync">Sync</TabsTrigger>
          <TabsTrigger value="audit">Audit</TabsTrigger>
        </TabsList>

        <TabsContent value="triage" className="space-y-4">
          <Card className="p-4 space-y-3">
            <Label>Symptoms</Label>
            <Textarea value={triageSymptoms} onChange={(e) => setTriageSymptoms(e.target.value)} rows={3} />
            <Label>Age</Label>
            <Input value={triageAge} onChange={(e) => setTriageAge(e.target.value)} />
            <div className="flex gap-2">
              <Button
                disabled={busy}
                onClick={() => run(async () => {
                  const res = await apiClient.post('/triage/assess', {
                    symptoms: triageSymptoms,
                    age: triageAge ? parseInt(triageAge, 10) : null,
                    risk_factors: ['hypertension'],
                    vitals: { spo2: 89, systolic_bp: 185, diastolic_bp: 120 },
                  });
                  if (res.data?.assessment_id) {
                    setTriageAssessmentId(String(res.data.assessment_id));
                  }
                  return res.data;
                })}
              >
                Assess Triage
              </Button>
              <Button
                variant="outline"
                disabled={busy}
                onClick={() => run(async () => (await apiClient.get('/triage/history')).data)}
              >
                Fetch History
              </Button>
            </div>
            <Label>Assessment ID (for escalation)</Label>
            <Input value={triageAssessmentId} onChange={(e) => setTriageAssessmentId(e.target.value)} />
            <Label>Escalation Reason</Label>
            <Input value={triageEscalationReason} onChange={(e) => setTriageEscalationReason(e.target.value)} />
            <Button
              disabled={busy || !triageAssessmentId}
              onClick={() => run(async () => (await apiClient.post('/triage/escalate', {
                assessment_id: parseInt(triageAssessmentId, 10),
                reason: triageEscalationReason,
              })).data)}
            >
              Escalate Case
            </Button>
          </Card>
        </TabsContent>

        <TabsContent value="followups" className="space-y-4">
          <Card className="p-4 space-y-3">
            <Label>Patient ID (optional)</Label>
            <Input value={followupPatientId} onChange={(e) => setFollowupPatientId(e.target.value)} />
            <Label>Diagnosis ID (optional)</Label>
            <Input value={followupDiagnosisId} onChange={(e) => setFollowupDiagnosisId(e.target.value)} />
            <Label>Due At (ISO)</Label>
            <Input value={followupDueAt} onChange={(e) => setFollowupDueAt(e.target.value)} />
            <div className="flex gap-2">
              <Button
                disabled={busy}
                onClick={() => run(async () => {
                  const res = await apiClient.post('/followups/schedule', {
                    patient_id: followupPatientId ? parseInt(followupPatientId, 10) : null,
                    diagnosis_id: followupDiagnosisId ? parseInt(followupDiagnosisId, 10) : null,
                    due_at: followupDueAt,
                    channel: 'sms',
                    reminder_enabled: true,
                    notes: 'Automated QA follow-up',
                  });
                  if (res.data?.id) {
                    setFollowupId(String(res.data.id));
                  }
                  return res.data;
                })}
              >
                Schedule Follow-Up
              </Button>
              <Button
                variant="outline"
                disabled={busy}
                onClick={() => run(async () => (await apiClient.get('/followups/pending')).data)}
              >
                Get Pending
              </Button>
            </div>
            <Label>Follow-Up ID (for status update)</Label>
            <Input value={followupId} onChange={(e) => setFollowupId(e.target.value)} />
            <Button
              disabled={busy || !followupId}
              onClick={() => run(async () => (await apiClient.patch(`/followups/${followupId}/status`, {
                status: 'completed',
                outcome: 'Patient improved after treatment.',
              })).data)}
            >
              Mark Completed
            </Button>
          </Card>
        </TabsContent>

        <TabsContent value="medications" className="space-y-4">
          <Card className="p-4 space-y-3">
            <Label>Medications (comma-separated)</Label>
            <Input value={medications} onChange={(e) => setMedications(e.target.value)} />
            <Label>Allergies (comma-separated)</Label>
            <Input value={allergies} onChange={(e) => setAllergies(e.target.value)} />
            <Label>Conditions (comma-separated)</Label>
            <Input value={conditions} onChange={(e) => setConditions(e.target.value)} />
            <label className="flex items-center gap-2 text-sm">
              <input type="checkbox" checked={pregnant} onChange={(e) => setPregnant(e.target.checked)} />
              Pregnant
            </label>
            <div className="flex gap-2">
              <Button
                disabled={busy}
                onClick={() => run(async () => (await apiClient.post('/medications/check-interactions', {
                  medications: medicationList,
                  allergies: allergyList,
                  conditions: conditionList,
                  pregnant,
                })).data)}
              >
                Check Interactions
              </Button>
              <Button
                variant="outline"
                disabled={busy}
                onClick={() => run(async () => (await apiClient.post('/medications/recommend', {
                  condition: medCondition,
                  current_medications: medicationList,
                  allergies: allergyList,
                  age: 35,
                  pregnant,
                })).data)}
              >
                Recommend Medication
              </Button>
            </div>
            <Label>Condition For Recommendation</Label>
            <Input value={medCondition} onChange={(e) => setMedCondition(e.target.value)} />
          </Card>
        </TabsContent>

        <TabsContent value="sync" className="space-y-4">
          <Card className="p-4 space-y-3">
            <Label>Device ID</Label>
            <Input value={syncDeviceId} onChange={(e) => setSyncDeviceId(e.target.value)} />
            <Label>Entity Type</Label>
            <Input value={syncEntityType} onChange={(e) => setSyncEntityType(e.target.value)} />
            <Label>Entity ID</Label>
            <Input value={syncEntityId} onChange={(e) => setSyncEntityId(e.target.value)} />
            <Label>Client Updated At (ISO)</Label>
            <Input value={syncClientUpdatedAt} onChange={(e) => setSyncClientUpdatedAt(e.target.value)} />
            <div className="flex gap-2">
              <Button
                disabled={busy}
                onClick={() => run(async () => {
                  const res = await apiClient.post('/sync/push', {
                    device_id: syncDeviceId,
                    records: [
                      {
                        entity_type: syncEntityType,
                        entity_id: syncEntityId,
                        operation: 'update',
                        payload: { note: 'qa sync update' },
                        client_updated_at: syncClientUpdatedAt,
                      },
                    ],
                  });
                  const first = res.data?.results?.[0];
                  if (first?.status === 'conflict') {
                    setConflictEventId(String(first.sync_event_id));
                  }
                  return res.data;
                })}
              >
                Push Sync
              </Button>
              <Button
                variant="outline"
                disabled={busy}
                onClick={() => run(async () => (await apiClient.get('/sync/pull')).data)}
              >
                Pull Sync
              </Button>
            </div>
            <Label>Conflict Event ID</Label>
            <Input value={conflictEventId} onChange={(e) => setConflictEventId(e.target.value)} />
            <Button
              disabled={busy || !conflictEventId}
              onClick={() => run(async () => (await apiClient.post('/sync/conflicts/resolve', {
                conflict_event_id: parseInt(conflictEventId, 10),
                strategy: 'merge',
                merged_payload: { note: 'merged on ops console' },
              })).data)}
            >
              Resolve Conflict (Merge)
            </Button>
          </Card>
        </TabsContent>

        <TabsContent value="audit" className="space-y-4">
          <Card className="p-4 space-y-3">
            <Label>Session ID (from chat)</Label>
            <Input value={auditSessionId} onChange={(e) => setAuditSessionId(e.target.value)} />
            <div className="flex gap-2">
              <Button
                disabled={busy || !auditSessionId}
                onClick={() => run(async () => {
                  const res = await apiClient.get(`/audit/decision/${auditSessionId}`);
                  const first = res.data?.[0];
                  if (first?.id) {
                    setAuditId(String(first.id));
                  }
                  return res.data;
                })}
              >
                Fetch Decision Log
              </Button>
              <Button
                variant="outline"
                disabled={busy}
                onClick={() => run(async () => (await apiClient.get('/audit/model-usage')).data)}
              >
                Get Model Usage
              </Button>
            </div>
            <Label>Audit ID</Label>
            <Input value={auditId} onChange={(e) => setAuditId(e.target.value)} />
            <Label>Override Reason</Label>
            <Textarea value={overrideReason} onChange={(e) => setOverrideReason(e.target.value)} rows={2} />
            <Button
              disabled={busy || !auditId}
              onClick={() => run(async () => (await apiClient.post('/audit/feedback', {
                audit_id: parseInt(auditId, 10),
                override_applied: true,
                override_reason: overrideReason,
                clinician_feedback: 'Reviewed and updated based on bedside exam.',
              })).data)}
            >
              Submit Override Feedback
            </Button>
          </Card>
        </TabsContent>
      </Tabs>

      <Card className="p-4">
        <h3 className="font-semibold mb-2">Live Response</h3>
        <pre className="text-xs whitespace-pre-wrap overflow-x-auto bg-slate-50 p-3 rounded-lg border">{output}</pre>
      </Card>
    </div>
  );
}
