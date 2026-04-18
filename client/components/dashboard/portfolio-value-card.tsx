"use client";

import { cn } from "@/lib/utils";
import { Card, CardContent } from "@/components/ui/card";
import { TrendingUp, TrendingDown } from "lucide-react";
import { formatCurrency, formatPct } from "@/lib/format";

interface PortfolioValueCardProps {
  totalValue: number;
  profitLoss: number;
  profitLossPct: number;
  className?: string;
}

export function PortfolioValueCard({
  totalValue,
  profitLoss,
  profitLossPct,
  className,
}: PortfolioValueCardProps) {
  const isPositive = profitLoss >= 0;

  return (
    <Card className={cn("bg-card/50 border-border/50", className)}>
      <CardContent className="p-4">
        <p className="text-sm text-muted-foreground">Total Value</p>
        <p className="mt-1 text-3xl font-bold font-mono text-foreground">
          {formatCurrency(totalValue)}
        </p>
        <div className="mt-2 flex items-center gap-2">
          <div
            className={cn(
              "flex items-center gap-1 rounded-md px-2 py-0.5",
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
            <span className="text-sm font-mono font-medium">
              {formatCurrency(profitLoss, { showSign: true })}
            </span>
          </div>
          <span
            className={cn(
              "text-sm font-mono",
              isPositive ? "text-profit" : "text-loss"
            )}
          >
            ({formatPct(profitLossPct)})
          </span>
        </div>
      </CardContent>
    </Card>
  );
}
