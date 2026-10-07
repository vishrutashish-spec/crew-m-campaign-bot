"use client";

/**
 * Floating SIGNAL launcher.
 *
 * A persistent avatar button; clicking it docks the full SIGNAL panel above
 * it. The panel is the SAME component the page renders inline, so answer
 * quality and the rubric cannot drift between the two placements.
 *
 * Established patterns for a launcher like this, all implemented here:
 *   - Escape closes it, and focus returns to the button
 *   - Clicking outside closes it
 *   - The input is focused on open so you can type immediately
 *   - aria-expanded / aria-controls / aria-haspopup on the button, role dialog
 *     with aria-modal false on the panel, since the page stays usable
 *   - Body scroll is never locked on desktop; the panel scrolls internally
 *   - Conversation state lives above the toggle, so closing and reopening does
 *     not lose the thread
 *   - Goes near-full-width under 720px
 */

import { useEffect, useRef, useState } from "react";
import { X } from "lucide-react";
import { SignalAvatar } from "@/components/signal-avatar";
import { SignalChat } from "@/components/signal-chat";

export function SignalLauncher({
  cohortKeys, org,
}: {
  cohortKeys: string[];
  org: string | null;
}) {
  const [open, setOpen] = useState(false);
  const btnRef = useRef<HTMLButtonElement>(null);
  const dockRef = useRef<HTMLDivElement>(null);

  // Escape to close, returning focus to the launcher.
  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        setOpen(false);
        btnRef.current?.focus();
      }
    };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [open]);

  // Click outside closes. Pointerdown so it beats any inner click handler.
  useEffect(() => {
    if (!open) return;
    const onDown = (e: PointerEvent) => {
      const t = e.target as Node;
      if (dockRef.current?.contains(t) || btnRef.current?.contains(t)) return;
      setOpen(false);
    };
    document.addEventListener("pointerdown", onDown);
    return () => document.removeEventListener("pointerdown", onDown);
  }, [open]);

  // Focus the composer on open so the panel is immediately usable.
  useEffect(() => {
    if (!open) return;
    const t = setTimeout(() => {
      dockRef.current?.querySelector<HTMLInputElement>(".phone-input")?.focus();
    }, 260);
    return () => clearTimeout(t);
  }, [open]);

  return (
    <>
      {open && (
        <div
          ref={dockRef}
          className="signal-dock"
          role="dialog"
          aria-modal="false"
          aria-label="SIGNAL cohort analyst"
          id="signal-dock"
        >
          <div className="relative">
            {/* sits just outside the phone frame so it never covers chrome */}
            <button
              onClick={() => { setOpen(false); btnRef.current?.focus(); }}
              className="glass absolute -right-1 -top-3 z-30 w-8 h-8 rounded-full flex items-center justify-center"
              aria-label="Close SIGNAL"
            >
              <X className="w-4 h-4" />
            </button>
            <SignalChat cohortKeys={cohortKeys} org={org} compact />
          </div>
        </div>
      )}

      <button
        ref={btnRef}
        className="signal-fab"
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
        aria-haspopup="dialog"
        aria-controls="signal-dock"
        aria-label={open ? "Close SIGNAL" : "Ask SIGNAL"}
        title={open ? "Close SIGNAL" : "Ask SIGNAL"}
      >
        <span className="signal-fab-ring" aria-hidden />
        <span className="relative">
          <SignalAvatar size={40} live />
        </span>
        {!open && <span className="signal-fab-badge" aria-hidden />}
      </button>
    </>
  );
}
