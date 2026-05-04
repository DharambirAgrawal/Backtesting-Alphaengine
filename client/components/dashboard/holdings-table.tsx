"use client";

import { useEffect, useMemo } from "react";
import { cn } from "@/lib/utils";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { formatCurrency, formatPct, formatShares } from "@/lib/format";
import type { Holding } from "@/lib/types";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/ui/empty-state";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Briefcase } from "lucide-react";

interface HoldingsTableProps {
  holdings: Holding[];
  isLoading?: boolean;
}

export function HoldingsTable({ holdings, isLoading }: HoldingsTableProps) {
  const errorHoldings = useMemo(
    () => holdings.filter((holding) => holding.price_error),
    [holdings]
  );
  const errorDigest = useMemo(
    () =>
      errorHoldings
        .map((holding) => `${holding.ticker}:${holding.price_error}`)
        .join("|") ||
      "",
    [errorHoldings]
  );

  useEffect(() => {
    if (!errorHoldings.length) return;
    console.warn("Market data errors", errorHoldings);
  }, [errorDigest, errorHoldings]);

  if (isLoading) {
    return (
      <Card className="bg-card/50 border-border/50">
        <CardHeader>
          <CardTitle className="text-base font-medium">
            Current Holdings
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-2">
            {[1, 2, 3].map((i) => (
              <Skeleton key={i} className="h-12 w-full" />
            ))}
          </div>
        </CardContent>
      </Card>
    );
  }

  if (holdings.length === 0) {
    return (
      <Card className="bg-card/50 border-border/50">
        <CardHeader>
          <CardTitle className="text-base font-medium">
            Current Holdings
          </CardTitle>
        </CardHeader>
        <CardContent>
          <EmptyState
            icon={Briefcase}
            title="No holdings yet"
            description="Your positions will appear here after the agent makes its first trade."
          />
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="bg-card/50 border-border/50">
      <CardHeader>
        <CardTitle className="text-base font-medium">Current Holdings</CardTitle>
      </CardHeader>
      <CardContent>
        {errorHoldings.length > 0 && (
          <Alert variant="destructive" className="mb-4">
            <AlertTitle>Market data issue</AlertTitle>
            <AlertDescription>
              <p>
                Live prices failed for: {errorHoldings
                  .map((holding) => holding.ticker)
                  .join(", ")}
                . Falling back to cached or avg-buy prices.
              </p>
              <div className="mt-2 space-y-1 text-xs text-destructive/90">
                {errorHoldings.map((holding) => (
                  <div key={`price-error-${holding.ticker}`}>
                    <span className="font-mono">{holding.ticker}:</span>{" "}
                    {holding.price_error}
                  </div>
                ))}
              </div>
            </AlertDescription>
          </Alert>
        )}
        <div className="space-y-3 md:hidden">
          {holdings.map((holding) => (
            <div
              key={holding.ticker}
              className="rounded-lg border border-border/50 bg-background/50 p-3"
            >
              <div className="flex items-start justify-between gap-3">
                <div>
                  <div className="font-mono font-semibold text-foreground">
                    {holding.ticker}
                  </div>
                  <div className="text-xs text-muted-foreground">
                    {formatShares(holding.shares)} shares
                  </div>
                </div>
                <div className="text-right">
                  <div className="font-mono font-medium text-foreground">
                    {formatCurrency(holding.value)}
                  </div>
                  <div
                    className={cn(
                      "text-xs font-mono",
                      holding.profit_loss >= 0 ? "text-profit" : "text-loss"
                    )}
                  >
                    {formatCurrency(holding.profit_loss, { showSign: true })}{" "}
                    ({formatPct(holding.profit_loss_pct)})
                  </div>
                </div>
              </div>

              <div className="mt-3 grid grid-cols-2 gap-2 text-sm">
                <div className="rounded-md bg-secondary/30 p-2">
                  <div className="text-xs text-muted-foreground">Avg Buy</div>
                  <div className="font-mono">{formatCurrency(holding.avg_buy_price)}</div>
                </div>
                <div className="rounded-md bg-secondary/30 p-2">
                  <div className="text-xs text-muted-foreground">Current</div>
                  <div className="font-mono">{formatCurrency(holding.current_price)}</div>
                </div>
              </div>
            </div>
          ))}
        </div>

        <div className="hidden overflow-x-auto md:block">
          <Table>
            <TableHeader>
              <TableRow className="border-border/50 hover:bg-transparent">
                <TableHead className="text-muted-foreground">Ticker</TableHead>
                <TableHead className="text-right text-muted-foreground">
                  Shares
                </TableHead>
                <TableHead className="text-right text-muted-foreground">
                  Avg Buy
                </TableHead>
                <TableHead className="text-right text-muted-foreground">
                  Current
                </TableHead>
                <TableHead className="text-right text-muted-foreground">
                  Value
                </TableHead>
                <TableHead className="text-right text-muted-foreground">
                  P&amp;L
                </TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {holdings.map((holding) => (
                <TableRow
                  key={holding.ticker}
                  className="border-border/50 hover:bg-secondary/30"
                >
                  <TableCell className="font-mono font-semibold text-foreground">
                    {holding.ticker}
                  </TableCell>
                  <TableCell className="text-right font-mono">
                    {formatShares(holding.shares)}
                  </TableCell>
                  <TableCell className="text-right font-mono text-muted-foreground">
                    {formatCurrency(holding.avg_buy_price)}
                  </TableCell>
                  <TableCell className="text-right font-mono">
                    {formatCurrency(holding.current_price)}
                  </TableCell>
                  <TableCell className="text-right font-mono font-medium">
                    {formatCurrency(holding.value)}
                  </TableCell>
                  <TableCell className="text-right">
                    <div className="flex flex-col items-end">
                      <span
                        className={cn(
                          "font-mono font-medium",
                          holding.profit_loss >= 0 ? "text-profit" : "text-loss"
                        )}
                      >
                        {formatCurrency(holding.profit_loss, { showSign: true })}
                      </span>
                      <span
                        className={cn(
                          "text-xs font-mono",
                          holding.profit_loss_pct >= 0
                            ? "text-profit"
                            : "text-loss"
                        )}
                      >
                        {formatPct(holding.profit_loss_pct)}
                      </span>
                    </div>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      </CardContent>
    </Card>
  );
}
