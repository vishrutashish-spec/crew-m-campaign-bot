"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { LayoutDashboard, Users, FlaskConical, BookOpen, Settings } from "lucide-react";
import { CrewMLogo } from "@/components/logos";
import { ThemeToggle } from "@/components/theme-toggle";
import { useAuth } from "@/components/auth-gate";
import { LogOut } from "lucide-react";

const NAV = [
  { href: "/", label: "Overview", icon: LayoutDashboard },
  { href: "/cohorts", label: "Cohorts", icon: Users },
  { href: "/simulate", label: "Simulator", icon: FlaskConical },
  { href: "/methodology", label: "Methodology", icon: BookOpen },
  { href: "/settings", label: "Settings", icon: Settings },
];

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="fixed inset-y-0 left-0 w-[236px] bg-sidebar border-r border-border flex flex-col z-40">
      {/* Brand */}
      <div className="h-[108px] flex items-center px-5 border-b border-border relative grid-ground overflow-hidden">
        <Link href="/" className="relative">
          <CrewMLogo />
        </Link>
      </div>

      {/* Nav */}
      <nav className="flex-1 px-3.5 pt-5">
        <p className="label-mono px-2.5 pb-2.5">Navigate</p>
        <div className="space-y-1">
          {NAV.map((item) => {
            const active =
              item.href === "/" ? pathname === "/" : pathname.startsWith(item.href);
            const Icon = item.icon;
            return (
              <Link
                key={item.href}
                href={item.href}
                className={`relative flex items-center gap-3 px-2.5 py-2.5 rounded-[10px] text-[13px] transition-all duration-150 ${
                  active
                    ? "bg-[color:var(--cyan-wash)] text-[color:var(--cyan-deep)] font-medium border border-[color:#b3e8ee]"
                    : "text-foreground/75 hover:text-foreground hover:bg-[color:var(--muted)] border border-transparent"
                }`}
              >
                {active && (
                  <span className="absolute left-0 top-2.5 bottom-2.5 w-[2.5px] rounded-r metal-cyan" />
                )}
                <Icon
                  className="w-[17px] h-[17px] flex-shrink-0"
                  strokeWidth={active ? 2.2 : 1.8}
                />
                {item.label}
              </Link>
            );
          })}
        </div>
      </nav>

      {/* Footer: the scope caveat lives here so it is always in view */}
      <div className="px-3.5 pb-4">
        <div className="flex items-center justify-between px-1 mb-3">
          <span className="label-mono">Theme</span>
          <ThemeToggle />
        </div>
        <div className="panel-flush p-3 bg-[color:var(--muted)]">
          <div className="flex items-center gap-2 mb-1.5">
            <span className="w-1.5 h-1.5 rounded-full bg-[color:var(--success)] live-dot" />
            <span className="label-mono !text-[9px]">Eligible base</span>
          </div>
          <p className="figure text-[15px]">956,050</p>
          <p className="text-[10px] text-muted-foreground mt-1 leading-snug">
            Active, non-test organisations
          </p>
        </div>
        <SignedIn />
        <p className="text-[10px] text-muted-foreground mt-3 px-1">
          Plum Product Marketing
        </p>
      </div>
    </aside>
  );
}


/**
 * Who is signed in, and the way out.
 *
 * Kept in the sidebar footer rather than a header menu, because on a tool
 * holding confidential aggregates the identity should always be in view: it is
 * the answer to "whose access produced this screenshot".
 */
function SignedIn() {
  const { email, signOut } = useAuth();
  if (!email) return null;
  const initials = email.split("@")[0].split(/[._-]/)
    .filter(Boolean).slice(0, 2).map((s) => s[0]?.toUpperCase()).join("");
  return (
    <div className="flex items-center gap-2 mt-3 px-1">
      <span className="auth-who">
        <span className="auth-avatar metal-cyan" aria-hidden>{initials || "P"}</span>
        <span className="auth-email" title={email}>{email}</span>
      </span>
      <button onClick={signOut} className="auth-signout ml-auto"
        aria-label="Sign out" title="Sign out">
        <LogOut className="w-3 h-3" />
      </button>
    </div>
  );
}
