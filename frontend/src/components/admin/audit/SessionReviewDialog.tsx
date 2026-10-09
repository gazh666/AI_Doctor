'use client';

import { useEffect, useMemo, useState } from 'react';

import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Textarea } from '@/components/ui/textarea';
import { AuditLogRecord, SessionMessage, adminAPI } from '@/lib/api/admin';

interface SessionReviewDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  audit: AuditLogRecord | null;
  onFeedbackSaved: () => void;
}

export function SessionReviewDialog({ open, onOpenChange, audit, onFeedbackSaved }: SessionReviewDialogProps) {
  const [messages, setMessages] = useState<SessionMessage[]>([]);
  const [loadingSession, setLoadingSession] = useState(false);
  const [feedback, setFeedback] = useState('');
  const [overrideApplied, setOverrideApplied] = useState(false);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (!audit) return;
    setFeedback(audit.clinician_feedback || '');
    setOverrideApplied(Boolean(audit.override_applied));
  }, [audit]);

  useEffect(() => {
    const loadSession = async () => {
      if (!open || !audit?.session_id) {
        setMessages([]);
        return;
      }
      setLoadingSession(true);
      try {
        const res = await adminAPI.getAuditSession(audit.session_id);
        setMessages(res.messages || []);
      } catch (err) {
        console.error('Failed to load session history', err);
        setMessages([]);
      } finally {
        setLoadingSession(false);
      }
    };
    void loadSession();
  }, [open, audit?.session_id]);

  const confidenceClass = useMemo(() => {
    const band = (audit?.confidence_band || '').toLowerCase();
    if (band === 'low') return 'bg-red-100 text-red-700 border-red-300';
    if (band === 'medium') return 'bg-amber-100 text-amber-700 border-amber-300';
    if (band === 'high') return 'bg-green-100 text-green-700 border-green-300';
    return 'bg-gray-100 text-gray-700 border-gray-300';
  }, [audit?.confidence_band]);

  const saveFeedback = async () => {
    if (!audit) return;
    setSaving(true);
    try {
      await adminAPI.updateAuditFeedback(audit.id, {
        clinician_feedback: feedback,
        override_applied: overrideApplied,
      });
      onFeedbackSaved();
      onOpenChange(false);
    } catch (err) {
      console.error('Failed to save clinician feedback', err);
    } finally {
      setSaving(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-5xl w-[95vw]">
        <DialogHeader>
          <DialogTitle>Session Review</DialogTitle>
          <DialogDescription>
            Review AI input/output and leave clinician feedback for quality and safety monitoring.
          </DialogDescription>
        </DialogHeader>

        {audit ? (
          <div className="space-y-4">
            <div className="flex items-center gap-2 flex-wrap">
              <Badge className={confidenceClass} variant="outline">
                Confidence: {audit.confidence_band || 'unknown'}
              </Badge>
              <Badge variant="outline">Model: {audit.model_name}</Badge>
              <Badge variant="outline">Decision: {audit.decision_type}</Badge>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="border rounded-md p-3 bg-muted/20">
                <p className="text-sm font-semibold mb-2">Input Summary</p>
                <p className="text-sm whitespace-pre-wrap">{audit.input_summary || 'No input summary available.'}</p>
              </div>
              <div className="border rounded-md p-3 bg-muted/20">
                <p className="text-sm font-semibold mb-2">AI Output Summary</p>
                <p className="text-sm whitespace-pre-wrap">{audit.output_summary || 'No output summary available.'}</p>
              </div>
            </div>

            <div className="border rounded-md p-3">
              <p className="text-sm font-semibold mb-2">Chat Session Context</p>
              <div className="max-h-56 overflow-auto space-y-2 pr-1">
                {loadingSession && <p className="text-sm text-muted-foreground">Loading session transcript...</p>}
                {!loadingSession && messages.length === 0 && (
                  <p className="text-sm text-muted-foreground">No chat history found for this session.</p>
                )}
                {messages.map((msg) => (
                  <div key={msg.id} className="rounded border p-2">
                    <p className="text-xs uppercase tracking-wide text-muted-foreground">{msg.role}</p>
                    <p className="text-sm whitespace-pre-wrap">{msg.content}</p>
                  </div>
                ))}
              </div>
            </div>

            <div className="space-y-2">
              <p className="text-sm font-semibold">Clinician Feedback</p>
              <Textarea
                value={feedback}
                onChange={(e) => setFeedback(e.target.value)}
                placeholder="Document medical concerns, hallucinations, bias, or correction notes..."
                className="min-h-24"
              />
              <label className="flex items-center gap-2 text-sm">
                <input
                  type="checkbox"
                  checked={overrideApplied}
                  onChange={(e) => setOverrideApplied(e.target.checked)}
                />
                Mark this AI decision as overridden by clinician.
              </label>
            </div>
          </div>
        ) : (
          <p className="text-sm text-muted-foreground">No audit selected.</p>
        )}

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button onClick={saveFeedback} disabled={!audit || saving}>
            {saving ? 'Saving...' : 'Save Feedback'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

