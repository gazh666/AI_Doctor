import type { Metadata, Viewport } from 'next';
import './globals.css';
import { AuthProvider } from '@/lib/auth/authContext';
import { Navbar } from '@/components/layout/Navbar';

// Modern SEO Metadata
export const metadata: Metadata = {
  title: 'Rural AI Doctor - Medical AI Assistant',
  description: 'AI-powered medical assistant for rural healthcare, bridging the gap for accessible diagnostics.',
  icons: {
    icon: '/favicon.ico',
  },
  openGraph: {
    title: 'Rural AI Doctor',
    description: 'AI-powered medical assistant for rural healthcare',
    type: 'website',
  },
};

// Separate Viewport export (Standard for Next.js 14+)
export const viewport: Viewport = {
  themeColor: '#2563eb', // A professional medical blue
  width: 'device-width',
  initialScale: 1,
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className="antialiased" suppressHydrationWarning>
        <AuthProvider>
          <Navbar />
          {/* Main container with standard padding/spacing */}
          <main className="min-h-screen">
            {children}
          </main>
        </AuthProvider>
      </body>
    </html>
  );
}