'use client';

import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Download, FileSpreadsheet, FileJson, FileText } from 'lucide-react';
import apiClient from '@/lib/api/client';

export function DataExport() {
  const handleExport = async (format: 'csv' | 'excel' | 'json') => {
    try {
      const response = await apiClient.get(`/exports/diagnoses/${format}`, {
        responseType: 'blob',
      });

      // Create download link
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;

      const extension = format === 'excel' ? 'xlsx' : format;
      link.setAttribute('download', `diagnoses.${extension}`);

      document.body.appendChild(link);
      link.click();
      link.remove();
    } catch (error) {
      console.error('Export failed:', error);
      alert('Failed to export data');
    }
  };

  return (
    <Card className="p-6">
      <h3 className="text-lg font-semibold mb-4">Export Your Data</h3>

      <div className="space-y-3">
        <Button
          onClick={() => handleExport('csv')}
          variant="outline"
          className="w-full justify-start"
        >
          <FileText className="w-4 h-4 mr-2" />
          Export as CSV
        </Button>

        <Button
          onClick={() => handleExport('excel')}
          variant="outline"
          className="w-full justify-start"
        >
          <FileSpreadsheet className="w-4 h-4 mr-2" />
          Export as Excel
        </Button>

        <Button
          onClick={() => handleExport('json')}
          variant="outline"
          className="w-full justify-start"
        >
          <FileJson className="w-4 h-4 mr-2" />
          Export as JSON
        </Button>
      </div>

      <p className="text-xs text-gray-500 mt-4">
        Export all your diagnosis data for your records
      </p>
    </Card>
  );
}