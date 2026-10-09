'use client';

import { useMemo, useState } from 'react';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Badge } from '@/components/ui/badge';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Loader2, Upload, FileText, Search } from 'lucide-react';
import { ragAPI, RagQueryResponse, RagUploadResponse } from '@/lib/api/rag';

const MAX_UPLOAD_BYTES = 40 * 1024 * 1024;

export function RagWorkspace() {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [uploadResult, setUploadResult] = useState<RagUploadResponse | null>(null);

  const [question, setQuestion] = useState('');
  const [topK, setTopK] = useState('4');
  const [asking, setAsking] = useState(false);
  const [queryResult, setQueryResult] = useState<RagQueryResponse | null>(null);

  const fileSizeLabel = useMemo(() => {
    if (!selectedFile) return '';
    return `${(selectedFile.size / (1024 * 1024)).toFixed(2)} MB`;
  }, [selectedFile]);

  const onFileChange = (file: File | null) => {
    setUploadResult(null);
    setQueryResult(null);

    if (!file) {
      setSelectedFile(null);
      return;
    }

    const lowerName = file.name.toLowerCase();
    const isPdf = lowerName.endsWith('.pdf');
    const isTxt = lowerName.endsWith('.txt');
    const isMd = lowerName.endsWith('.md');
    const isCsv = lowerName.endsWith('.csv');

    if (!isPdf && !isTxt && !isMd && !isCsv) {
      alert('Only PDF, TXT, MD, and CSV files are allowed.');
      return;
    }

    if (file.size > MAX_UPLOAD_BYTES) {
      alert('File exceeds 40MB limit. Please upload a smaller file.');
      return;
    }

    setSelectedFile(file);
  };

  const handleUpload = async () => {
    if (!selectedFile) {
      alert('Please select a PDF, TXT, MD, or CSV file first.');
      return;
    }

    try {
      setUploading(true);
      const result = await ragAPI.uploadFile(selectedFile);
      setUploadResult(result);
      alert('File uploaded and indexed successfully.');
    } catch (error: any) {
      console.error('RAG upload error:', error);
      alert(error.response?.data?.detail || 'Failed to upload file');
    } finally {
      setUploading(false);
    }
  };

  const handleAsk = async () => {
    if (!question.trim()) {
      alert('Please enter a question.');
      return;
    }

    try {
      setAsking(true);
      const response = await ragAPI.ask({
        question: question.trim(),
        top_k: Number(topK) || 4,
      });
      setQueryResult(response);
    } catch (error: any) {
      console.error('RAG query error:', error);
      alert(error.response?.data?.detail || 'Failed to query uploaded reports');
    } finally {
      setAsking(false);
    }
  };

  return (
    <div className="space-y-6">
      <Card className="p-6">
        <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
          <Upload className="w-5 h-5" />
          Upload Report File (PDF/TXT/MD/CSV, Max 40MB)
        </h3>

        <div className="space-y-4">
          <div>
            <Label htmlFor="pdfUpload">Medical Report File</Label>
            <Input
              id="pdfUpload"
              type="file"
              accept=".pdf,.txt,.md,.csv,text/plain,text/markdown,text/csv,application/pdf"
              onChange={(e) => onFileChange(e.target.files?.[0] || null)}
              disabled={uploading}
            />
          </div>

          {selectedFile && (
            <div className="rounded-md border p-3 text-sm bg-slate-50">
              <p className="font-medium">{selectedFile.name}</p>
              <p className="text-slate-600">Size: {fileSizeLabel}</p>
            </div>
          )}

          <Button onClick={handleUpload} disabled={uploading || !selectedFile} className="w-full">
            {uploading ? (
              <>
                <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                Indexing file...
              </>
            ) : (
              <>
                <FileText className="w-4 h-4 mr-2" />
                Upload To Knowledge Base
              </>
            )}
          </Button>

          {uploadResult && (
            <div className="rounded-md border border-green-300 bg-green-50 p-3 text-sm">
              <p className="font-medium text-green-800">{uploadResult.message}</p>
              <p className="text-green-700">Chunks Indexed: {uploadResult.chunks_indexed}</p>
              <p className="text-green-700">KB ID: {uploadResult.knowledge_base_id}</p>
            </div>
          )}
        </div>
      </Card>

      <Card className="p-6">
        <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
          <Search className="w-5 h-5" />
          Ask Questions About Uploaded Reports
        </h3>

        <div className="space-y-4">
          <div>
            <Label htmlFor="ragQuestion">Question</Label>
            <Textarea
              id="ragQuestion"
              placeholder="Example: What are the critical findings in my report and what follow-up is suggested?"
              rows={4}
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              disabled={asking}
            />
          </div>

          <div className="max-w-32">
            <Label htmlFor="topK">Top Sources</Label>
            <Input
              id="topK"
              type="number"
              min={1}
              max={10}
              value={topK}
              onChange={(e) => setTopK(e.target.value)}
              disabled={asking}
            />
          </div>

          <Button onClick={handleAsk} disabled={asking || !question.trim()} className="w-full">
            {asking ? (
              <>
                <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                Generating Answer...
              </>
            ) : (
              'Ask RAG'
            )}
          </Button>
        </div>
      </Card>

      {queryResult && (
        <Card className="p-6 space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-lg font-semibold">RAG Answer</h3>
            <Badge variant="secondary">{queryResult.matched_chunks} sources matched</Badge>
          </div>

          <div className="rounded-md border p-4 bg-slate-50 whitespace-pre-wrap text-sm">
            {queryResult.answer}
          </div>

          <div>
            <h4 className="font-medium mb-2">Citations</h4>
            <ScrollArea className="h-72 pr-3">
              <div className="space-y-3">
                {queryResult.citations.map((citation) => (
                  <div key={citation.id} className="rounded-md border p-3">
                    <p className="font-medium text-sm">[{citation.rank}] {citation.title}</p>
                    {citation.source && (
                      <p className="text-xs text-slate-500 mt-1">Source: {citation.source}</p>
                    )}
                    <p className="text-sm text-slate-700 mt-2 whitespace-pre-wrap">{citation.excerpt}</p>
                  </div>
                ))}
              </div>
            </ScrollArea>
          </div>
        </Card>
      )}
    </div>
  );
}
