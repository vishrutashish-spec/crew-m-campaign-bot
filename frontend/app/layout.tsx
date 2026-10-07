import type { Metadata } from "next";
import { Inter, Geist_Mono } from "next/font/google";
import "./globals.css";
import { Sidebar } from "@/components/sidebar";
import { CursorGlow } from "@/components/cursor-glow";
import { SignalLauncher } from "@/components/signal-launcher";
import { AuthGate } from "@/components/auth-gate";

// Inter carries body copy; Vollkorn is loaded from /public/fonts via @font-face
// in globals.css and owns every heading, figure and chart label.
const inter = Inter({
  variable: "--font-inter",
  subsets: ["latin"],
  display: "swap",
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
  display: "swap",
});

export const metadata: Metadata = {
  title: "Crew M",
  description: "Campaign intelligence for Plum product marketing",
};

// Applies the saved theme (or the OS preference) before first paint, so
// neither theme ever flashes. Runs synchronously during HTML parsing.
const THEME_INIT = `(function(){try{var t=localStorage.getItem("crewm-theme");var d=t?t==="dark":matchMedia("(prefers-color-scheme: dark)").matches;if(d)document.documentElement.classList.add("dark")}catch(e){}})();`;

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="en" className={`${inter.variable} ${geistMono.variable} h-full`}
      suppressHydrationWarning>
      <body className="min-h-full bg-background text-foreground">
        <script dangerouslySetInnerHTML={{ __html: THEME_INIT }} />
        {/* Nothing below the gate renders until a Plum Workspace session
            exists, so no sidebar, assistant or figure ever paints for a
            signed-out visitor. The server gate in proxy.ts is what
            actually protects the data. */}
        <AuthGate>
          <CursorGlow />
          <Sidebar />
          <main className="ml-[236px] min-h-screen">
            <div className="mx-auto w-full max-w-[1500px] px-8 xl:px-12 py-9">
              {children}
            </div>
          </main>
          {/* SIGNAL is reachable from every screen. Pages that care about a
              specific cohort still render their own inline phone. */}
          <SignalLauncher cohortKeys={["26_35"]} org={null} />
        </AuthGate>
      </body>
    </html>
  );
}
