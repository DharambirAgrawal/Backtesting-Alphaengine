"use client";

import { useAuth } from "@/hooks/use-auth";
import { PortfolioSwitcher } from "./portfolio-switcher";
import { usePortfolios } from "@/hooks/use-portfolio";

interface HeaderProps {
  portfolioId?: string;
  title?: string;
}

export function Header({ portfolioId, title }: HeaderProps) {
  const { email, role } = useAuth();
  const { portfolios } = usePortfolios();

  return (
    <header className="flex h-16 items-center justify-between border-b border-border bg-card/50 px-6">
      <div className="flex items-center gap-4">
        {portfolioId ? (
          <PortfolioSwitcher
            portfolios={portfolios}
            currentPortfolioId={portfolioId}
          />
        ) : (
          <h1 className="text-lg font-semibold text-foreground">
            {title || "Dashboard"}
          </h1>
        )}
      </div>

      <div className="flex items-center gap-4">
        <div className="text-right">
          <p className="text-sm font-medium text-foreground">{email}</p>
          <p className="text-xs text-muted-foreground capitalize">{role}</p>
        </div>
        <div className="h-9 w-9 rounded-full bg-primary/10 flex items-center justify-center">
          <span className="text-sm font-medium text-primary">
            {email?.charAt(0).toUpperCase()}
          </span>
        </div>
      </div>
    </header>
  );
}
