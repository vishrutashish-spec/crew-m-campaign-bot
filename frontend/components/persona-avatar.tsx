"use client";

const PERSONA_ICONS: Record<string, { icon: (size: number) => React.ReactNode; bg: string }> = {
  dormant: {
    bg: "oklch(0.94 0.02 280)",
    icon: (s) => (
      <svg width={s * 0.55} height={s * 0.55} viewBox="0 0 24 24" fill="none" stroke="oklch(0.45 0.12 280)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <path d="M12 3a6 6 0 0 0 9 9 9 9 0 1 1-9-9Z" />
      </svg>
    ),
  },
  active: {
    bg: "oklch(0.94 0.03 155)",
    icon: (s) => (
      <svg width={s * 0.55} height={s * 0.55} viewBox="0 0 24 24" fill="none" stroke="oklch(0.45 0.15 155)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <path d="m13 2-2 8h6L11 22l2-8H7z" />
      </svg>
    ),
  },
  th_engaged: {
    bg: "oklch(0.94 0.03 320)",
    icon: (s) => (
      <svg width={s * 0.55} height={s * 0.55} viewBox="0 0 24 24" fill="none" stroke="oklch(0.45 0.12 320)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <path d="M22 12h-4l-3 9L9 3l-3 9H2" />
      </svg>
    ),
  },
  hc_engaged: {
    bg: "oklch(0.94 0.03 15)",
    icon: (s) => (
      <svg width={s * 0.55} height={s * 0.55} viewBox="0 0 24 24" fill="none" stroke="oklch(0.55 0.18 15)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <path d="M9 12h6" /><path d="M12 9v6" />
        <path d="M3 7V5a2 2 0 0 1 2-2h2" /><path d="M17 3h2a2 2 0 0 1 2 2v2" />
        <path d="M21 17v2a2 2 0 0 1-2 2h-2" /><path d="M7 21H5a2 2 0 0 1-2-2v-2" />
      </svg>
    ),
  },
  dual_product: {
    bg: "oklch(0.94 0.03 65)",
    icon: (s) => (
      <svg width={s * 0.55} height={s * 0.55} viewBox="0 0 24 24" fill="none" stroke="oklch(0.55 0.15 65)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2" />
      </svg>
    ),
  },
  no_app: {
    bg: "oklch(0.94 0.01 200)",
    icon: (s) => (
      <svg width={s * 0.55} height={s * 0.55} viewBox="0 0 24 24" fill="none" stroke="oklch(0.45 0.1 200)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <rect x="5" y="2" width="14" height="20" rx="2" ry="2" /><line x1="12" y1="18" x2="12.01" y2="18" />
        <line x1="2" y1="2" x2="22" y2="22" />
      </svg>
    ),
  },
  pre_activation: {
    bg: "oklch(0.95 0.03 100)",
    icon: (s) => (
      <svg width={s * 0.55} height={s * 0.55} viewBox="0 0 24 24" fill="none" stroke="oklch(0.5 0.12 100)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <path d="M4.5 16.5c-1.5 1.26-2 5-2 5s3.74-.5 5-2c.71-.84.7-2.13-.09-2.91a2.18 2.18 0 0 0-2.91-.09z" />
        <path d="m12 15-3-3a22 22 0 0 1 2-3.95A12.88 12.88 0 0 1 22 2c0 2.72-.78 7.5-6 11a22.35 22.35 0 0 1-4 2z" />
        <path d="M9 12H4s.55-3.03 2-4c1.62-1.08 5 0 5 0" />
        <path d="M12 15v5s3.03-.55 4-2c1.08-1.62 0-5 0-5" />
      </svg>
    ),
  },
  low_app: {
    bg: "oklch(0.95 0.02 340)",
    icon: (s) => (
      <svg width={s * 0.55} height={s * 0.55} viewBox="0 0 24 24" fill="none" stroke="oklch(0.45 0.12 340)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <circle cx="12" cy="12" r="10" /><line x1="12" y1="8" x2="12" y2="12" /><line x1="12" y1="16" x2="12.01" y2="16" />
      </svg>
    ),
  },
};

function getPersonaType(name: string): string {
  const lower = name.toLowerCase();
  if (lower.includes("dormant")) return "dormant";
  if (lower.includes("dual-product")) return "dual_product";
  if (lower.includes("th-engaged")) return "th_engaged";
  if (lower.includes("hc-engaged")) return "hc_engaged";
  if (lower.includes("no-app")) return "no_app";
  if (lower.includes("pre-activation")) return "pre_activation";
  if (lower.includes("low-app")) return "low_app";
  if (lower.includes("active")) return "active";
  return "pre_activation";
}

export function PersonaAvatar({ personaId, personaName, size = 36 }: { personaId: number; personaName?: string; size?: number }) {
  const type = personaName ? getPersonaType(personaName) : Object.keys(PERSONA_ICONS)[personaId % Object.keys(PERSONA_ICONS).length];
  const config = PERSONA_ICONS[type] || PERSONA_ICONS.pre_activation;

  return (
    <div
      className="rounded-lg flex items-center justify-center flex-shrink-0"
      style={{ width: size, height: size, background: config.bg }}
    >
      {config.icon(size)}
    </div>
  );
}
