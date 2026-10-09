'use client'

import React from 'react';
import { AlertTriangle } from 'lucide-react';

/**
 * Knowledge feature has been removed from this deployment.
 */
export default function KnowledgePage() {
  return (
    <div className="min-h-screen bg-slate-50/50" suppressHydrationWarning>
      <div className="container mx-auto p-6 max-w-3xl">
        <div className="mt-20 rounded-2xl border border-amber-200 bg-amber-50 p-8 text-center shadow-sm">
          <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-amber-100">
            <AlertTriangle className="h-6 w-6 text-amber-700" />
          </div>
          <h1 className="text-2xl font-bold text-slate-900">Knowledge Base Removed</h1>
          <p className="mt-3 text-slate-600">
            The Knowledge Base (RAG) feature has been removed from this project.
          </p>
          <p className="mt-2 text-sm text-slate-500">
            This page is intentionally disabled and no knowledge ingestion or query calls are made.
          </p>
        </div>
      </div>
    </div>
  );
}