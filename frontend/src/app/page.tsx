'use client';

import Link from 'next/link';
import { useRouter } from 'next/navigation';
import type { LucideIcon } from 'lucide-react';
import {
  Activity,
  BookOpen,
  CalendarClock,
  Download,
  FileText,
  FlaskConical,
  History,
  Image as ImageIcon,
  LogOut,
  Mic,
  Settings,
  ShieldCheck,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { useAuth } from '@/lib/auth/authContext';

type FeatureCard = {
  title: string;
  description: string;
  route: string;
  icon: LucideIcon;
};

type CarePillar = {
  title: string;
  description: string;
};

type QuickAccessItem = {
  title: string;
  route?: string;
  icon: LucideIcon;
  isAction?: boolean;
};



const FEATURE_CARDS: FeatureCard[] = [
  {
    title: 'AI Chat Triage',
    description: 'Start symptom conversations and route urgent cases quickly.',
    route: '/chat',
    icon: Activity,
  },
  {
    title: 'New Diagnosis',
    description: 'Run multi-agent diagnosis with treatment support guidance.',
    route: '/diagnosis',
    icon: FileText,
  },
  {
    title: 'Voice Consultation',
    description: 'Use speech workflows for faster consultations in local settings.',
    route: '/voice',
    icon: Mic,
  },
  {
    title: 'X-Ray Analysis',
    description: 'Upload X-rays and review AI-assisted findings securely.',
    route: '/xray',
    icon: ImageIcon,
  },
  {
    title: 'Knowledge Assistant',
    description: 'Ask clinical questions over your indexed medical resources.',
    route: '/rag',
    icon: BookOpen,
  },
  {
    title: 'Clinical Monitoring',
    description: 'Track activity, audit outcomes, and system reliability.',
    route: '/admin',
    icon: ShieldCheck,
  },
];

const CARE_PILLARS: CarePillar[] = [
  {
    title: 'Calm Clinical UI',
    description: 'A cleaner interface designed for focused patient-facing workflows.',
  },
  {
    title: 'Rural Ready',
    description: 'Built for quick usage in small clinics and distributed care centers.',
  },
  {
    title: 'Fast Access',
    description: 'Critical tools are available within one tap after sign-in.',
  },
];

const QUICK_ACCESS_ITEMS: QuickAccessItem[] = [
  { title: 'Clinical Ops', route: '/clinical-ops', icon: FlaskConical },
  { title: 'RAG Assistant', route: '/rag', icon: BookOpen },
  { title: 'History', route: '/history', icon: History },
  { title: 'Appointments', route: '/appointments', icon: CalendarClock },
  { title: 'Export Data', route: '/export', icon: Download },


  { title: 'Profile Settings', route: '/profile', icon: Settings },
  { title: 'Logout', icon: LogOut, isAction: true },
];

export default function Home() {
  const router = useRouter();
  const { isAuthenticated, loading, logout, user } = useAuth();

  const handleFeatureAccess = (route: string) => {
    if (!isAuthenticated) {
      router.push(`/login?next=${encodeURIComponent(route)}`);
      return;
    }

    router.push(route);
  };

  return (
    <main className={` min-h-screen bg-slate-50 text-slate-900`}>
      <div className="relative overflow-hidden border-b border-sky-100 bg-gradient-to-br from-sky-100 via-cyan-50 to-white">
        <div className="absolute -left-14 -top-14 h-52 w-52 rounded-full bg-cyan-200/40 blur-3xl" />
        <div className="absolute -right-12 top-12 h-44 w-44 rounded-full bg-emerald-200/35 blur-3xl" />

        <div className="container relative mx-auto px-4 py-12 md:py-16">
          <div className="max-w-3xl space-y-5">
            <div className="inline-flex items-center rounded-full border border-sky-200 bg-white/90 px-4 py-1 text-xs font-semibold tracking-wide text-sky-800 uppercase shadow-sm">
              Rural AI Doctor Care Console
            </div>

            <h1 className={` text-4xl leading-tight font-semibold text-slate-900 md:text-5xl`}>
              Clinical support designed with a hospital-first experience.
            </h1>

            <p className="max-w-2xl text-base text-slate-700 md:text-lg">
              A focused workspace for triage, diagnosis, voice consults, and imaging. The interface keeps care tools
              front and center so teams can move faster with confidence.
            </p>

            <div className="flex flex-wrap items-center gap-3">
              {!isAuthenticated && !loading ? (
                <>
                  <Button className="bg-cyan-700 hover:bg-cyan-800" asChild>
                    <Link href="/login">Open Clinical Console</Link>
                  </Button>
                  <Button variant="outline" className="border-cyan-300 text-cyan-800 hover:bg-cyan-50" asChild>
                    <Link href="/register">Create Care Team Account</Link>
                  </Button>
                </>
              ) : null}

              {isAuthenticated ? (
                <div className="rounded-md border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm text-emerald-800">
                  Signed in as {user?.email}
                </div>
              ) : null}
            </div>
          </div>
        </div>
      </div>

      <div className="container mx-auto space-y-8 px-4 py-8 md:py-10">
        <section className="grid grid-cols-1 gap-4 md:grid-cols-3">
          {CARE_PILLARS.map((pillar) => (
            <Card key={pillar.title} className="border-sky-100 bg-white/95 shadow-sm">
              <CardHeader className="pb-2">
                <CardTitle className="text-lg text-slate-900">{pillar.title}</CardTitle>
              </CardHeader>
              <CardContent>
                <CardDescription className="text-sm text-slate-600">{pillar.description}</CardDescription>
              </CardContent>
            </Card>
          ))}
        </section>

        <section className="space-y-4">
          <div className="flex items-center justify-between">
            <h2 className={` text-2xl font-semibold text-slate-900 md:text-3xl`}>Quick Access</h2>
            <span className="rounded-full bg-emerald-100 px-3 py-1 text-xs font-semibold text-emerald-800">Care Menu</span>
          </div>

          <div className="grid grid-cols-2 gap-3 md:grid-cols-4 xl:grid-cols-7">
            {QUICK_ACCESS_ITEMS.map((item) => {
              const Icon = item.icon;
              const isLogout = Boolean(item.isAction);

              return (
                <Card
                  key={item.title}
                  className="group border-slate-200 bg-white shadow-sm transition-all duration-300 hover:-translate-y-0.5 hover:border-cyan-200 hover:shadow-md"
                >
                  <CardContent className="p-3">
                    <Button
                      variant="ghost"
                      className="h-auto w-full flex-col gap-2 py-3 text-slate-700 hover:bg-cyan-50 hover:text-cyan-800"
                      onClick={() => {
                        if (isLogout) {
                          if (isAuthenticated) {
                            logout();
                          } else {
                            router.push('/login');
                          }
                          return;
                        }

                        if (item.route) {
                          handleFeatureAccess(item.route);
                        }
                      }}
                    >
                      <Icon className="h-5 w-5" />
                      <span className="text-xs font-semibold text-center leading-tight">{item.title}</span>
                    </Button>
                  </CardContent>
                </Card>
              );
            })}
          </div>
        </section>

        <section className="space-y-4">
          <div className="flex items-center justify-between">
            <h2 className={` text-2xl font-semibold text-slate-900 md:text-3xl`}>
              Clinical Feature Access
            </h2>
            <span className="rounded-full bg-cyan-100 px-3 py-1 text-xs font-semibold text-cyan-800">Hospital UI</span>
          </div>

          <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
            {FEATURE_CARDS.map((feature) => {
              const Icon = feature.icon;

              return (
                <Card
                  key={feature.route}
                  className="group h-full border-slate-200 bg-white shadow-sm transition-all duration-300 hover:-translate-y-1 hover:border-cyan-200 hover:shadow-lg"
                >
                  <CardHeader className="gap-3">
                    <div className="inline-flex h-10 w-10 items-center justify-center rounded-lg bg-cyan-100 text-cyan-800 transition-colors group-hover:bg-cyan-700 group-hover:text-white">
                      <Icon className="h-5 w-5" />
                    </div>
                    <CardTitle className="text-xl text-slate-900">{feature.title}</CardTitle>
                    <CardDescription className="text-sm text-slate-600">{feature.description}</CardDescription>
                  </CardHeader>
                  <CardContent>
                    <Button className="w-full bg-slate-900 hover:bg-slate-800" onClick={() => handleFeatureAccess(feature.route)}>
                      {isAuthenticated ? 'Open Feature' : 'Login Required'}
                    </Button>
                  </CardContent>
                </Card>
              );
            })}
          </div>
        </section>
      </div>
    </main>
  );
}
