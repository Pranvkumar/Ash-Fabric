import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "ASH-Fabric — Command Center",
  description: "Autonomous Self-Healing Cloud Fabric Dashboard",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-ash-bg text-ash-text antialiased">
        {/* Top Navigation */}
        <nav className="sticky top-0 z-50 border-b border-ash-border bg-ash-bg/80 backdrop-blur-md">
          <div className="mx-auto flex max-w-7xl items-center justify-between px-6 py-3">
            <div className="flex items-center gap-3">
              <div className="h-8 w-8 rounded-lg bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center text-sm font-bold">
                AF
              </div>
              <span className="text-lg font-semibold tracking-tight">
                ASH-Fabric
              </span>
              <span className="ml-2 rounded-full bg-ash-accent/10 px-2 py-0.5 text-xs text-ash-accent">
                v0.1.0
              </span>
            </div>
            <div className="flex items-center gap-4 text-sm text-ash-muted">
              <div className="flex items-center gap-1.5">
                <span className="h-2 w-2 rounded-full bg-ash-success animate-pulse-dot" />
                System Online
              </div>
            </div>
          </div>
        </nav>

        <main className="mx-auto max-w-7xl px-6 py-6">{children}</main>
      </body>
    </html>
  );
}
