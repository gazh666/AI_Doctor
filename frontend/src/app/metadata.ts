import { Metadata } from 'next';

export const siteMetadata: Metadata = {
  title: {
    default: 'Rural AI Doctor | AI-Powered Medical Diagnosis',
    template: '%s | Rural AI Doctor',
  },
  description:
    'Get instant medical diagnosis powered by AI. Chat with AI doctor, analyze medical images, voice-powered consultations. Accessible healthcare for everyone.',
  keywords: [
    'AI doctor',
    'medical diagnosis',
    'healthcare AI',
    'telemedicine',
    'rural healthcare',
    'medical chatbot',
    'AI diagnosis',
    'remote doctor',
  ],
  authors: [{ name: 'Rural AI Doctor Team' }],
  creator: 'Rural AI Doctor',
  publisher: 'Rural AI Doctor',
  formatDetection: {
    email: false,
    address: false,
    telephone: false,
  },
  openGraph: {
    title: 'Rural AI Doctor - AI-Powered Medical Diagnosis',
    description:
      'Get instant medical diagnosis powered by AI. Accessible healthcare for rural areas.',
    url: 'https://rural-ai-doctor-rwp9-ms2ddaaq6-rockys-projects-e671580a.vercel.app',
    siteName: 'Rural AI Doctor',
    locale: 'en_US',
    type: 'website',
  },
  twitter: {
    card: 'summary_large_image',
    title: 'Rural AI Doctor - AI-Powered Medical Diagnosis',
    description: 'Get instant medical diagnosis powered by AI',
    creator: '@rural_ai_doctor',
  },
  robots: {
    index: true,
    follow: true,
    googleBot: {
      index: true,
      follow: true,
      'max-video-preview': -1,
      'max-image-preview': 'large',
      'max-snippet': -1,
    },
  },
};