"use client";

import { Sidebar } from "./sidebar";
import { Header } from "./header";

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
  return (
    <div className="flex h-screen overflow-hidden bg-background">
      <Sidebar portfolioId={portfolioId} />
      <div className="flex flex-1 flex-col overflow-hidden">
        <Header portfolioId={portfolioId} title={title} />
        <main className="flex-1 overflow-auto p-6">{children}</main>
      </div>
    </div>
  );
}
