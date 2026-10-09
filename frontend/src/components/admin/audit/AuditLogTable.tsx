'use client';

import { useEffect, useMemo, useState } from 'react';

import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { AuditLogRecord, adminAPI } from '@/lib/api/admin';

import { SessionReviewDialog } from './SessionReviewDialog';

const PAGE_SIZE = 10;

export function AuditLogTable() {
  const [rows, setRows] = useState<AuditLogRecord[]>([]);
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const [search, setSearch] = useState('');
  const [confidenceFilter, setConfidenceFilter] = useState<'all' | 'low' | 'medium' | 'high'>('all');
  const [decisionFilter, setDecisionFilter] = useState<'all' | 'chat' | 'triage' | 'symptom_analysis'>('all');
  const [overriddenFilter, setOverriddenFilter] = useState<'all' | 'true' | 'false'>('all');
  const [loading, setLoading] = useState(false);
  const [exporting, setExporting] = useState(false);
  const [seeding, setSeeding] = useState(false);
  const [selectedAudit, setSelectedAudit] = useState<AuditLogRecord | null>(null);
  const [dialogOpen, setDialogOpen] = useState(false);
  const isNonProd =
    (process.env.NEXT_PUBLIC_ENVIRONMENT || process.env.NODE_ENV || 'production').toLowerCase() !== 'production';

  useEffect(() => {
    const timer = setTimeout(() => {
      void loadRows();
    }, 250);
    return () => clearTimeout(timer);
  }, [page, search, confidenceFilter, decisionFilter, overriddenFilter]);

  const loadRows = async () => {
    setLoading(true);
    try {
      const data = await adminAPI.getAuditLogs({
        page,
        page_size: PAGE_SIZE,
        q: search || undefined,
        confidence_band: confidenceFilter === 'all' ? undefined : confidenceFilter,
        decision_type: decisionFilter === 'all' ? undefined : decisionFilter,
        overridden:
          overriddenFilter === 'all' ? undefined : overriddenFilter === 'true',
      });
      setRows(data.items || []);
      setTotal(data.total || 0);
    } catch (err) {
      console.error('Failed to load audit logs', err);
      setRows([]);
      setTotal(0);
    } finally {
      setLoading(false);
    }
  };

  const totalPages = useMemo(() => Math.max(1, Math.ceil(total / PAGE_SIZE)), [total]);

  const openSessionReview = (row: AuditLogRecord) => {
    setSelectedAudit(row);
    setDialogOpen(true);
  };

  const seedDemoData = async () => {
    setSeeding(true);
    try {
      await adminAPI.seedDemoAudits(30);
      setPage(1);
      await loadRows();
    } catch (err) {
      console.error('Failed to seed demo audit rows', err);
    } finally {
      setSeeding(false);
    }
  };

  const exportCsv = async () => {
    setExporting(true);
    try {
      let exportPage = 1;
      const allRows: AuditLogRecord[] = [];
      let expectedTotal = 1;

      while (allRows.length < expectedTotal) {
        const data = await adminAPI.getAuditLogs({
          page: exportPage,
          page_size: 100,
          q: search || undefined,
          confidence_band: confidenceFilter === 'all' ? undefined : confidenceFilter,
          decision_type: decisionFilter === 'all' ? undefined : decisionFilter,
          overridden: overriddenFilter === 'all' ? undefined : overriddenFilter === 'true',
        });
        expectedTotal = data.total || 0;
        if (!data.items?.length) break;
        allRows.push(...data.items);
        exportPage += 1;
      }

      const escapeCsv = (value: unknown) => {
        const str = String(value ?? '');
        return `"${str.replace(/"/g, '""')}"`;
      };

      const header = [
        'id',
        'created_at',
        'decision_type',
        'confidence_band',
        'override_applied',
        'model_name',
        'session_id',
        'input_summary',
        'output_summary',
      ];
      const body = allRows.map((row) =>
        [
          row.id,
          row.created_at,
          row.decision_type,
          row.confidence_band,
          row.override_applied,
          row.model_name,
          row.session_id,
          row.input_summary,
          row.output_summary,
        ]
          .map(escapeCsv)
          .join(','),
      );
      const csv = [header.join(','), ...body].join('\n');

      const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `ai_audit_logs_${new Date().toISOString().slice(0, 10)}.csv`);
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      URL.revokeObjectURL(url);
    } catch (err) {
      console.error('Failed to export audit CSV', err);
    } finally {
      setExporting(false);
    }
  };

  return (
    <div className="space-y-4">
      <Card className="p-4">
        <div className="flex items-center gap-3 flex-wrap">
          <Input
            value={search}
            onChange={(e) => {
              setPage(1);
              setSearch(e.target.value);
            }}
            placeholder="Search input/output/model/session..."
            className="max-w-md"
          />
          <Button variant="outline" onClick={() => void loadRows()} disabled={loading}>
            Refresh
          </Button>
          <Button variant="outline" onClick={() => void exportCsv()} disabled={loading || exporting}>
            {exporting ? 'Exporting...' : 'Export CSV'}
          </Button>
          {isNonProd && (
            <Button variant="outline" onClick={() => void seedDemoData()} disabled={loading || seeding}>
              {seeding ? 'Seeding...' : 'Seed Demo Data'}
            </Button>
          )}
          <p className="text-sm text-muted-foreground ml-auto">
            Showing page {page} of {totalPages} ({total} logs)
          </p>
        </div>

        <div className="mt-3 flex flex-wrap gap-2">
          <span className="text-xs text-muted-foreground self-center mr-1">Confidence:</span>
          {(['all', 'low', 'medium', 'high'] as const).map((item) => (
            <Button
              key={`confidence-${item}`}
              size="sm"
              variant={confidenceFilter === item ? 'default' : 'outline'}
              onClick={() => {
                setPage(1);
                setConfidenceFilter(item);
              }}
            >
              {item}
            </Button>
          ))}

          <span className="text-xs text-muted-foreground self-center ml-3 mr-1">Decision:</span>
          {(['all', 'chat', 'triage', 'symptom_analysis'] as const).map((item) => (
            <Button
              key={`decision-${item}`}
              size="sm"
              variant={decisionFilter === item ? 'default' : 'outline'}
              onClick={() => {
                setPage(1);
                setDecisionFilter(item);
              }}
            >
              {item}
            </Button>
          ))}

          <span className="text-xs text-muted-foreground self-center ml-3 mr-1">Override:</span>
          {(['all', 'true', 'false'] as const).map((item) => (
            <Button
              key={`override-${item}`}
              size="sm"
              variant={overriddenFilter === item ? 'default' : 'outline'}
              onClick={() => {
                setPage(1);
                setOverriddenFilter(item);
              }}
            >
              {item === 'all' ? 'all' : item === 'true' ? 'overridden' : 'not overridden'}
            </Button>
          ))}
        </div>
      </Card>

      <Card className="overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-muted/50">
              <tr>
                <th className="text-left p-3 font-semibold">Timestamp</th>
                <th className="text-left p-3 font-semibold">Decision</th>
                <th className="text-left p-3 font-semibold">Input</th>
                <th className="text-left p-3 font-semibold">Output</th>
                <th className="text-left p-3 font-semibold">Confidence</th>
                <th className="text-left p-3 font-semibold">Model</th>
              </tr>
            </thead>
            <tbody>
              {loading && (
                <tr>
                  <td className="p-4 text-muted-foreground" colSpan={6}>
                    Loading audit logs...
                  </td>
                </tr>
              )}
              {!loading && rows.length === 0 && (
                <tr>
                  <td className="p-4 text-muted-foreground" colSpan={6}>
                    No audit logs found.
                  </td>
                </tr>
              )}
              {!loading &&
                rows.map((row) => {
                  const confidence = (row.confidence_band || 'unknown').toLowerCase();
                  const lowConfidence = confidence === 'low';
                  return (
                    <tr
                      key={row.id}
                      onClick={() => openSessionReview(row)}
                      className={`border-t cursor-pointer hover:bg-muted/30 ${lowConfidence ? 'bg-red-50/60' : ''}`}
                    >
                      <td className="p-3 whitespace-nowrap">
                        {new Date(row.created_at).toLocaleString()}
                      </td>
                      <td className="p-3">
                        <div className="flex gap-2 items-center">
                          <Badge variant="outline">{row.decision_type}</Badge>
                          {row.override_applied && <Badge variant="destructive">Overridden</Badge>}
                        </div>
                      </td>
                      <td className="p-3 max-w-sm">
                        <p className="line-clamp-2">{row.input_summary || 'N/A'}</p>
                      </td>
                      <td className="p-3 max-w-sm">
                        <p className="line-clamp-2">{row.output_summary || 'N/A'}</p>
                      </td>
                      <td className="p-3">
                        <Badge
                          variant="outline"
                          className={
                            confidence === 'low'
                              ? 'text-red-700 border-red-300 bg-red-100'
                              : confidence === 'medium'
                                ? 'text-amber-700 border-amber-300 bg-amber-100'
                                : 'text-green-700 border-green-300 bg-green-100'
                          }
                        >
                          {row.confidence_band || 'unknown'}
                        </Badge>
                      </td>
                      <td className="p-3">{row.model_name}</td>
                    </tr>
                  );
                })}
            </tbody>
          </table>
        </div>
      </Card>

      <div className="flex items-center justify-end gap-2">
        <Button variant="outline" onClick={() => setPage((v) => Math.max(1, v - 1))} disabled={page <= 1 || loading}>
          Previous
        </Button>
        <Button
          variant="outline"
          onClick={() => setPage((v) => Math.min(totalPages, v + 1))}
          disabled={page >= totalPages || loading}
        >
          Next
        </Button>
      </div>

      <SessionReviewDialog
        open={dialogOpen}
        onOpenChange={setDialogOpen}
        audit={selectedAudit}
        onFeedbackSaved={() => void loadRows()}
      />
    </div>
  );
}
