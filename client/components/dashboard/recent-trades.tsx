"use client";

import { useState } from "react";
import Link from "next/link";
import { cn } from "@/lib/utils";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  CardAction,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { EmptyState } from "@/components/ui/empty-state";
import { RelativeDate } from "@/components/ui/relative-date";
import { ChevronRight, ChevronDown, ArrowRightLeft } from "lucide-react";
import { formatCurrency, formatShares } from "@/lib/format";
import { ACTION_COLORS } from "@/lib/constants";
import type { Transaction } from "@/lib/types";
import { Skeleton } from "@/components/ui/skeleton";

interface RecentTradesProps {
  transactions: Transaction[];
  portfolioId: string;
  isLoading?: boolean;
}

export function RecentTrades({
  transactions,
  portfolioId,
  isLoading,
}: RecentTradesProps) {
  const [expandedId, setExpandedId] = useState<string | null>(null);

  if (isLoading) {
    return (
      <Card className="bg-card/50 border-border/50">
        <CardHeader>
          <CardTitle className="text-base font-medium">
            Recent Agent Activity
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            {[1, 2, 3].map((i) => (
              <Skeleton key={i} className="h-16 w-full" />
            ))}
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="bg-card/50 border-border/50">
      <CardHeader>
        <CardTitle className="text-base font-medium">
          Recent Agent Activity
        </CardTitle>
        <CardAction>
          <Button variant="ghost" size="sm" asChild>
            <Link
              href={`/dashboard/${portfolioId}/trades`}
              className="text-primary"
            >
              View all
              <ChevronRight className="ml-1 h-4 w-4" />
            </Link>
          </Button>
        </CardAction>
      </CardHeader>
      <CardContent>
        {transactions.length === 0 ? (
          <EmptyState
            icon={ArrowRightLeft}
            title="No trades yet"
            description="Agent activity will appear here after the first trade is executed."
          />
        ) : (
          <div className="space-y-3">
            {transactions.map((tx) => (
              <div
                key={tx.id}
                className="rounded-lg border border-border/50 bg-background/50 p-3"
              >
                <div className="flex items-start justify-between">
                  <div className="flex items-center gap-2">
                    <Badge
                      variant="outline"
                      className={cn(
                        "font-mono text-xs",
                        ACTION_COLORS[tx.action]
                      )}
                    >
                      {tx.action}
                    </Badge>
                    <span className="font-mono font-semibold text-foreground">
                      {tx.ticker}
                    </span>
                    <span className="text-sm text-muted-foreground">
                      {formatShares(tx.shares)} shares @ {formatCurrency(tx.price_at_trade)}
                    </span>
                  </div>
                  <RelativeDate
                    value={tx.executed_at}
                    className="text-xs text-muted-foreground"
                  />
                </div>

                <div className="mt-2">
                  <button
                    onClick={() =>
                      setExpandedId(expandedId === tx.id ? null : tx.id)
                    }
                    className="flex items-center gap-1 text-xs text-primary hover:text-primary/80 transition-colors"
                  >
                    {expandedId === tx.id ? (
                      <ChevronDown className="h-3 w-3" />
                    ) : (
                      <ChevronRight className="h-3 w-3" />
                    )}
                    Why?
                  </button>

                  {expandedId === tx.id && (
                    <div className="mt-2 rounded-md bg-secondary/30 p-3 text-sm text-muted-foreground">
                      <p className="italic">&quot;{tx.llm_reasoning}&quot;</p>
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
