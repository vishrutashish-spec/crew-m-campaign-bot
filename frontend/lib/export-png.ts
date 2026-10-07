/**
 * Chart-to-PNG export.
 *
 * Rasterising an inline SVG is full of quiet failure modes, and each one is
 * handled here rather than hoped away:
 *
 *  1. CSS custom properties (var(--ink)) do not resolve once the SVG leaves the
 *     document, so every visual property is read with getComputedStyle on the
 *     LIVE node and written as a hard attribute on the clone.
 *  2. Web fonts are not available to the rasteriser, so Vollkorn is fetched
 *     once, base64-encoded and injected as an @font-face inside the SVG. Without
 *     this the export silently falls back to a default serif.
 *  3. SVG loaded through a blob: URL taints the canvas in some browsers, so the
 *     markup goes in as a data: URL instead.
 *  4. An SVG with no explicit width/height rasterises at zero in Firefox, so
 *     both are set from the measured box.
 *  5. Charts are transparent by default; a white plate is painted underneath so
 *     the PNG is usable on a slide.
 *
 * Exports the rendered chart image only. It carries no row-level data and no
 * identifiers: the same aggregate figures already visible on screen.
 */

const FONT_URLS = [
  { url: "/fonts/Vollkorn-Regular.ttf", weight: 400 },
  { url: "/fonts/Vollkorn-Bold.ttf", weight: 700 },
];

let fontCssPromise: Promise<string> | null = null;

/** Fetch + base64 the fonts once per page load. */
function getFontCss(): Promise<string> {
  if (fontCssPromise) return fontCssPromise;

  fontCssPromise = (async () => {
    const faces = await Promise.all(
      FONT_URLS.map(async ({ url, weight }) => {
        try {
          const res = await fetch(url);
          if (!res.ok) return "";
          const buf = await res.arrayBuffer();
          // Chunked conversion: a spread on a large array blows the call stack.
          const bytes = new Uint8Array(buf);
          let binary = "";
          const CHUNK = 0x8000;
          for (let i = 0; i < bytes.length; i += CHUNK) {
            binary += String.fromCharCode(...bytes.subarray(i, i + CHUNK));
          }
          const b64 = btoa(binary);
          return `@font-face{font-family:'Vollkorn';font-style:normal;font-weight:${weight};src:url(data:font/ttf;base64,${b64}) format('truetype');}`;
        } catch {
          return "";
        }
      })
    );
    return faces.join("");
  })();

  return fontCssPromise;
}

/** Visual properties that must survive the trip out of the document. */
const CARRIED = [
  "fill",
  "fill-opacity",
  "stroke",
  "stroke-width",
  "stroke-dasharray",
  "stroke-opacity",
  "stroke-linecap",
  "opacity",
  "font-family",
  "font-size",
  "font-weight",
  "font-style",
  "text-anchor",
  "dominant-baseline",
  "letter-spacing",
] as const;

/**
 * Copy computed styles from the live tree onto the clone, node for node.
 * Both trees have identical structure, so a parallel walk keeps them aligned.
 */
function inlineStyles(live: Element, clone: Element) {
  const computed = window.getComputedStyle(live);
  const decls: string[] = [];

  for (const prop of CARRIED) {
    const value = computed.getPropertyValue(prop);
    if (!value || value === "none" && prop !== "fill") continue;
    if (value === "normal" || value === "auto") continue;
    decls.push(`${prop}:${value}`);
  }
  if (decls.length) {
    const existing = clone.getAttribute("style");
    clone.setAttribute("style", existing ? `${existing};${decls.join(";")}` : decls.join(";"));
  }

  const liveKids = live.children;
  const cloneKids = clone.children;
  for (let i = 0; i < liveKids.length && i < cloneKids.length; i++) {
    inlineStyles(liveKids[i], cloneKids[i]);
  }
}

export interface ExportOptions {
  /** Filename without extension. */
  filename?: string;
  /** Resolution multiplier. 2 gives a crisp result on retina and in slides. */
  scale?: number;
  /** Plate colour painted under the chart. */
  background?: string;
  /** Optional caption burned into the footer of the image. */
  caption?: string;
}

/**
 * Rasterise an <svg> element to PNG and hand it to the browser as a download.
 * Throws with a readable message so the caller can surface a real failure
 * instead of a silently dead button.
 */
export async function exportSvgToPng(
  svg: SVGSVGElement,
  options: ExportOptions = {}
): Promise<void> {
  // Defaults follow the active theme: a dark-mode chart exports onto the
  // dark card surface with the dark tick colour, so light text never lands
  // on a white plate.
  const rootStyle = window.getComputedStyle(document.documentElement);
  const themeBg = rootStyle.getPropertyValue("--card").trim() || "#ffffff";
  const themeTick = rootStyle.getPropertyValue("--tick").trim() || "#565064";

  const {
    filename = "chart",
    scale = 2,
    background = themeBg,
    caption,
  } = options;

  const box = svg.getBoundingClientRect();
  const width = Math.max(1, Math.ceil(box.width || svg.clientWidth || 800));
  const height = Math.max(1, Math.ceil(box.height || svg.clientHeight || 400));

  const pad = 20;
  const footer = caption ? 26 : 0;
  const outW = width + pad * 2;
  const outH = height + pad * 2 + footer;

  // --- Build a self-contained SVG -----------------------------------------
  const clone = svg.cloneNode(true) as SVGSVGElement;
  inlineStyles(svg, clone);

  clone.setAttribute("xmlns", "http://www.w3.org/2000/svg");
  clone.setAttribute("width", String(width));
  clone.setAttribute("height", String(height));
  if (!clone.getAttribute("viewBox")) {
    clone.setAttribute("viewBox", `0 0 ${width} ${height}`);
  }

  const fontCss = await getFontCss();
  if (fontCss) {
    const style = document.createElementNS("http://www.w3.org/2000/svg", "style");
    style.textContent = fontCss;
    clone.insertBefore(style, clone.firstChild);
  }

  const markup = new XMLSerializer().serializeToString(clone);
  // encodeURIComponent handles the non-ASCII the base64 font would otherwise break.
  const dataUrl = `data:image/svg+xml;charset=utf-8,${encodeURIComponent(markup)}`;

  // --- Rasterise ----------------------------------------------------------
  const img = new Image();
  img.decoding = "sync";

  await new Promise<void>((resolve, reject) => {
    img.onload = () => resolve();
    img.onerror = () => reject(new Error("Could not rasterise the chart SVG"));
    img.src = dataUrl;
  });

  // decode() settles the race where onload fires before the font is applied.
  if (typeof img.decode === "function") {
    try {
      await img.decode();
    } catch {
      /* Safari rejects decode() on data URLs it has already loaded: harmless. */
    }
  }

  const canvas = document.createElement("canvas");
  canvas.width = Math.ceil(outW * scale);
  canvas.height = Math.ceil(outH * scale);

  const ctx = canvas.getContext("2d");
  if (!ctx) throw new Error("Canvas 2D context unavailable");

  ctx.scale(scale, scale);
  ctx.fillStyle = background;
  ctx.fillRect(0, 0, outW, outH);
  ctx.drawImage(img, pad, pad, width, height);

  if (caption) {
    ctx.fillStyle = themeTick;
    ctx.font = "11px Vollkorn, Georgia, serif";
    ctx.textBaseline = "middle";
    ctx.fillText(caption, pad, pad + height + footer / 2 + 2);
  }

  const blob = await new Promise<Blob | null>((resolve) =>
    canvas.toBlob(resolve, "image/png")
  );
  if (!blob) throw new Error("Could not encode the PNG");

  const href = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = href;
  a.download = `${filename.replace(/[^a-z0-9-_]+/gi, "-").toLowerCase()}.png`;
  document.body.appendChild(a);
  a.click();
  a.remove();
  // Revoke on the next frame: revoking synchronously cancels the download
  // in Safari.
  requestAnimationFrame(() => URL.revokeObjectURL(href));
}

/** Find the chart SVG inside a wrapper element. */
export function findChartSvg(container: HTMLElement | null): SVGSVGElement | null {
  if (!container) return null;
  return (
    container.querySelector<SVGSVGElement>(".recharts-surface") ??
    container.querySelector<SVGSVGElement>("svg")
  );
}
