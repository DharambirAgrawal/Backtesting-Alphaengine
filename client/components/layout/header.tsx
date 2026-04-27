"use client";

import { Menu } from "lucide-react";
import { useAuth } from "@/hooks/use-auth";
import { PortfolioSwitcher } from "./portfolio-switcher";
import { usePortfolios } from "@/hooks/use-portfolio";
import { Button } from "@/components/ui/button";

interface HeaderProps {
  portfolioId?: string;
  title?: string;
  onMenuClick?: () => void;
}

export function Header({ portfolioId, title, onMenuClick }: HeaderProps) {
  const { email, role, isReady } = useAuth();
  const { portfolios } = usePortfolios(Boolean(portfolioId));
  const displayEmail = email ?? "Signed in";
  const displayRole = isReady ? role ?? "user" : "Loading";
  const initial = email?.charAt(0).toUpperCase() ?? "A";

  return (
    <header className="flex h-16 items-center justify-between gap-3 border-b border-border bg-card/50 px-4 sm:px-6">
      <div className="flex min-w-0 flex-1 items-center gap-3">
        <Button
          variant="ghost"
          size="icon-sm"
          onClick={onMenuClick}
          className="md:hidden"
          aria-label="Open navigation"
        >
          <Menu className="h-4 w-4" />
        </Button>
        {portfolioId ? (
          <PortfolioSwitcher
            portfolios={portfolios}
            currentPortfolioId={portfolioId}
          />
        ) : (
          <h1 className="truncate text-base font-semibold text-foreground sm:text-lg">
            {title || "Dashboard"}
          </h1>
        )}
      </div>

      <div className="flex items-center gap-3 sm:gap-4">
        <div className="hidden text-right sm:block">
          <p className="max-w-[180px] truncate text-sm font-medium text-foreground">
            {displayEmail}
          </p>
          <p className="text-xs text-muted-foreground capitalize">
            {displayRole}
          </p>
        </div>
        <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-primary/10">
          <span className="text-sm font-medium text-primary">{initial}</span>
        </div>
      </div>
    </header>
  );
}
