"use client";

import { cn } from "@/lib/utils";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Badge } from "@/components/ui/badge";
import { formatCurrency, formatDate, formatShares } from "@/lib/format";
import { ACTION_COLORS } from "@/lib/constants";
import type { Transaction } from "@/lib/types";
import { MessageSquare, Wrench } from "lucide-react";

interface TradeDetailModalProps {
  transaction: Transaction | null;
  open: boolean;
  onClose: () => void;
}

export function TradeDetailModal({
  transaction,
  open,
  onClose,
}: TradeDetailModalProps) {
  if (!transaction) return null;

  const toolsCalled = transaction.tools_called
    ? Object.entries(transaction.tools_called)
    : [];

  return (
    <Dialog open={open} onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="max-w-2xl bg-card border-border">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-3">
            <span>Trade:</span>
            <Badge
              variant="outline"
              className={cn(
                "font-mono text-sm",
                ACTION_COLORS[transaction.action]
              )}
            >
              {transaction.action}
            </Badge>
            <span className="font-mono font-bold">{transaction.ticker}</span>
            <span className="text-muted-foreground font-normal">
              {formatDate(transaction.executed_at, "long")}
            </span>
          </DialogTitle>
        </DialogHeader>

        <div className="space-y-6">
          {/* Trade Summary */}
          <div className="flex items-center gap-6 text-sm">
            <div>
              <span className="text-muted-foreground">Shares: </span>
              <span className="font-mono font-medium">
                {formatShares(transaction.shares)}
              </span>
            </div>
            <div>
              <span className="text-muted-foreground">Price: </span>
              <span className="font-mono font-medium">
                {formatCurrency(transaction.price_at_trade)}
              </span>
            </div>
            <div>
              <span className="text-muted-foreground">Total: </span>
              <span className="font-mono font-medium">
                {formatCurrency(transaction.total_value)}
              </span>
            </div>
          </div>

          {/* Agent Reasoning */}
          <div>
            <div className="flex items-center gap-2 text-sm font-medium text-foreground mb-2">
              <MessageSquare className="h-4 w-4 text-primary" />
              Agent Reasoning
            </div>
            <div className="rounded-lg bg-secondary/30 border border-border/50 p-4">
              <p className="text-sm text-muted-foreground italic leading-relaxed">
                &quot;{transaction.llm_reasoning}&quot;
              </p>
            </div>
          </div>

          {/* Tools Called */}
          {toolsCalled.length > 0 && (
            <div>
              <div className="flex items-center gap-2 text-sm font-medium text-foreground mb-2">
                <Wrench className="h-4 w-4 text-primary" />
                Tools Called
              </div>
              <div className="rounded-lg bg-secondary/30 border border-border/50 overflow-hidden">
                <div className="divide-y divide-border/50">
                  {toolsCalled.map(([tool, result]) => (
                    <div
                      key={tool}
                      className="flex items-start justify-between px-4 py-3 text-sm"
                    >
                      <span className="font-mono text-primary">{tool}</span>
                      <span className="font-mono text-muted-foreground text-right max-w-[60%] truncate">
                        {typeof result === "object"
                          ? JSON.stringify(result)
                          : String(result)}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
}
