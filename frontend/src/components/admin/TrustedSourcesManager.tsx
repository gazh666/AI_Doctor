'use client';

import { useEffect, useMemo, useState } from 'react';

import { Alert } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { adminAPI, TrustedSourceCreatePayload, TrustedSourceRecord } from '@/lib/api/admin';

const evidenceLevels = [
  'guideline',
  'systematic_review',
  'meta_analysis',
  'rct',
  'observational',
  'expert_consensus',
  'reference',
] as const;

const defaultForm: TrustedSourceCreatePayload = {
  provider: 'WHO',
  title: '',
  url: '',
  excerpt: '',
  condition_tags: [],
  evidence_level: 'guideline',
};

export function TrustedSourcesManager() {
  const [sources, setSources] = useState<TrustedSourceRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [seeding, setSeeding] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [form, setForm] = useState<TrustedSourceCreatePayload>(defaultForm);
  const [tagsInput, setTagsInput] = useState('');

  const sortedSources = useMemo(
    () =>
      [...sources].sort((a, b) => {
        const providerCmp = a.provider.localeCompare(b.provider);
        if (providerCmp !== 0) return providerCmp;
        return b.id - a.id;
      }),
    [sources],
  );

  useEffect(() => {
    void loadSources();
  }, []);

  const loadSources = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await adminAPI.listTrustedSources();
      setSources(data);
    } catch (err) {
      console.error('Failed to load trusted sources', err);
      setError('Failed to load trusted sources. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const handleSeedDefaults = async () => {
    setSeeding(true);
    setError(null);
    setNotice(null);
    try {
      const result = await adminAPI.seedDefaultTrustedSources();
      setNotice(`Default sources seeded: ${result.inserted}, already present: ${result.skipped_existing}.`);
      await loadSources();
    } catch (err) {
      console.error('Failed to seed default trusted sources', err);
      setError('Unable to seed default sources. Verify admin access and backend migration state.');
    } finally {
      setSeeding(false);
    }
  };

  const handleCreateSource = async () => {
    if (!form.provider?.trim() || !form.title?.trim() || !form.url?.trim() || !form.excerpt?.trim()) {
      setError('Provider, title, URL, and excerpt are required.');
      return;
    }

    setSaving(true);
    setError(null);
    setNotice(null);

    const payload: TrustedSourceCreatePayload = {
      ...form,
      condition_tags: tagsInput
        .split(',')
        .map((tag) => tag.trim())
        .filter(Boolean),
    };

    try {
      const created = await adminAPI.createTrustedSource(payload);
      setSources((prev) => [created, ...prev]);
      setForm(defaultForm);
      setTagsInput('');
      setNotice('Trusted source added successfully.');
    } catch (err) {
      console.error('Failed to create trusted source', err);
      setError('Unable to create trusted source. Ensure URL is valid and you are logged in as admin.');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="space-y-6">
      <Card className="p-6 space-y-4">
        <div className="flex items-center justify-between gap-3 flex-wrap">
          <div>
            <h3 className="text-lg font-semibold">Trusted Medical Sources</h3>
            <p className="text-sm text-gray-600">
              Manage the curated evidence catalog used to ground diagnosis and RAG answers.
            </p>
          </div>
          <div className="flex items-center gap-2">
            <Button variant="outline" onClick={() => void loadSources()} disabled={loading}>
              Refresh
            </Button>
            <Button variant="outline" onClick={() => void handleSeedDefaults()} disabled={seeding}>
              {seeding ? 'Seeding...' : 'Seed Baseline Sources'}
            </Button>
          </div>
        </div>

        {error && <Alert className="border-red-300 text-red-700">{error}</Alert>}
        {notice && <Alert className="border-emerald-300 text-emerald-700">{notice}</Alert>}
      </Card>

      <Card className="p-6 space-y-4">
        <h4 className="font-semibold">Add New Trusted Source</h4>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <Label htmlFor="provider">Provider</Label>
            <Input
              id="provider"
              value={form.provider}
              onChange={(e) => setForm((prev) => ({ ...prev, provider: e.target.value }))}
              placeholder="WHO"
            />
          </div>
          <div>
            <Label htmlFor="evidence-level">Evidence Level</Label>
            <Input
              id="evidence-level"
              list="evidence-level-list"
              value={form.evidence_level || ''}
              onChange={(e) => setForm((prev) => ({ ...prev, evidence_level: e.target.value }))}
              placeholder="guideline"
            />
            <datalist id="evidence-level-list">
              {evidenceLevels.map((level) => (
                <option key={level} value={level} />
              ))}
            </datalist>
          </div>
        </div>

        <div>
          <Label htmlFor="source-title">Title</Label>
          <Input
            id="source-title"
            value={form.title}
            onChange={(e) => setForm((prev) => ({ ...prev, title: e.target.value }))}
            placeholder="Fever in under 5s: assessment and initial management"
          />
        </div>

        <div>
          <Label htmlFor="source-url">Source URL</Label>
          <Input
            id="source-url"
            value={form.url}
            onChange={(e) => setForm((prev) => ({ ...prev, url: e.target.value }))}
            placeholder="https://www.nice.org.uk/guidance/ng143"
          />
        </div>

        <div>
          <Label htmlFor="source-excerpt">Evidence Excerpt</Label>
          <Textarea
            id="source-excerpt"
            rows={4}
            value={form.excerpt}
            onChange={(e) => setForm((prev) => ({ ...prev, excerpt: e.target.value }))}
            placeholder="Add a concise clinical recommendation excerpt used for retrieval grounding."
          />
        </div>

        <div>
          <Label htmlFor="source-tags">Condition Tags (comma-separated)</Label>
          <Input
            id="source-tags"
            value={tagsInput}
            onChange={(e) => setTagsInput(e.target.value)}
            placeholder="fever, pediatrics, triage"
          />
        </div>

        <Button onClick={() => void handleCreateSource()} disabled={saving}>
          {saving ? 'Saving Source...' : 'Add Trusted Source'}
        </Button>
      </Card>

      <Card className="p-6 space-y-3">
        <h4 className="font-semibold">Catalog ({sortedSources.length})</h4>

        {loading ? (
          <p className="text-sm text-gray-500">Loading sources...</p>
        ) : sortedSources.length === 0 ? (
          <p className="text-sm text-gray-500">No trusted sources found. Use Seed Baseline Sources or add one manually.</p>
        ) : (
          <div className="space-y-3 max-h-120 overflow-y-auto pr-1">
            {sortedSources.map((source) => (
              <div key={source.id} className="border rounded-lg p-4 bg-white">
                <div className="flex items-start justify-between gap-3 flex-wrap">
                  <div>
                    <p className="font-semibold text-gray-900">{source.title}</p>
                    <p className="text-xs text-gray-500">{source.url}</p>
                  </div>
                  <div className="flex items-center gap-2 flex-wrap">
                    <Badge variant="outline">{source.provider}</Badge>
                    {source.evidence_level && <Badge>{source.evidence_level}</Badge>}
                    {source.last_verified_at && (
                      <Badge variant="outline">Verified: {new Date(source.last_verified_at).toLocaleDateString()}</Badge>
                    )}
                  </div>
                </div>

                <p className="text-sm text-gray-700 mt-3">{source.excerpt}</p>

                {source.condition_tags?.length > 0 && (
                  <div className="mt-3 flex gap-2 flex-wrap">
                    {source.condition_tags.map((tag) => (
                      <Badge key={`${source.id}-${tag}`} variant="secondary">
                        {tag}
                      </Badge>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </Card>
    </div>
  );
}
