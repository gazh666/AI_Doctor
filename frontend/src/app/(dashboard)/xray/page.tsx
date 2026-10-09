'use client';

import { useEffect } from 'react';
import { XRayUpload } from '@/components/vision/XRayUpload';
import { useAuth } from '@/lib/auth/authContext';
import { useRouter } from 'next/navigation';

export default function XRayPage() {
  const { isAuthenticated, loading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!loading && !isAuthenticated) {
      router.push('/login?next=/xray');
    }
  }, [isAuthenticated, loading, router]);

  if (loading) {
    return <div className="p-8">Loading...</div>;
  }

  if (!isAuthenticated) {
    return null;
  }

  return (
    <div className="container mx-auto p-6 max-w-4xl">
      <div className="mb-8">
        <h1 className="text-3xl font-bold mb-2">Chest X-Ray Analysis 🏥</h1>
        <p className="text-gray-600">
          Upload a chest X-ray image for AI-powered analysis using Gemini Vision
        </p>
      </div>

      <XRayUpload />
    </div>
  );
}
