'use client';

import { useState, useRef } from 'react';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import { 
  Upload, 
  Image as ImageIcon, 
  Loader2, 
  CheckCircle, 
  AlertCircle,
  X,
  Download
} from 'lucide-react';
import { visionAPI, XRayAnalysisResponse } from '@/lib/api/vision';
import { getApiBaseUrl } from '@/lib/api/base-url';
import Image from 'next/image';
import jsPDF from 'jspdf';

export function XRayUpload() {
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<string | null>(null);
  const [analyzing, setAnalyzing] = useState(false);
  const [result, setResult] = useState<XRayAnalysisResponse | null>(null);
  const [downloading, setDownloading] = useState(false);
  
  // Form fields
  const [symptoms, setSymptoms] = useState('');
  const [age, setAge] = useState('');
  const [gender, setGender] = useState('');
  const [medicalHistory, setMedicalHistory] = useState('');
  
  const fileInputRef = useRef<HTMLInputElement>(null);

  const generateAndDownloadReport = (analysis: XRayAnalysisResponse) => {
    const doc = new jsPDF();
    const pageWidth = doc.internal.pageSize.getWidth();
    const margin = 14;
    const contentWidth = pageWidth - margin * 2;
    let y = 18;

    const ensurePage = (extraHeight: number = 8) => {
      if (y + extraHeight > 280) {
        doc.addPage();
        y = 18;
      }
    };

    const writeWrapped = (text: string, fontSize: number = 11) => {
      const lines = doc.splitTextToSize(text, contentWidth);
      doc.setFontSize(fontSize);
      for (const line of lines) {
        ensurePage(7);
        doc.text(line, margin, y);
        y += 6;
      }
    };

    doc.setFontSize(16);
    doc.text('Rural AI Doctor - X-Ray Analysis Report', margin, y);
    y += 10;

    doc.setFontSize(10);
    doc.text(`Report ID: ${analysis.analysis_id}`, margin, y);
    y += 6;
    doc.text(`Severity: ${analysis.severity}`, margin, y);
    y += 6;
    doc.text(`Confidence: ${(analysis.confidence * 100).toFixed(0)}%`, margin, y);
    y += 10;

    doc.setFontSize(12);
    doc.text('Key Findings', margin, y);
    y += 7;
    if (analysis.findings.length > 0) {
      analysis.findings.forEach((finding) => {
        writeWrapped(`- ${finding}`);
      });
    } else {
      writeWrapped('- No key findings were generated.');
    }

    y += 4;
    ensurePage(10);
    doc.setFontSize(12);
    doc.text('Differential Diagnosis', margin, y);
    y += 7;
    if (analysis.differential_diagnosis.length > 0) {
      analysis.differential_diagnosis.forEach((item) => {
        writeWrapped(`- ${item}`);
      });
    } else {
      writeWrapped('- No differential diagnosis provided.');
    }

    y += 4;
    ensurePage(10);
    doc.setFontSize(12);
    doc.text('Recommendations', margin, y);
    y += 7;
    writeWrapped(analysis.recommendations || 'No recommendations provided.');

    y += 6;
    ensurePage(14);
    doc.setFontSize(9);
    writeWrapped(
      'Disclaimer: This AI analysis is for informational purposes only and does not replace professional medical advice.'
    , 9);

    doc.save(`Medical_Report_${analysis.analysis_id}.pdf`);
  };

  const handleDownloadPDF = async () => {
    if (!result?.analysis_id) return;

    try {
      setDownloading(true);
      const API_BASE_URL = getApiBaseUrl();
      const response = await fetch(`${API_BASE_URL}/vision/analysis/${result.analysis_id}/pdf`);
      
      if (!response.ok) throw new Error('Failed to generate PDF');

      // Process the file stream
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `Medical_Report_${result.analysis_id}.pdf`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
    } catch (error) {
      // Fallback to client-side PDF generation when backend PDF endpoint is unavailable.
      generateAndDownloadReport(result);
    } finally {
      setDownloading(false);
    }
  };
  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const selectedFile = e.target.files[0];
      
      // Validate file type
      if (!selectedFile.type.startsWith('image/')) {
        alert('Please select an image file');
        return;
      }
      
      setFile(selectedFile);
      setResult(null);
      
      // Create preview
      const reader = new FileReader();
      reader.onload = (e) => {
        setPreview(e.target?.result as string);
      };
      reader.readAsDataURL(selectedFile);
    }
  };

  const handleAnalyze = async () => {
    if (!file) return;

    try {
      setAnalyzing(true);
      
      const response = await visionAPI.analyzeXRay({
        file,
        symptoms: symptoms || undefined,
        age: age ? parseInt(age) : undefined,
        gender: gender || undefined,
        medicalHistory: medicalHistory || undefined,
      });
      
      setResult(response);
    } catch (error: any) {
      console.error('Analysis error:', error);
      
     
      let errorMessage = 'Analysis failed. Please try again.';
      
      if (error.response?.status === 500) {
        const detail = error.response?.data?.detail || '';
        
        if (detail.includes('503') || detail.includes('UNAVAILABLE') || detail.includes('high demand')) {
          errorMessage = '⚠️ AI model is currently overloaded due to high demand. Please try again in a few moments.';
        } else {
          errorMessage = detail || 'Server error occurred';
        }
      } else if (error.response?.status === 400) {
        errorMessage = error.response?.data?.detail || 'Invalid image file';
      }
      
      alert(errorMessage);
    } finally {
      setAnalyzing(false);
    }
  };

  const handleClear = () => {
    setFile(null);
    setPreview(null);
    setResult(null);
    setSymptoms('');
    setAge('');
    setGender('');
    setMedicalHistory('');
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  const getSeverityColor = (severity: string) => {
    const colors: Record<string, string> = {
      critical: 'bg-red-100 text-red-800 border-red-300',
      severe: 'bg-orange-100 text-orange-800 border-orange-300',
      moderate: 'bg-yellow-100 text-yellow-800 border-yellow-300',
      mild: 'bg-blue-100 text-blue-800 border-blue-300',
      normal: 'bg-green-100 text-green-800 border-green-300',
    };
    return colors[severity] || 'bg-gray-100 text-gray-800 border-gray-300';
  };

  return (
    <div className="space-y-6">
      {/* Upload Section */}
      <Card className="p-6">
        <h3 className="text-lg font-semibold mb-4">Upload Chest X-Ray</h3>

        {!preview ? (
          <div className="border-2 border-dashed border-gray-300 rounded-lg p-8 text-center hover:border-blue-400 transition-colors">
            <input
              ref={fileInputRef}
              type="file"
              accept="image/*"
              onChange={handleFileChange}
              className="hidden"
              id="xray-upload"
            />
            <label
              htmlFor="xray-upload"
              className="cursor-pointer flex flex-col items-center gap-3"
            >
              <Upload className="w-16 h-16 text-gray-400" />
              <div>
                <p className="text-sm font-medium text-gray-700">
                  Click to upload chest X-ray
                </p>
                <p className="text-xs text-gray-500 mt-1">
                  PNG, JPG, or JPEG (max 10MB)
                </p>
              </div>
            </label>
          </div>
        ) : (
          <div className="space-y-4">
            {/* Image Preview */}
            <div className="relative border rounded-lg overflow-hidden bg-gray-50">
              <Image
                src={preview}
                alt="X-ray preview"
                width={800}
                height={600}
                className="w-full h-auto max-h-96 object-contain"
              />
              <Button
                variant="destructive"
                size="icon"
                className="absolute top-2 right-2"
                onClick={handleClear}
              >
                <X className="w-4 h-4" />
              </Button>
            </div>

            {/* Patient Information */}
            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label htmlFor="age">Age (optional)</Label>
                <Input
                  id="age"
                  type="number"
                  placeholder="e.g., 45"
                  value={age}
                  onChange={(e) => setAge(e.target.value)}
                  disabled={analyzing}
                />
              </div>
              <div>
                <Label htmlFor="gender">Gender (optional)</Label>
                <Input
                  id="gender"
                  placeholder="e.g., Male/Female"
                  value={gender}
                  onChange={(e) => setGender(e.target.value)}
                  disabled={analyzing}
                />
              </div>
            </div>

            <div>
              <Label htmlFor="symptoms">Symptoms (optional)</Label>
              <Textarea
                id="symptoms"
                placeholder="e.g., Cough for 2 weeks, fever, chest pain..."
                value={symptoms}
                onChange={(e) => setSymptoms(e.target.value)}
                rows={2}
                disabled={analyzing}
              />
            </div>

            <div>
              <Label htmlFor="history">Medical History (optional)</Label>
              <Textarea
                id="history"
                placeholder="e.g., Previous pneumonia, smoker..."
                value={medicalHistory}
                onChange={(e) => setMedicalHistory(e.target.value)}
                rows={2}
                disabled={analyzing}
              />
            </div>

            <Button
              onClick={handleAnalyze}
              disabled={analyzing}
              className="w-full"
              size="lg"
            >
              {analyzing ? (
                <>
                  <Loader2 className="w-5 h-5 mr-2 animate-spin" />
                  Analyzing X-Ray...
                </>
              ) : (
                <>
                  <ImageIcon className="w-5 h-5 mr-2" />
                  Analyze X-Ray
                </>
              )}
            </Button>
          </div>
        )}
      </Card>

      {/* Results Section */}
      {result && (
        <div className="space-y-4">
          {/* Urgent Flags */}
          {result.urgent_flags && result.urgent_flags.length > 0 && (
            <Card className="p-4 bg-red-50 border-red-200">
              <div className="flex items-start gap-3">
                <AlertCircle className="w-5 h-5 text-red-600 shrink-0 mt-0.5" />
                <div>
                  <h4 className="font-semibold text-red-900 mb-2">Urgent Attention Required</h4>
                  {result.urgent_flags.map((flag, idx) => (
                    <p key={idx} className="text-sm text-red-800">{flag}</p>
                  ))}
                </div>
              </div>
            </Card>
          )}

          {/* Summary Card */}
          <Card className="p-6 overflow-hidden">
            <div className="flex items-start justify-between mb-4">
              <h3 className="text-lg font-semibold">Analysis Results</h3>
              <div className="flex gap-2 flex-wrap justify-end max-w-full">
                <Badge className={getSeverityColor(result.severity)}>
                  {result.severity.toUpperCase()}
                </Badge>
                <Badge variant="secondary">
                  {(result.confidence * 100).toFixed(0)}% Confidence
                </Badge>
              </div>
            </div>

            <div className="mb-4 flex justify-end">
              <Button
                onClick={handleDownloadPDF}
                variant="outline"
                size="sm"
                disabled={downloading}
              >
                {downloading ? (
                  <>
                    <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                    Preparing Report...
                  </>
                ) : (
                  <>
                    <Download className="w-4 h-4 mr-2" />
                    Download Report (PDF)
                  </>
                )}
              </Button>
            </div>

            {/* Key Findings */}
            {result.findings && result.findings.length > 0 && (
              <div className="mb-4">
                <h4 className="font-medium mb-2 flex items-center gap-2">
                  <CheckCircle className="w-4 h-4 text-blue-600" />
                  Key Findings
                </h4>
                <ul className="space-y-1">
                  {result.findings.map((finding, idx) => (
                    <li key={idx} className="text-sm text-gray-700 pl-6 wrap-break-word">
                      • {finding}
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {/* Differential Diagnosis */}
            {result.differential_diagnosis && result.differential_diagnosis.length > 0 && (
              <div className="mb-4">
                <h4 className="font-medium mb-2">Differential Diagnosis</h4>
                <div className="flex flex-wrap gap-2">
                  {result.differential_diagnosis.map((diagnosis, idx) => (
                    <Badge key={idx} variant="outline" className="max-w-full whitespace-normal wrap-break-word text-left leading-snug">
                      {diagnosis}
                    </Badge>
                  ))}
                </div>
              </div>
            )}

            {/* Recommendations */}
            {result.recommendations && (
              <div className="mb-4">
                <h4 className="font-medium mb-2">Recommendations</h4>
                <p className="text-sm text-gray-700 whitespace-pre-wrap wrap-break-word">
                  {result.recommendations}
                </p>
              </div>
            )}

            {/* Full Analysis */}
            <details className="mt-4">
              <summary className="cursor-pointer font-medium text-sm text-blue-600 hover:text-blue-700">
                View Detailed Analysis
              </summary>
              <div className="mt-3 p-4 bg-gray-50 rounded-lg overflow-hidden">
                <p className="text-sm text-gray-800 whitespace-pre-wrap wrap-break-word">
                  {result.analysis}
                </p>
              </div>
            </details>
          </Card>

          {/* Disclaimer */}
          <Card className="p-4 bg-yellow-50 border-yellow-200">
            <p className="text-xs text-yellow-800">
              ⚠️ <strong>Disclaimer:</strong> This AI analysis is for informational purposes only 
              and should not replace professional medical advice. Please consult a qualified 
              healthcare provider for proper diagnosis and treatment.
            </p>
          </Card>
        </div>
      )}
    </div>
  );
}
