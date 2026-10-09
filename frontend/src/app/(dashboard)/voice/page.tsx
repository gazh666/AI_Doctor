'use client';

import { useEffect } from 'react';
import dynamic from 'next/dynamic';
import { useRouter } from 'next/navigation';
import { ShieldCheck, Zap, Loader2 } from 'lucide-react';
import { useAuth } from '@/lib/auth/authContext';

const VoiceDiagnosis = dynamic(
  () => import('@/components/voice/VoiceDiagnosis').then(mod => mod.VoiceDiagnosis),
  { 
    ssr: false,
    loading: () => (
      <div className="h-100 w-full flex items-center justify-center bg-slate-50 rounded-3xl border border-slate-100">
        <div className="flex flex-col items-center gap-2">
          <Loader2 className="h-8 w-8 animate-spin text-blue-600" />
          <p className="text-sm text-slate-500 font-medium">Loading Clinical Interface...</p>
        </div>
      </div>
    )
  }
);

const LiveVoiceConsultation = dynamic(
  () => import('@/components/voice/LiveVoiceConsultation').then(mod => mod.LiveVoiceConsultation),
  {
    ssr: false,
    loading: () => (
      <div className="h-55 w-full flex items-center justify-center bg-slate-50 rounded-3xl border border-slate-100">
        <div className="flex flex-col items-center gap-2">
          <Loader2 className="h-7 w-7 animate-spin text-blue-600" />
          <p className="text-sm text-slate-500 font-medium">Connecting Live Voice Interface...</p>
        </div>
      </div>
    )
  }
);

export default function VoicePage() {
  const { isAuthenticated, loading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!loading && !isAuthenticated) {
      router.push('/login?next=/voice');
    }
  }, [isAuthenticated, loading, router]);

  if (loading) {
    return <div className="p-8">Loading...</div>;
  }

  if (!isAuthenticated) {
    return null;
  }

  return (
    <div className="container mx-auto px-4 py-8 max-w-4xl animate-in fade-in duration-500">
      {/* Header Section */}
      <header className="mb-10 text-center md:text-left">
        <div className="flex items-center justify-center md:justify-start gap-3 mb-2">
          <h1 className="text-4xl font-black tracking-tight text-slate-900">
            Voice Consultation
          </h1>
          <span className="bg-blue-100 text-blue-700 text-xs font-bold px-2 py-1 rounded-md uppercase">
            Live AI
          </span>
        </div>
        <p className="text-lg text-slate-500 max-w-2xl">
          Describe your symptoms naturally. Our AI listens in 14+ languages to provide 
          instant triage and diagnostic support.
        </p>
      </header>

      <LiveVoiceConsultation />

      <div className="mt-10">
        <h2 className="text-xl font-bold text-slate-900 mb-3">One-Shot Voice Diagnosis (Legacy)</h2>
        <p className="text-sm text-slate-500 mb-4">
          Use this fallback flow if you prefer recording once and receiving a single comprehensive response.
        </p>
        <VoiceDiagnosis />
      </div>

      {/* Instructional & Safety Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mt-12">
        {/* Process Flow */}
        <div className="p-6 bg-slate-50 border border-slate-200 rounded-3xl">
          <h3 className="flex items-center gap-2 font-bold text-slate-900 mb-4">
            <Zap size={18} className="text-blue-600" />
            The Intelligent Workflow
          </h3>
          
          <ul className="space-y-3 text-sm text-slate-600">
            <li className="flex gap-3">
              <span className="font-bold text-blue-600">01</span>
              Local Whisper engine transcribes audio even on low bandwidth.
            </li>
            <li className="flex gap-3">
              <span className="font-bold text-blue-600">02</span>
              Agentic RAG scans 5,000+ medical journals for your symptoms.
            </li>
            <li className="flex gap-3">
              <span className="font-bold text-blue-600">03</span>
              Multi-agent consensus determines urgency and care steps.
            </li>
          </ul>
        </div>

        {/* Safety Disclaimer */}
        <div className="p-6 bg-amber-50 border border-amber-100 rounded-3xl">
          <h3 className="flex items-center gap-2 font-bold text-amber-900 mb-4">
            <ShieldCheck size={18} className="text-amber-600" />
            Medical Safety Notice
          </h3>
          <p className="text-sm text-amber-800 leading-relaxed">
            This AI is a decision-support tool designed for rural areas with limited access 
            to specialists. It is <strong>not</strong> a replacement for emergency services. 
            In case of severe pain or bleeding, please visit the nearest clinic immediately.
          </p>
        </div>
      </div>

      <footer className="mt-12 text-center text-slate-400 text-xs">
        &copy; 2026 Rural AI Doctor Project &bull; Encrypted & HIPAA Compliant Data Processing
      </footer>
    </div>
  );
}
