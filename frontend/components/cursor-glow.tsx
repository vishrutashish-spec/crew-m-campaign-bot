"use client";

/**
 * A plum-red bloom that follows the pointer.
 *
 * Two layers moving at different rates give it the sense of a light source
 * with weight: a wide soft halo that lags, and a tighter core that tracks
 * closely. Both are eased toward the pointer every frame rather than snapped,
 * which is what makes it read as seamless instead of a chasing dot.
 *
 * Position is written straight to the transform in a rAF loop, so React never
 * re-renders on mouse move. Mouse coordinates go nowhere near state.
 * Hidden on touch and under reduced motion by CSS.
 */

import { useEffect, useRef } from "react";

export function CursorGlow() {
  const halo = useRef<HTMLDivElement>(null);
  const core = useRef<HTMLDivElement>(null);

  useEffect(() => {
    // Skip entirely where a cursor glow makes no sense or is unwelcome.
    if (typeof window === "undefined") return;
    if (window.matchMedia("(hover: none)").matches) return;
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;

    const target = { x: window.innerWidth / 2, y: window.innerHeight / 2 };
    const slow = { ...target };
    const fast = { ...target };
    let raf = 0;
    let visible = false;

    const move = (e: MouseEvent) => {
      target.x = e.clientX;
      target.y = e.clientY;
      if (!visible) {
        visible = true;
        halo.current?.classList.add("on");
        core.current?.classList.add("on");
      }
    };
    const leave = () => {
      visible = false;
      halo.current?.classList.remove("on");
      core.current?.classList.remove("on");
    };

    const tick = () => {
      // Two easing rates: the halo trails, the core keeps up.
      slow.x += (target.x - slow.x) * 0.075;
      slow.y += (target.y - slow.y) * 0.075;
      fast.x += (target.x - fast.x) * 0.20;
      fast.y += (target.y - fast.y) * 0.20;
      if (halo.current) {
        halo.current.style.transform =
          `translate3d(${slow.x}px, ${slow.y}px, 0)`;
      }
      if (core.current) {
        core.current.style.transform =
          `translate3d(${fast.x}px, ${fast.y}px, 0)`;
      }
      raf = requestAnimationFrame(tick);
    };

    window.addEventListener("mousemove", move, { passive: true });
    document.addEventListener("mouseleave", leave);
    raf = requestAnimationFrame(tick);

    return () => {
      window.removeEventListener("mousemove", move);
      document.removeEventListener("mouseleave", leave);
      cancelAnimationFrame(raf);
    };
  }, []);

  return (
    <>
      <div ref={halo} className="cursor-glow" aria-hidden />
      <div ref={core} className="cursor-glow-core" aria-hidden />
    </>
  );
}
