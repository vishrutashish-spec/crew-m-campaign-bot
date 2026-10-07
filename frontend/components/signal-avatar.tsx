"use client";

/**
 * SIGNAL's avatar: the supplied pixel portrait, redrawn as a deterministic
 * SVG pixel grid so it scales cleanly and needs no raster asset.
 *
 * Grid is 16 wide by 18 tall. One character per pixel:
 *   .  transparent      B  backdrop blue-grey
 *   K  hair and beard   S  skin        H  glasses frame / lens
 *   L  skin highlight   T  shirt
 */

const PALETTE: Record<string, string> = {
  B: "#6B7F96",
  K: "#141414",
  S: "#D9A884",
  L: "#E6BC9A",
  H: "#0B0B0B",
  T: "#2B2B31",
};

// The portrait: quiffed dark hair, glasses, full beard, shoulders.
const GRID = [
  "BBBBBBBBBBBBBBBB",
  "BBBBBKKKKKKBBBBB",
  "BBBKKKKKKKKKBBBB",
  "BBKKKKKKKKKKKBBB",
  "BBKKKSSSSSSKKBBB",
  "BBKKSSSSSSSSKBBB",
  "BBKSSSLLSSLLSKBB",
  "BBKSHHHSSHHHSKBB",
  "BBKSHHHSSHHHSKBB",
  "BBKSSSSSSSSSSKBB",
  "BBKSSSSLLSSSSKBB",
  "BBKKSSSSSSSSKKBB",
  "BBKKKSSSSSSKKKBB",
  "BBBKKKKSSKKKKBBB",
  "BBBBKKKKKKKKBBBB",
  "BBBBBKKKKKKBBBBB",
  "BBBBBBSSSSBBBBBB",
  "BBBBTTTTTTTTTBBB",
];

export function SignalAvatar({ size = 44, rounded = true, live = false, thinking = false }: {
  size?: number; rounded?: boolean; live?: boolean; thinking?: boolean;
}) {
  const inner = (
    <SignalAvatarSvg size={size} rounded={rounded} />
  );
  if (!live) return inner;
  return (
    <span className="avatar-wrap inline-block" style={{ width: size, height: size }}>
      <span className={`avatar-live inline-block ${thinking ? "avatar-thinking" : ""}`}>
        {inner}
      </span>
      <span className="avatar-scan" aria-hidden />
    </span>
  );
}

function SignalAvatarSvg({ size, rounded }: { size: number; rounded: boolean }) {
  const cols = GRID[0].length;
  const rows = GRID.length;
  return (
    <svg
      width={size}
      height={size}
      viewBox={`0 0 ${cols} ${rows}`}
      shapeRendering="crispEdges"
      aria-label="SIGNAL"
      style={{ display: "block", borderRadius: rounded ? size * 0.22 : 0 }}
    >
      {GRID.map((row, y) =>
        row.split("").map((ch, x) => {
          const fill = PALETTE[ch];
          if (!fill) return null;
          return <rect key={`${x}-${y}`} x={x} y={y} width={1} height={1} fill={fill} />;
        })
      )}
    </svg>
  );
}

/** Avatar with the live ring, for the chat header. */
export function SignalBadge({ size = 52 }: { size?: number }) {
  return (
    <span className="relative inline-flex flex-shrink-0">
      <span
        className="absolute -inset-[3px] rounded-[14px]"
        style={{
          background: "linear-gradient(135deg, #22C8D6, #3B82F6, #4FE3C1)",
          padding: 2,
        }}
        aria-hidden
      />
      <span className="relative rounded-[12px] overflow-hidden"
        style={{ background: "var(--card)", padding: 2 }}>
        <SignalAvatar size={size} />
      </span>
      <span
        className="absolute -bottom-0.5 -right-0.5 w-3 h-3 rounded-full border-2 live-dot"
        style={{ background: "#4FE3C1", borderColor: "var(--card)" }}
        aria-hidden
      />
    </span>
  );
}
