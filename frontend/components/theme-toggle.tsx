"use client";

/**
 * Theme toggle: a metallic pill whose knob slides between sun and moon.
 *
 * The theme itself is applied before hydration by the inline script in
 * layout.tsx (reads localStorage, falls back to the OS preference), so this
 * component only has to mirror and flip the class that is already on <html>.
 * That split is what prevents both the flash of the wrong theme and a
 * hydration mismatch.
 */

import { useEffect, useState } from "react";
import { Sun, Moon } from "lucide-react";

export function ThemeToggle() {
  // Render a neutral state on the server; adopt the real one after mount.
  const [dark, setDark] = useState<boolean | null>(null);

  useEffect(() => {
    setDark(document.documentElement.classList.contains("dark"));
  }, []);

  function flip() {
    const next = !(dark ?? false);
    setDark(next);
    document.documentElement.classList.toggle("dark", next);
    try {
      localStorage.setItem("crewm-theme", next ? "dark" : "light");
    } catch {
      /* private-mode storage failures are fine to ignore */
    }
  }

  return (
    <button
      className="theme-pill"
      data-dark={dark === true}
      onClick={flip}
      aria-label={dark ? "Switch to light mode" : "Switch to dark mode"}
      title={dark ? "Switch to light mode" : "Switch to dark mode"}
    >
      <span className="hint hint-l" aria-hidden>
        <Sun className="w-3.5 h-3.5" strokeWidth={2} />
      </span>
      <span className="hint hint-r" aria-hidden>
        <Moon className="w-3.5 h-3.5" strokeWidth={2} />
      </span>
      <span className={`knob ${dark ? "metal-ink" : "metal-cyan"}`}>
        {dark ? (
          <Moon className="w-3 h-3 text-[color:var(--sand)]" strokeWidth={2.4} />
        ) : (
          <Sun className="w-3 h-3 text-white" strokeWidth={2.4} />
        )}
      </span>
    </button>
  );
}
