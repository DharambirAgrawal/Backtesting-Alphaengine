"use client";

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
import { Briefcase } from "lucide-react";

interface HoldingsTableProps {
  holdings: Holding[];
  isLoading?: boolean;
}

export function HoldingsTable({ holdings, isLoading }: HoldingsTableProps) {
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
        <div className="overflow-x-auto">
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
                  P&L
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
