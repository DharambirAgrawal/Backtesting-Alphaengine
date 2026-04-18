"use client";

import { useState } from "react";
import { cn } from "@/lib/utils";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { TradeDetailModal } from "./trade-detail-modal";
import { formatCurrency, formatShares, formatDate } from "@/lib/format";
import { ACTION_COLORS } from "@/lib/constants";
import type { Transaction } from "@/lib/types";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/ui/empty-state";
import { ArrowRightLeft } from "lucide-react";

interface TransactionTableProps {
  transactions: Transaction[];
  isLoading?: boolean;
}

export function TransactionTable({
  transactions,
  isLoading,
}: TransactionTableProps) {
  const [selectedTransaction, setSelectedTransaction] =
    useState<Transaction | null>(null);

  if (isLoading) {
    return (
      <div className="space-y-2">
        {[1, 2, 3, 4, 5].map((i) => (
          <Skeleton key={i} className="h-14 w-full" />
        ))}
      </div>
    );
  }

  if (transactions.length === 0) {
    return (
      <EmptyState
        icon={ArrowRightLeft}
        title="No transactions found"
        description="Try adjusting your filters or wait for the agent to make some trades."
      />
    );
  }

  return (
    <>
      <div className="overflow-x-auto rounded-lg border border-border/50">
        <Table>
          <TableHeader>
            <TableRow className="border-border/50 bg-secondary/30 hover:bg-secondary/30">
              <TableHead className="text-muted-foreground">Date & Time</TableHead>
              <TableHead className="text-muted-foreground">Ticker</TableHead>
              <TableHead className="text-muted-foreground">Action</TableHead>
              <TableHead className="text-right text-muted-foreground">
                Shares
              </TableHead>
              <TableHead className="text-right text-muted-foreground">
                Price
              </TableHead>
              <TableHead className="text-right text-muted-foreground">
                Total
              </TableHead>
              <TableHead className="text-center text-muted-foreground">
                Details
              </TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {transactions.map((tx) => (
              <TableRow
                key={tx.id}
                className="border-border/50 hover:bg-secondary/20"
              >
                <TableCell className="text-sm text-muted-foreground">
                  {formatDate(tx.executed_at, "long")}
                </TableCell>
                <TableCell className="font-mono font-semibold text-foreground">
                  {tx.ticker}
                </TableCell>
                <TableCell>
                  <Badge
                    variant="outline"
                    className={cn("font-mono text-xs", ACTION_COLORS[tx.action])}
                  >
                    {tx.action}
                  </Badge>
                </TableCell>
                <TableCell className="text-right font-mono">
                  {formatShares(tx.shares)}
                </TableCell>
                <TableCell className="text-right font-mono">
                  {formatCurrency(tx.price_at_trade)}
                </TableCell>
                <TableCell className="text-right font-mono font-medium">
                  {formatCurrency(tx.total_value)}
                </TableCell>
                <TableCell className="text-center">
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => setSelectedTransaction(tx)}
                    className="text-primary hover:text-primary/80"
                  >
                    View Reasoning
                  </Button>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>

      <TradeDetailModal
        transaction={selectedTransaction}
        open={!!selectedTransaction}
        onClose={() => setSelectedTransaction(null)}
      />
    </>
  );
}
