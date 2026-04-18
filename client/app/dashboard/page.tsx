"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect } from "react";
import { DashboardLayout } from "@/components/layout/dashboard-layout";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/empty-state";
import { Skeleton } from "@/components/ui/skeleton";
import { usePortfolios } from "@/hooks/use-portfolio";
import { formatCurrency, formatPct, formatDate } from "@/lib/format";
import { cn } from "@/lib/utils";
import {
  Briefcase,
  Plus,
  TrendingUp,
  TrendingDown,
  ChevronRight,
} from "lucide-react";

export default function DashboardPage() {
  const router = useRouter();
  const { portfolios, isLoading } = usePortfolios();

  // If only one portfolio, redirect directly to it
  useEffect(() => {
    if (!isLoading && portfolios.length === 1) {
      router.replace(`/dashboard/${portfolios[0].id}`);
    }
  }, [isLoading, portfolios, router]);

  return (
    <DashboardLayout title="Portfolios">
      <div className="mx-auto max-w-6xl">
        <div className="mb-6 flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-foreground">
              Your Portfolios
            </h1>
            <p className="text-muted-foreground">
              Manage your paper trading portfolios
            </p>
          </div>
          <Button asChild>
            <Link href="/portfolios/new">
              <Plus className="h-4 w-4" />
              Create Portfolio
            </Link>
          </Button>
        </div>

        {isLoading ? (
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            {[1, 2, 3].map((i) => (
              <Skeleton key={i} className="h-48" />
            ))}
          </div>
        ) : portfolios.length === 0 ? (
          <Card className="bg-card/50 border-border/50">
            <CardContent className="py-12">
              <EmptyState
                icon={Briefcase}
                title="No portfolios yet"
                description="Create your first portfolio to start paper trading with AI-powered decisions."
              >
                <Button asChild>
                  <Link href="/portfolios/new">
                    <Plus className="h-4 w-4" />
                    Create Portfolio
                  </Link>
                </Button>
              </EmptyState>
            </CardContent>
          </Card>
        ) : (
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            {portfolios.map((portfolio) => {
              const isPositive = portfolio.profit_loss >= 0;
              return (
                <Link
                  key={portfolio.id}
                  href={`/dashboard/${portfolio.id}`}
                  className="group"
                >
                  <Card className="bg-card/50 border-border/50 transition-all hover:border-primary/50 hover:bg-card/80">
                    <CardHeader className="pb-2">
                      <div className="flex items-start justify-between">
                        <CardTitle className="text-lg font-semibold group-hover:text-primary transition-colors">
                          {portfolio.name}
                        </CardTitle>
                        <ChevronRight className="h-5 w-5 text-muted-foreground group-hover:text-primary transition-colors" />
                      </div>
                      {portfolio.description && (
                        <p className="text-sm text-muted-foreground line-clamp-1">
                          {portfolio.description}
                        </p>
                      )}
                    </CardHeader>
                    <CardContent>
                      <div className="flex items-baseline justify-between">
                        <span className="text-2xl font-bold font-mono text-foreground">
                          {formatCurrency(portfolio.total_value)}
                        </span>
                        <div
                          className={cn(
                            "flex items-center gap-1 rounded-md px-2 py-0.5 text-sm font-mono font-medium",
                            isPositive
                              ? "bg-profit/10 text-profit"
                              : "bg-loss/10 text-loss"
                          )}
                        >
                          {isPositive ? (
                            <TrendingUp className="h-3 w-3" />
                          ) : (
                            <TrendingDown className="h-3 w-3" />
                          )}
                          {formatPct(portfolio.profit_loss_pct)}
                        </div>
                      </div>

                      <div className="mt-4 flex items-center justify-between text-sm">
                        <div className="flex items-center gap-1 text-muted-foreground">
                          <span className="font-mono">
                            {formatCurrency(portfolio.starting_capital)}
                          </span>
                          <span className="mx-1">→</span>
                          <span
                            className={cn(
                              "font-mono",
                              isPositive ? "text-profit" : "text-loss"
                            )}
                          >
                            {formatCurrency(portfolio.total_value)}
                          </span>
                        </div>
                      </div>

                      <div className="mt-3 flex items-center justify-between text-xs text-muted-foreground">
                        <span>{portfolio.tickers.length} tickers</span>
                        <span>Created {formatDate(portfolio.created_at)}</span>
                      </div>
                    </CardContent>
                  </Card>
                </Link>
              );
            })}
          </div>
        )}
      </div>
    </DashboardLayout>
  );
}
