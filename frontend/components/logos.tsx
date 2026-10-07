"use client";

/**
 * Brand marks.
 *
 * CrewMMark is the product's own mark: a geometric M cut from the plum
 * gradient, a metallic cyan signal node above its valley (the "intelligence"
 * dot, in the interaction colour by design), and three baseline ticks that
 * read as a chart axis. Deterministic SVG, no raster assets.
 *
 * PlumWordmark / PlumGlyph are taken from the official Plum_Logo_0.svg the
 * team supplied, colour #FF4052 as shipped.
 *
 * WhatsAppGlyph and GmailGlyph are the real brand glyphs, used to identify
 * channels everywhere, including inside charts via ChannelTickX / ChannelTickY.
 * All are pure paths with hard fills, so they survive the PNG exporter.
 */

/* ------------------------------------------------------------------ Crew M */

/*
 * Wordmark v5, locked by feedback: no custom letterforms, no animation, no
 * pointy geometry. "Crew M" set in Vollkorn Bold (the product's own serif,
 * broad and round) as SVG text, filled with a static cyan-spectrum gradient.
 * One small seafoam node after the M is the only ornament, and it does not
 * move. Quiet confidence instead of choreography.
 */

export function CrewMWordmark({ width = 172 }: { width?: number }) {
  const height = Math.round(width * (46 / 168));
  return (
    <svg width={width} height={height} viewBox="0 0 168 46" fill="none"
      aria-label="Crew M" style={{ display: "block", overflow: "visible" }}>
      <defs>
        <linearGradient id="wm-g" x1="0" y1="8" x2="168" y2="38" gradientUnits="userSpaceOnUse">
          <stop offset="0" stopColor="#0E9AA7" />
          <stop offset="0.42" stopColor="#22C8D6" />
          <stop offset="0.72" stopColor="#4FE3C1" />
          <stop offset="1" stopColor="#3B82F6" />
        </linearGradient>
      </defs>
      {/* Brigold: tall condensed sans, static cyan-spectrum gradient, no motion */}
      <text x="0" y="34" fontFamily="Brigold, Vollkorn, Georgia, serif"
        fontSize="38" letterSpacing="1.5" fill="url(#wm-g)">
        Crew M
      </text>
    </svg>
  );
}

/** Compact glyph: a broad, rounded wave with the node. Nothing pointy. */
export function CrewMMark({ size = 30 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 32 32" fill="none" aria-label="Crew M"
      style={{ overflow: "visible" }}>
      <defs>
        <linearGradient id="wm-s" x1="0" y1="0" x2="32" y2="0" gradientUnits="userSpaceOnUse">
          <stop offset="0" stopColor="#22C8D6" />
          <stop offset="1" stopColor="#3B82F6" />
        </linearGradient>
      </defs>
      <path d="M3 21 C8 9, 12 9, 16 17 S24 27 29 13" stroke="url(#wm-s)"
        strokeWidth="4.6" strokeLinecap="round" fill="none" />
      <circle cx="29" cy="7.5" r="2" fill="#4FE3C1" />
    </svg>
  );
}

export function CrewMLogo({ compact = false }: { compact?: boolean }) {
  return (
    <span className="inline-block">
      <CrewMWordmark width={compact ? 116 : 168} />
      {!compact && (
        <span className="label-mono block mt-1.5 !text-[9px] !tracking-[0.22em]">
          Campaign intelligence
        </span>
      )}
    </span>
  );
}

/* -------------------------------------------------------------------- Plum */

const PLUM_P =
  "M50.6253 32.5297C50.6253 37.9889 49.9994 42.3475 48.7475 45.6054C47.4956 48.8633 45.7483 51.1839 43.5054 52.5673C41.2607 53.9471 38.5432 54.6379 35.3528 54.6397C31.3363 54.6397 27.8995 53.7121 25.0424 51.857C22.3738 50.1256 20.4262 47.4357 19.1997 43.7874C19.1282 43.5721 18.9778 43.39 18.7772 43.2761C18.5767 43.1621 18.3401 43.1243 18.1127 43.1699L17.966 43.2017C17.7333 43.2492 17.5278 43.3808 17.3906 43.5701C17.2535 43.7594 17.195 43.9923 17.2268 44.222L18.8736 56.2722C18.8764 56.3127 18.8764 56.3535 18.8736 56.3941V60.0274C18.8736 61.3525 18.1508 62.2058 16.6425 62.2058H2.94342C2.64743 62.2158 2.3525 62.1663 2.07699 62.0603C1.80148 61.9543 1.55129 61.7942 1.34199 61.5898C1.1327 61.3855 0.968784 61.1413 0.860455 60.8725C0.752127 60.6037 0.701704 60.316 0.712326 60.0274V13.2526C0.707172 12.9655 0.761361 12.6803 0.871659 12.4141C0.981958 12.1478 1.14611 11.906 1.35432 11.7029C1.56253 11.4999 1.81054 11.3398 2.08356 11.2322C2.35658 11.1247 2.64901 11.0718 2.94342 11.0769H16.1751C17.4306 11.0769 18.4443 11.8719 18.235 13.4222L16.8762 24.301C16.847 24.5359 16.9118 24.7728 17.057 24.9623C17.2023 25.1518 17.4169 25.2795 17.6562 25.3187L17.7594 25.3372C17.9988 25.3785 18.2453 25.3282 18.4477 25.197C18.6501 25.0657 18.7929 24.8635 18.8465 24.6323C19.6726 21.0758 20.7424 18.2561 22.0559 16.1731C23.4744 13.9293 25.2164 12.3392 27.2817 11.4028C29.347 10.4664 31.8834 10 34.8908 10.0036C45.404 10.0053 50.6489 17.514 50.6253 32.5297ZM30.7873 40.4058C31.6932 38.9783 32.1461 36.7098 32.1461 33.6003C32.1461 30.5845 31.7095 28.4317 30.8362 27.1419C29.963 25.8522 28.5272 25.2073 26.5289 25.2073C25.2592 25.2054 24.0118 25.5328 22.9146 26.1561C21.7206 26.8537 20.7509 27.8636 20.1155 29.0712C19.3909 30.3716 18.9778 31.9784 18.8763 33.8918V38.9271C18.8771 39.0786 18.9159 39.2276 18.9893 39.3611C19.0627 39.4946 19.1686 39.6085 19.2976 39.693C20.5319 40.5394 21.8437 41.2731 23.2162 41.8846C24.3211 42.3356 25.5079 42.5645 26.7056 42.5577C28.5299 42.5507 29.8905 41.8334 30.7873 40.4058Z";

/** The Plum 'p' from the official logo, on a white tile so it reads at 16px. */
export function PlumGlyph({ size = 18 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 64 64" aria-label="Plum">
      <rect x="1" y="1" width="62" height="62" rx="15" fill="#FFFFFF" stroke="#EBE7EE" strokeWidth="2" />
      <g transform="translate(10.5, -3.5) scale(0.86)">
        <path d={PLUM_P} fill="#FF4052" />
      </g>
    </svg>
  );
}

export function PlumWordmark({ height = 16 }: { height?: number }) {
  return (
    <svg height={height} viewBox="0 0 204 63" aria-label="Plum" style={{ display: "block" }}>
      <path d={PLUM_P} fill="#FF4052" />
      <path d="M71.7077 2.05849V51.3906C71.711 51.6774 71.6555 51.9618 71.5446 52.2274C71.4337 52.493 71.2695 52.7343 71.0617 52.9372C70.8539 53.14 70.6067 53.3004 70.3345 53.4089C70.0623 53.5175 69.7707 53.5719 69.4766 53.569H55.946C55.6519 53.5719 55.3601 53.5175 55.0878 53.409C54.8154 53.3005 54.568 53.1402 54.36 52.9373C54.152 52.7345 53.9876 52.4932 53.8763 52.2276C53.7651 51.962 53.7093 51.6775 53.7122 51.3906V4.71656C53.6935 4.1601 53.881 3.61569 54.2403 3.18303C54.5997 2.75037 55.1068 2.4584 55.6688 2.3606L69.387 0.0947402C70.7349 -0.11727 71.7077 0.844727 71.7077 2.05849Z" fill="#FF4052" />
      <path d="M86.3799 52.2546C82.838 50.6185 80.193 48.2644 78.4447 45.192C76.6964 42.1196 75.8232 38.4174 75.825 34.0853V13.2526C75.8171 12.9648 75.8695 12.6785 75.9788 12.411C76.0882 12.1436 76.2522 11.9007 76.461 11.6971C76.6697 11.4935 76.9188 11.3335 77.1931 11.2269C77.4673 11.1202 77.761 11.0692 78.0561 11.0769H91.7633C92.0575 11.0733 92.3494 11.1271 92.6218 11.2352C92.8943 11.3432 93.1419 11.5033 93.35 11.706C93.5582 11.9088 93.7226 12.15 93.8338 12.4156C93.9449 12.6812 94.0004 12.9658 93.9972 13.2526V33.7037C93.9972 35.7319 94.4691 37.1259 95.413 37.8856C96.3569 38.6453 97.7501 39.0251 99.5926 39.0251C101.435 39.0251 102.835 38.6276 103.791 37.8326C104.748 37.0375 105.226 35.6612 105.226 33.7037V13.2526C105.218 12.9648 105.271 12.6785 105.38 12.411C105.489 12.1436 105.653 11.9007 105.862 11.6971C106.071 11.4935 106.32 11.3335 106.594 11.2269C106.868 11.1202 107.162 11.0692 107.457 11.0769H121.167C122.439 11.0769 123.398 11.8719 123.398 13.0035V34.0853C123.398 38.4156 122.525 42.1178 120.778 45.192C119.032 48.2661 116.387 50.6203 112.843 52.2546C109.3 53.8888 104.883 54.7068 99.5926 54.7086C94.3024 54.7103 89.8982 53.8923 86.3799 52.2546Z" fill="#FF4052" />
      <path d="M199.974 15.2561C202.465 18.7596 203.711 24.3337 203.711 31.9785V51.3907C203.719 51.6787 203.667 51.9653 203.558 52.2331C203.448 52.5008 203.284 52.7441 203.076 52.9479C202.867 53.1518 202.618 53.312 202.343 53.4188C202.069 53.5256 201.775 53.5767 201.479 53.5691H187.734C186.503 53.5691 185.503 52.7899 185.503 51.3907V32.9802C185.503 30.24 185.09 28.2824 184.264 27.1075C183.438 25.9326 182.209 25.3452 180.579 25.3452C178.572 25.3452 177.096 26.0068 176.152 27.3301C175.208 28.6534 174.712 30.7435 174.663 33.6003V51.3907C174.671 51.6787 174.619 51.9653 174.51 52.2331C174.401 52.5008 174.237 52.7441 174.028 52.9479C173.819 53.1518 173.57 53.312 173.295 53.4188C173.021 53.5256 172.727 53.5767 172.432 53.5691H158.757C158.462 53.5767 158.168 53.5256 157.893 53.4188C157.619 53.312 157.37 53.1518 157.161 52.9479C156.952 52.7441 156.788 52.5008 156.679 52.2331C156.57 51.9653 156.518 51.6787 156.526 51.3907V32.9802C156.526 30.2612 156.125 28.3089 155.322 27.1234C154.52 25.9379 153.291 25.3452 151.637 25.3452C150.806 25.3258 149.982 25.5024 149.236 25.86C148.49 26.2175 147.844 26.7455 147.352 27.399C146.265 28.7718 145.709 30.8036 145.686 33.4943V51.388C145.686 52.6627 144.824 53.5664 143.455 53.5664H129.745C129.449 53.5741 129.155 53.523 128.881 53.4162C128.607 53.3094 128.357 53.1492 128.149 52.9453C127.94 52.7414 127.776 52.4982 127.667 52.2304C127.557 51.9627 127.505 51.676 127.514 51.388V13.2526C127.501 12.9637 127.551 12.6755 127.658 12.4061C127.766 12.1367 127.93 11.892 128.14 11.6875C128.349 11.483 128.6 11.3232 128.877 11.2181C129.153 11.113 129.448 11.0649 129.745 11.0769H142.99C144.327 11.0769 145.265 11.75 145.118 12.9611L143.925 23.3443C143.9 23.5642 143.957 23.7853 144.086 23.9674C144.215 24.1494 144.406 24.2801 144.626 24.3355C144.751 24.3671 144.881 24.3733 145.008 24.3538C145.135 24.3343 145.257 24.2895 145.366 24.2222C145.475 24.1548 145.568 24.0664 145.641 23.9623C145.713 23.8583 145.762 23.7408 145.786 23.6173C146.433 20.347 147.295 17.7508 148.371 15.8286C149.55 13.7191 151.061 12.2217 152.904 11.3366C154.746 10.4515 157.084 10.0098 159.917 10.0115C163.36 10.0115 166.188 11.1749 168.402 13.5018C170.483 15.6943 171.731 19.0653 172.144 23.6147C172.167 23.8433 172.276 24.0554 172.451 24.2093C172.626 24.3632 172.854 24.4479 173.089 24.4468H173.274C173.491 24.4474 173.702 24.3746 173.871 24.2407C174.039 24.1069 174.155 23.9203 174.198 23.7127C174.894 20.3559 175.825 17.7057 176.992 15.7623C178.244 13.6793 179.838 12.1997 181.775 11.3234C183.711 10.447 186.18 10.0054 189.18 9.99829C193.885 10.0036 197.483 11.7562 199.974 15.2561Z" fill="#FF4052" />
    </svg>
  );
}

/* ---------------------------------------------------------------- WhatsApp */

const WA_PATH =
  "M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347m-5.421 7.403h-.004a9.87 9.87 0 01-5.031-1.378l-.361-.214-3.741.982.998-3.648-.235-.374a9.86 9.86 0 01-1.51-5.26c.001-5.45 4.436-9.884 9.888-9.884 2.64 0 5.122 1.03 6.988 2.898a9.825 9.825 0 012.893 6.994c-.003 5.45-4.437 9.884-9.885 9.884m8.413-18.297A11.815 11.815 0 0012.05 0C5.495 0 .16 5.335.157 11.892c0 2.096.547 4.142 1.588 5.945L.057 24l6.305-1.654a11.882 11.882 0 005.683 1.448h.005c6.554 0 11.89-5.335 11.893-11.893a11.821 11.821 0 00-3.48-8.413z";

export function WhatsAppGlyph({ size = 18 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" aria-label="WhatsApp">
      <path d={WA_PATH} fill="#25D366" fillRule="evenodd" clipRule="evenodd" />
    </svg>
  );
}

/* ------------------------------------------------------------------- Gmail */

export function GmailGlyph({ size = 18 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" aria-label="Gmail">
      <path fill="#4285F4" d="M1.636 20.727h3.819V11.73L0 7.636v11.455c0 .904.732 1.636 1.636 1.636z" />
      <path fill="#34A853" d="M18.545 20.727h3.819c.905 0 1.636-.732 1.636-1.636V7.636l-5.455 4.094z" />
      <path fill="#FBBC04" d="M18.545 4.638v7.093L24 7.636V5.457c0-2.023-2.309-3.178-3.927-1.964z" />
      <path fill="#EA4335" d="M5.455 11.73V4.638L12 9.548l6.545-4.91v7.093L12 16.64z" />
      <path fill="#C5221F" d="M0 5.457v2.18l5.455 4.092V4.638L3.927 3.493C2.309 2.28 0 3.434 0 5.457z" />
    </svg>
  );
}

/* --------------------------------------------------------- channel helpers */

export const CHANNEL_KEY_BY_LABEL: Record<string, string> = {
  WhatsApp: "whatsapp", Email: "email", Push: "push",
  whatsapp: "whatsapp", email: "email", push: "push",
  "Push (real)": "push", "Push, deliverable": "push",
};

export function ChannelGlyph({ channel, size = 18 }: { channel: string; size?: number }) {
  const key = CHANNEL_KEY_BY_LABEL[channel] ?? channel;
  if (key === "whatsapp") return <WhatsAppGlyph size={size} />;
  if (key === "email") return <GmailGlyph size={size} />;
  return <PlumGlyph size={size} />;
}

/** Logo + name, for legends, option rows and table headers. */
export function ChannelTag({ channel, size = 16, className = "" }: {
  channel: string; size?: number; className?: string;
}) {
  const key = CHANNEL_KEY_BY_LABEL[channel] ?? channel;
  const name = key === "whatsapp" ? "WhatsApp" : key === "email" ? "Gmail" : "Plum push";
  return (
    <span className={`inline-flex items-center gap-1.5 ${className}`}>
      <ChannelGlyph channel={key} size={size} />
      <span>{name}</span>
    </span>
  );
}

/* ----------------------------------------------- recharts axis tick logos */

interface TickProps {
  x?: number; y?: number;
  payload?: { value?: string | number };
}

/** Bottom axis: logo above the channel name. Nested svg keeps the glyph
    inside the chart's own SVG, so the PNG exporter carries it for free. */
export function ChannelTickX({ x = 0, y = 0, payload }: TickProps) {
  const label = String(payload?.value ?? "");
  const key = CHANNEL_KEY_BY_LABEL[label] ?? label.toLowerCase();
  return (
    <g transform={`translate(${x},${y})`}>
      <svg x={-9} y={5} width={18} height={18} viewBox="0 0 24 24">
        {key === "whatsapp" ? (
          <path d={WA_PATH} fill="#25D366" fillRule="evenodd" clipRule="evenodd" />
        ) : key === "email" ? (
          <>
            <path fill="#4285F4" d="M1.636 20.727h3.819V11.73L0 7.636v11.455c0 .904.732 1.636 1.636 1.636z" />
            <path fill="#34A853" d="M18.545 20.727h3.819c.905 0 1.636-.732 1.636-1.636V7.636l-5.455 4.094z" />
            <path fill="#FBBC04" d="M18.545 4.638v7.093L24 7.636V5.457c0-2.023-2.309-3.178-3.927-1.964z" />
            <path fill="#EA4335" d="M5.455 11.73V4.638L12 9.548l6.545-4.91v7.093L12 16.64z" />
            <path fill="#C5221F" d="M0 5.457v2.18l5.455 4.092V4.638L3.927 3.493C2.309 2.28 0 3.434 0 5.457z" />
          </>
        ) : (
          <g transform="translate(4.2,-1.2) scale(0.32)">
            <path d={PLUM_P} fill="#FF4052" />
          </g>
        )}
      </svg>
      <text y={38} textAnchor="middle" fontSize={11} fill="var(--tick)"
        fontFamily="Vollkorn, Georgia, serif">
        {label}
      </text>
    </g>
  );
}

/** Left axis: logo beside the channel name. */
export function ChannelTickY({ x = 0, y = 0, payload }: TickProps) {
  const label = String(payload?.value ?? "");
  const key = CHANNEL_KEY_BY_LABEL[label] ?? label.toLowerCase();
  return (
    <g transform={`translate(${x},${y})`}>
      <svg x={-86} y={-9} width={18} height={18} viewBox="0 0 24 24">
        {key === "whatsapp" ? (
          <path d={WA_PATH} fill="#25D366" fillRule="evenodd" clipRule="evenodd" />
        ) : key === "email" ? (
          <>
            <path fill="#4285F4" d="M1.636 20.727h3.819V11.73L0 7.636v11.455c0 .904.732 1.636 1.636 1.636z" />
            <path fill="#34A853" d="M18.545 20.727h3.819c.905 0 1.636-.732 1.636-1.636V7.636l-5.455 4.094z" />
            <path fill="#FBBC04" d="M18.545 4.638v7.093L24 7.636V5.457c0-2.023-2.309-3.178-3.927-1.964z" />
            <path fill="#EA4335" d="M5.455 11.73V4.638L12 9.548l6.545-4.91v7.093L12 16.64z" />
            <path fill="#C5221F" d="M0 5.457v2.18l5.455 4.092V4.638L3.927 3.493C2.309 2.28 0 3.434 0 5.457z" />
          </>
        ) : (
          <g transform="translate(4.2,-1.2) scale(0.32)">
            <path d={PLUM_P} fill="#FF4052" />
          </g>
        )}
      </svg>
      <text x={-62} y={4} textAnchor="start" fontSize={11} fill="var(--tick)"
        fontFamily="Vollkorn, Georgia, serif">
        {label}
      </text>
    </g>
  );
}
