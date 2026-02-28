'use client';

import { useRouter } from 'next/navigation';
import { useIsAuthenticated, useMsal } from '@azure/msal-react';
import { InteractionStatus } from '@azure/msal-browser';
import {
  Shield,
  DollarSign,
  Lightbulb,
  Server,
  Building2,
  ArrowRight,
  BarChart3,
  Zap,
  CheckCircle,
  Globe,
  TrendingDown,
  Lock,
  Sparkles,
  ChevronRight,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { loginRequest, AUTH_ENABLED } from '@/lib/msal';
import { HeroIllustration } from '@/components/landing/hero-illustration';

/* ---------- static data ---------- */
const features = [
  {
    icon: DollarSign,
    title: 'Cost Analysis',
    description: 'Deep visibility into Azure spend by service, resource group, and subscription with daily trend tracking.',
    gradient: 'from-blue-500 to-cyan-500',
    bgGlow: 'bg-blue-500/10',
  },
  {
    icon: Lightbulb,
    title: 'Smart Recommendations',
    description: 'AI-powered optimization suggestions with savings estimates, confidence scores, and approval workflows.',
    gradient: 'from-amber-500 to-orange-500',
    bgGlow: 'bg-amber-500/10',
  },
  {
    icon: Server,
    title: 'Resource Tracking',
    description: 'Complete inventory of all Azure resources across subscriptions with tags and utilization insights.',
    gradient: 'from-emerald-500 to-green-500',
    bgGlow: 'bg-emerald-500/10',
  },
  {
    icon: Building2,
    title: 'Multi-Tenant',
    description: 'Manage costs across multiple Azure tenants from a single dashboard with tenant-level data isolation.',
    gradient: 'from-purple-500 to-indigo-500',
    bgGlow: 'bg-purple-500/10',
  },
];

const steps = [
  {
    num: '01',
    icon: Globe,
    title: 'Connect',
    description: 'Link your Azure tenants and subscriptions via secure service principal with Entra ID.',
  },
  {
    num: '02',
    icon: BarChart3,
    title: 'Analyze',
    description: 'Automated daily ingestion of costs, resources, and Azure Advisor recommendations.',
  },
  {
    num: '03',
    icon: Zap,
    title: 'Optimize',
    description: 'Review, approve, and execute optimization recommendations to reduce cloud spend.',
  },
];

const stats = [
  { value: '11', label: 'Optimization Rules', icon: Sparkles },
  { value: '4', label: 'Rule Categories', icon: BarChart3 },
  { value: '100%', label: 'Entra ID Secured', icon: Lock },
  { value: 'Real-time', label: 'Cost Insights', icon: TrendingDown },
];

const trustedBy = [
  'Virtual Machines', 'Azure SQL', 'App Service', 'AKS', 'Cosmos DB', 'Storage', 'Functions', 'Key Vault',
];

/* ---------- component ---------- */
export default function LandingPage() {
  const isAuthenticated = useIsAuthenticated();
  const { instance, inProgress } = useMsal();
  const router = useRouter();
  const loading = inProgress !== InteractionStatus.None;

  const handleSignIn = () => {
    if (!AUTH_ENABLED) {
      router.push('/dashboard');
      return;
    }
    instance.loginRedirect(loginRequest);
  };

  const handleGoToDashboard = () => router.push('/dashboard');

  return (
    <div className="min-h-screen bg-background overflow-hidden">
      {/* ── Navbar ─────────────────────────────────── */}
      <nav className="sticky top-0 z-50 border-b bg-background/80 backdrop-blur-xl">
        <div className="container mx-auto flex h-16 items-center justify-between px-6">
          <div className="flex items-center gap-2.5">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-gradient-to-br from-blue-600 to-indigo-600 shadow-lg shadow-blue-500/25">
              <Shield className="h-4 w-4 text-white" />
            </div>
            <span className="text-xl font-bold tracking-tight">AzCops</span>
            <span className="hidden sm:inline-flex items-center rounded-full border border-blue-200 bg-blue-50 px-2 py-0.5 text-[10px] font-medium text-blue-700 dark:border-blue-800 dark:bg-blue-950 dark:text-blue-300">
              v0.1
            </span>
          </div>
          <div className="flex items-center gap-3">
            {loading ? (
              <Button disabled variant="outline" size="sm">
                Loading...
              </Button>
            ) : isAuthenticated ? (
              <Button onClick={handleGoToDashboard} size="sm" className="group">
                Go to Dashboard
                <ArrowRight className="ml-2 h-4 w-4 transition-transform group-hover:translate-x-0.5" />
              </Button>
            ) : (
              <>
                <Button variant="ghost" size="sm" onClick={handleSignIn} className="hidden sm:inline-flex">
                  Sign in
                </Button>
                <Button onClick={handleSignIn} size="sm" className="group bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700 shadow-lg shadow-blue-500/25">
                  Get Started
                  <ArrowRight className="ml-2 h-4 w-4 transition-transform group-hover:translate-x-0.5" />
                </Button>
              </>
            )}
          </div>
        </div>
      </nav>

      {/* ── Hero ───────────────────────────────────── */}
      <section className="relative">
        {/* Background gradient orbs */}
        <div className="absolute inset-0 overflow-hidden pointer-events-none">
          <div className="absolute -top-40 -right-40 h-[500px] w-[500px] rounded-full bg-blue-500/5 blur-3xl" />
          <div className="absolute -bottom-40 -left-40 h-[500px] w-[500px] rounded-full bg-indigo-500/5 blur-3xl" />
          <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 h-[600px] w-[600px] rounded-full bg-purple-500/3 blur-3xl" />
          {/* Grid pattern */}
          <div className="absolute inset-0 bg-[linear-gradient(rgba(99,102,241,0.03)_1px,transparent_1px),linear-gradient(90deg,rgba(99,102,241,0.03)_1px,transparent_1px)] bg-[size:60px_60px]" />
        </div>

        <div className="container mx-auto px-6 py-16 lg:py-24">
          <div className="grid gap-12 lg:grid-cols-2 lg:gap-16 items-center">
            {/* Left: Text */}
            <div className="max-w-xl">
              <div className="mb-6 inline-flex items-center gap-2 rounded-full border border-blue-200 bg-blue-50 px-4 py-1.5 text-sm dark:border-blue-800 dark:bg-blue-950">
                <CheckCircle className="h-3.5 w-3.5 text-green-500" />
                <span className="text-blue-700 dark:text-blue-300">Enterprise-grade Azure FinOps Platform</span>
              </div>

              <h1 className="text-4xl font-bold tracking-tight sm:text-5xl lg:text-6xl leading-[1.1]">
                Azure Cost
                <br />
                Optimization
                <span className="block mt-1 bg-gradient-to-r from-blue-600 via-indigo-600 to-purple-600 bg-clip-text text-transparent">
                  Made Simple
                </span>
              </h1>

              <p className="mt-6 text-lg leading-8 text-muted-foreground">
                Identify waste, right-size resources, and govern cloud spend across all your
                Azure tenants — powered by intelligent rules and real-time cost data.
              </p>

              <div className="mt-8 flex flex-col sm:flex-row gap-3">
                {isAuthenticated ? (
                  <Button size="lg" onClick={handleGoToDashboard} className="group bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700 shadow-lg shadow-blue-500/25 h-12 px-8">
                    Open Dashboard
                    <ArrowRight className="ml-2 h-4 w-4 transition-transform group-hover:translate-x-1" />
                  </Button>
                ) : (
                  <>
                    <Button size="lg" onClick={handleSignIn} className="group bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700 shadow-lg shadow-blue-500/25 h-12 px-8">
                      Get Started Free
                      <ArrowRight className="ml-2 h-4 w-4 transition-transform group-hover:translate-x-1" />
                    </Button>
                    <Button size="lg" variant="outline" onClick={handleSignIn} className="group h-12 px-8">
                      Sign in with Azure
                      <ChevronRight className="ml-1 h-4 w-4 transition-transform group-hover:translate-x-0.5" />
                    </Button>
                  </>
                )}
              </div>

              {/* Social proof mini */}
              <div className="mt-10 flex items-center gap-3">
                <div className="flex -space-x-2">
                  {['bg-blue-500', 'bg-indigo-500', 'bg-purple-500', 'bg-emerald-500'].map((bg, i) => (
                    <div key={i} className={`h-8 w-8 rounded-full ${bg} border-2 border-background flex items-center justify-center text-[10px] font-bold text-white`}>
                      {['AZ', 'FN', 'CT', 'NW'][i]}
                    </div>
                  ))}
                </div>
                <p className="text-sm text-muted-foreground">
                  Trusted by <span className="font-semibold text-foreground">FinOps</span> teams managing Azure at scale
                </p>
              </div>
            </div>

            {/* Right: Dashboard Preview */}
            <div className="hidden lg:block">
              <HeroIllustration />
            </div>
          </div>
        </div>
      </section>

      {/* ── Scrolling Service Ticker ─────────────── */}
      <section className="border-y bg-muted/20 py-5 overflow-hidden">
        <div className="flex items-center justify-center gap-8 animate-marquee whitespace-nowrap">
          {[...trustedBy, ...trustedBy].map((name, i) => (
            <div key={i} className="flex items-center gap-2 text-sm text-muted-foreground/60">
              <div className="h-1.5 w-1.5 rounded-full bg-blue-500/40" />
              {name}
            </div>
          ))}
        </div>
      </section>

      {/* ── Stats Bar ──────────────────────────────── */}
      <section className="py-16">
        <div className="container mx-auto px-6">
          <div className="grid grid-cols-2 gap-6 md:grid-cols-4">
            {stats.map((s) => (
              <div
                key={s.label}
                className="group relative rounded-2xl border bg-card p-6 text-center transition-all hover:shadow-lg hover:border-primary/20"
              >
                <div className="mx-auto mb-3 flex h-10 w-10 items-center justify-center rounded-xl bg-primary/10 group-hover:bg-primary/15 transition-colors">
                  <s.icon className="h-5 w-5 text-primary" />
                </div>
                <p className="text-3xl font-bold bg-gradient-to-br from-foreground to-foreground/70 bg-clip-text text-transparent">
                  {s.value}
                </p>
                <p className="mt-1.5 text-sm text-muted-foreground">{s.label}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── Features Grid ──────────────────────────── */}
      <section className="py-20 relative">
        <div className="absolute inset-0 bg-[linear-gradient(rgba(99,102,241,0.02)_1px,transparent_1px),linear-gradient(90deg,rgba(99,102,241,0.02)_1px,transparent_1px)] bg-[size:40px_40px] pointer-events-none" />
        <div className="container mx-auto px-6 relative">
          <div className="mx-auto max-w-2xl text-center mb-14">
            <div className="inline-flex items-center rounded-full border px-3 py-1 text-xs font-medium text-muted-foreground mb-4">
              <Sparkles className="mr-1.5 h-3 w-3" />
              Features
            </div>
            <h2 className="text-3xl font-bold tracking-tight sm:text-4xl">
              Everything You Need for{' '}
              <span className="bg-gradient-to-r from-blue-600 to-indigo-600 bg-clip-text text-transparent">
                Azure FinOps
              </span>
            </h2>
            <p className="mt-4 text-lg text-muted-foreground">
              From cost visibility to automated recommendations, AzCops covers the full
              FinOps lifecycle.
            </p>
          </div>

          <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-4">
            {features.map((f) => (
              <Card key={f.title} className="group relative overflow-hidden border transition-all hover:shadow-xl hover:border-primary/20 hover:-translate-y-1 duration-300">
                {/* Subtle gradient overlay on hover */}
                <div className={`absolute inset-0 ${f.bgGlow} opacity-0 group-hover:opacity-100 transition-opacity duration-300`} />
                <CardHeader className="relative">
                  <div className={`mb-4 flex h-12 w-12 items-center justify-center rounded-xl bg-gradient-to-br ${f.gradient} shadow-lg`}>
                    <f.icon className="h-6 w-6 text-white" />
                  </div>
                  <CardTitle className="text-lg">{f.title}</CardTitle>
                </CardHeader>
                <CardContent className="relative">
                  <CardDescription className="leading-relaxed">{f.description}</CardDescription>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      </section>

      {/* ── How It Works ───────────────────────────── */}
      <section className="border-t bg-muted/30 py-20">
        <div className="container mx-auto px-6">
          <div className="mx-auto max-w-2xl text-center mb-14">
            <div className="inline-flex items-center rounded-full border px-3 py-1 text-xs font-medium text-muted-foreground mb-4">
              Getting Started
            </div>
            <h2 className="text-3xl font-bold tracking-tight sm:text-4xl">
              Up and Running in{' '}
              <span className="bg-gradient-to-r from-blue-600 to-indigo-600 bg-clip-text text-transparent">
                Minutes
              </span>
            </h2>
            <p className="mt-4 text-lg text-muted-foreground">
              Three simple steps to start optimizing your Azure spend.
            </p>
          </div>

          <div className="relative">
            {/* Connecting line */}
            <div className="absolute top-7 left-0 right-0 hidden md:block">
              <div className="mx-auto max-w-2xl h-0.5 bg-gradient-to-r from-transparent via-primary/20 to-transparent" />
            </div>

            <div className="grid gap-10 md:grid-cols-3 max-w-4xl mx-auto">
              {steps.map((s) => (
                <div key={s.num} className="relative text-center group">
                  <div className="mx-auto mb-5 relative">
                    <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-2xl bg-gradient-to-br from-blue-600 to-indigo-600 text-white shadow-lg shadow-blue-500/25 group-hover:shadow-blue-500/40 transition-shadow">
                      <s.icon className="h-6 w-6" />
                    </div>
                    <div className="absolute -top-2 -right-2 flex h-6 w-6 items-center justify-center rounded-full bg-background border-2 border-primary text-[10px] font-bold text-primary">
                      {s.num}
                    </div>
                  </div>
                  <h3 className="text-xl font-semibold mb-2">{s.title}</h3>
                  <p className="text-sm leading-6 text-muted-foreground max-w-xs mx-auto">{s.description}</p>
                </div>
              ))}
            </div>
          </div>

          <div className="mt-14 text-center">
            <Button size="lg" onClick={isAuthenticated ? handleGoToDashboard : handleSignIn} className="group bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700 shadow-lg shadow-blue-500/25 h-12 px-8">
              {isAuthenticated ? 'Open Dashboard' : 'Start Optimizing Now'}
              <ArrowRight className="ml-2 h-4 w-4 transition-transform group-hover:translate-x-1" />
            </Button>
          </div>
        </div>
      </section>

      {/* ── CTA Banner ────────────────────────────── */}
      <section className="py-20">
        <div className="container mx-auto px-6">
          <div className="relative overflow-hidden rounded-3xl bg-gradient-to-br from-blue-600 via-indigo-600 to-purple-700 px-8 py-16 text-center shadow-2xl">
            {/* Background pattern */}
            <div className="absolute inset-0 bg-[linear-gradient(rgba(255,255,255,0.05)_1px,transparent_1px),linear-gradient(90deg,rgba(255,255,255,0.05)_1px,transparent_1px)] bg-[size:40px_40px]" />
            <div className="absolute -top-24 -right-24 h-64 w-64 rounded-full bg-white/5 blur-3xl" />
            <div className="absolute -bottom-24 -left-24 h-64 w-64 rounded-full bg-white/5 blur-3xl" />

            <div className="relative">
              <h2 className="text-3xl font-bold text-white sm:text-4xl">
                Ready to Reduce Your Azure Spend?
              </h2>
              <p className="mx-auto mt-4 max-w-xl text-lg text-blue-100/80">
                Join FinOps teams who save thousands per month with intelligent cost optimization powered by AzCops.
              </p>
              <div className="mt-8 flex flex-col sm:flex-row items-center justify-center gap-4">
                <Button
                  size="lg"
                  onClick={isAuthenticated ? handleGoToDashboard : handleSignIn}
                  className="bg-white text-blue-700 hover:bg-blue-50 shadow-xl h-12 px-8 font-semibold"
                >
                  {isAuthenticated ? 'Go to Dashboard' : 'Get Started Free'}
                  <ArrowRight className="ml-2 h-4 w-4" />
                </Button>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ── Footer ─────────────────────────────────── */}
      <footer className="border-t py-10">
        <div className="container mx-auto flex flex-col items-center gap-4 px-6 text-center sm:flex-row sm:justify-between">
          <div className="flex items-center gap-2.5">
            <div className="flex h-6 w-6 items-center justify-center rounded-md bg-gradient-to-br from-blue-600 to-indigo-600">
              <Shield className="h-3 w-3 text-white" />
            </div>
            <span className="text-sm font-medium">AzCops</span>
            <span className="text-xs text-muted-foreground">v0.1.0</span>
          </div>
          <p className="text-sm text-muted-foreground">
            Azure Cost Optimization Platform · Built with Next.js & FastAPI
          </p>
        </div>
      </footer>
    </div>
  );
}
