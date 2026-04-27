"use client";

import { useState } from "react";
import { Sidebar } from "./sidebar";
import { Header } from "./header";
import { ConnectionBanner } from "./connection-banner";

interface DashboardLayoutProps {
  children: React.ReactNode;
  portfolioId?: string;
  title?: string;
}

export function DashboardLayout({
  children,
  portfolioId,
  title,
}: DashboardLayoutProps) {
  const [mobileNavOpen, setMobileNavOpen] = useState(false);

  return (
    <div className="flex min-h-screen bg-background">
      <Sidebar
        portfolioId={portfolioId}
        mobileOpen={mobileNavOpen}
        onMobileOpenChange={setMobileNavOpen}
      />
      <div className="flex flex-1 flex-col overflow-hidden">
        <ConnectionBanner />
        <Header
          portfolioId={portfolioId}
          title={title}
          onMenuClick={() => setMobileNavOpen(true)}
        />
        <main className="flex-1 overflow-auto p-4 pb-20 sm:p-6 sm:pb-6 animate-fade-in-up">
          {children}
        </main>
      </div>
    </div>
  );
}
