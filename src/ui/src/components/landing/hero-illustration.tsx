'use client';

/**
 * Animated SVG dashboard illustration for the landing page hero section.
 * Shows a stylized preview of the AzCops dashboard with cost charts and savings cards.
 */
export function HeroIllustration() {
  return (
    <div className="relative mx-auto w-full max-w-2xl">
      {/* Glow effect behind the illustration */}
      <div className="absolute -inset-4 rounded-3xl bg-gradient-to-r from-blue-500/20 via-indigo-500/20 to-purple-500/20 blur-3xl" />

      <div className="relative rounded-2xl border border-white/10 bg-gradient-to-b from-slate-900 to-slate-950 p-1 shadow-2xl">
        {/* Browser chrome */}
        <div className="flex items-center gap-2 border-b border-white/10 px-4 py-2.5">
          <div className="flex gap-1.5">
            <div className="h-2.5 w-2.5 rounded-full bg-red-500/70" />
            <div className="h-2.5 w-2.5 rounded-full bg-yellow-500/70" />
            <div className="h-2.5 w-2.5 rounded-full bg-green-500/70" />
          </div>
          <div className="flex-1 flex justify-center">
            <div className="rounded-md bg-white/5 px-16 py-1 text-[10px] text-slate-400">
              azcops.azure.app/dashboard
            </div>
          </div>
        </div>

        {/* Dashboard content */}
        <div className="p-4 space-y-3">
          {/* KPI Row */}
          <div className="grid grid-cols-4 gap-2">
            {[
              { label: 'Monthly Spend', value: '$12,480', color: 'from-blue-500 to-blue-600' },
              { label: 'Potential Savings', value: '$3,712', color: 'from-green-500 to-emerald-600' },
              { label: 'Open Recommendations', value: '9', color: 'from-amber-500 to-orange-600' },
              { label: 'Resources', value: '247', color: 'from-purple-500 to-indigo-600' },
            ].map((kpi) => (
              <div
                key={kpi.label}
                className="rounded-lg bg-white/5 p-2.5 border border-white/5"
              >
                <p className="text-[8px] text-slate-400 mb-1">{kpi.label}</p>
                <p className={`text-sm font-bold bg-gradient-to-r ${kpi.color} bg-clip-text text-transparent`}>
                  {kpi.value}
                </p>
              </div>
            ))}
          </div>

          {/* Chart area */}
          <div className="rounded-lg bg-white/5 border border-white/5 p-3">
            <p className="text-[9px] text-slate-400 mb-2">Cost Trend — Last 30 Days</p>
            <svg viewBox="0 0 400 120" className="w-full h-auto" preserveAspectRatio="xMidYMid meet">
              <defs>
                <linearGradient id="heroChartGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#6366f1" stopOpacity="0.4" />
                  <stop offset="100%" stopColor="#6366f1" stopOpacity="0" />
                </linearGradient>
              </defs>
              {/* Grid lines */}
              {[30, 60, 90].map((y) => (
                <line key={y} x1="0" y1={y} x2="400" y2={y} stroke="rgba(255,255,255,0.05)" />
              ))}
              {/* Area fill */}
              <path
                d="M0,85 C20,80 40,72 60,75 C80,78 100,65 120,60 C140,55 160,52 180,48 C200,44 220,50 240,42 C260,34 280,38 300,30 C320,26 340,35 360,28 C380,22 390,25 400,20 L400,120 L0,120 Z"
                fill="url(#heroChartGrad)"
              >
                <animate
                  attributeName="d"
                  dur="4s"
                  repeatCount="indefinite"
                  values="
                    M0,85 C20,80 40,72 60,75 C80,78 100,65 120,60 C140,55 160,52 180,48 C200,44 220,50 240,42 C260,34 280,38 300,30 C320,26 340,35 360,28 C380,22 390,25 400,20 L400,120 L0,120 Z;
                    M0,82 C20,78 40,75 60,70 C80,74 100,68 120,63 C140,58 160,50 180,52 C200,48 220,45 240,40 C260,38 280,35 300,32 C320,30 340,28 360,25 C380,20 390,22 400,18 L400,120 L0,120 Z;
                    M0,85 C20,80 40,72 60,75 C80,78 100,65 120,60 C140,55 160,52 180,48 C200,44 220,50 240,42 C260,34 280,38 300,30 C320,26 340,35 360,28 C380,22 390,25 400,20 L400,120 L0,120 Z
                  "
                />
              </path>
              {/* Line */}
              <path
                d="M0,85 C20,80 40,72 60,75 C80,78 100,65 120,60 C140,55 160,52 180,48 C200,44 220,50 240,42 C260,34 280,38 300,30 C320,26 340,35 360,28 C380,22 390,25 400,20"
                fill="none"
                stroke="#6366f1"
                strokeWidth="2"
              >
                <animate
                  attributeName="d"
                  dur="4s"
                  repeatCount="indefinite"
                  values="
                    M0,85 C20,80 40,72 60,75 C80,78 100,65 120,60 C140,55 160,52 180,48 C200,44 220,50 240,42 C260,34 280,38 300,30 C320,26 340,35 360,28 C380,22 390,25 400,20;
                    M0,82 C20,78 40,75 60,70 C80,74 100,68 120,63 C140,58 160,50 180,52 C200,48 220,45 240,40 C260,38 280,35 300,32 C320,30 340,28 360,25 C380,20 390,22 400,18;
                    M0,85 C20,80 40,72 60,75 C80,78 100,65 120,60 C140,55 160,52 180,48 C200,44 220,50 240,42 C260,34 280,38 300,30 C320,26 340,35 360,28 C380,22 390,25 400,20
                  "
                />
              </path>
              {/* Glowing dot at the end */}
              <circle cx="400" cy="20" r="4" fill="#6366f1">
                <animate attributeName="cy" dur="4s" repeatCount="indefinite" values="20;18;20" />
                <animate attributeName="opacity" dur="2s" repeatCount="indefinite" values="1;0.5;1" />
              </circle>
              <circle cx="400" cy="20" r="8" fill="#6366f1" opacity="0.2">
                <animate attributeName="cy" dur="4s" repeatCount="indefinite" values="20;18;20" />
                <animate attributeName="r" dur="2s" repeatCount="indefinite" values="8;12;8" />
                <animate attributeName="opacity" dur="2s" repeatCount="indefinite" values="0.2;0.05;0.2" />
              </circle>
            </svg>
          </div>

          {/* Bottom row: Savings + Service breakdown */}
          <div className="grid grid-cols-5 gap-2">
            {/* Savings opportunities */}
            <div className="col-span-3 rounded-lg bg-white/5 border border-white/5 p-2.5 space-y-1.5">
              <p className="text-[9px] text-slate-400 mb-1">Top Savings Opportunities</p>
              {[
                { text: 'Purchase RI for 3 D4s_v5 VMs', savings: '$1,240', risk: 'low' },
                { text: 'Downsize vm-api-prod D8s→D4s', savings: '$520', risk: 'med' },
                { text: 'Delete 4 unattached disks', savings: '$340', risk: 'low' },
              ].map((r) => (
                <div key={r.text} className="flex items-center justify-between">
                  <span className="text-[8px] text-slate-300 truncate flex-1">{r.text}</span>
                  <div className="flex items-center gap-1.5 ml-2">
                    <span className={`text-[7px] px-1 py-0.5 rounded ${
                      r.risk === 'low' ? 'bg-green-500/20 text-green-400' : 'bg-amber-500/20 text-amber-400'
                    }`}>
                      {r.risk}
                    </span>
                    <span className="text-[9px] font-semibold text-green-400">{r.savings}</span>
                  </div>
                </div>
              ))}
            </div>

            {/* Service breakdown */}
            <div className="col-span-2 rounded-lg bg-white/5 border border-white/5 p-2.5">
              <p className="text-[9px] text-slate-400 mb-2">By Service</p>
              <div className="space-y-1.5">
                {[
                  { name: 'VMs', pct: 38, color: 'bg-blue-500' },
                  { name: 'SQL', pct: 19, color: 'bg-purple-500' },
                  { name: 'Storage', pct: 13, color: 'bg-pink-500' },
                  { name: 'AKS', pct: 8, color: 'bg-amber-500' },
                  { name: 'Other', pct: 22, color: 'bg-slate-500' },
                ].map((s) => (
                  <div key={s.name} className="flex items-center gap-1.5">
                    <span className="text-[7px] text-slate-400 w-7 text-right">{s.pct}%</span>
                    <div className="flex-1 h-1.5 rounded-full bg-white/5 overflow-hidden">
                      <div className={`h-full rounded-full ${s.color}`} style={{ width: `${s.pct}%` }} />
                    </div>
                    <span className="text-[7px] text-slate-300 w-8">{s.name}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Floating accent elements */}
      <div className="absolute -right-4 top-1/4 h-20 w-20 rounded-full bg-blue-500/10 blur-xl animate-pulse" />
      <div className="absolute -left-6 bottom-1/4 h-16 w-16 rounded-full bg-purple-500/10 blur-xl animate-pulse" style={{ animationDelay: '1s' }} />
    </div>
  );
}
