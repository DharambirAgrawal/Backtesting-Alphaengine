"use client";

import { Badge } from "@/components/ui/badge";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "@/components/ui/accordion";
import { Skeleton } from "@/components/ui/skeleton";
import { ACTION_COLORS } from "@/lib/constants";
import { cn } from "@/lib/utils";
import { formatCurrency, formatDateTimeET, formatShares } from "@/lib/format";
import type { AgentRun, AgentRunDetail } from "@/lib/types";
import { Bot, Wrench } from "lucide-react";

interface RunDetailModalProps {
  runSummary: AgentRun | null;
  run: AgentRunDetail | null;
  isLoading: boolean;
  open: boolean;
  onClose: () => void;
}

function summaryLines(summary: string | null | undefined): string[] {
  if (!summary) return [];
  return summary
    .split(/\n+/)
    .map((line) => line.trim())
    .filter(Boolean);
}

function formatSession(value: string | null) {
  if (!value) return "Unknown";
  return value
    .split(/[_\s-]+/)
    .filter(Boolean)
    .map((item) => item.charAt(0).toUpperCase() + item.slice(1))
    .join(" ");
}

function getActionColor(action: string) {
  return (
    ACTION_COLORS[action as keyof typeof ACTION_COLORS] ??
    "border-warning/30 bg-warning/10 text-warning"
  );
}

export function RunDetailModal({
  runSummary,
  run,
  isLoading,
  open,
  onClose,
}: RunDetailModalProps) {
  const headerRun = run ?? runSummary;
  if (!headerRun) return null;

  return (
    <Dialog open={open} onOpenChange={(next) => !next && onClose()}>
      <DialogContent className="max-h-[90vh] max-w-5xl overflow-hidden border-border bg-card p-0">
        <DialogHeader className="border-b border-border/50 px-6 py-4">
          <DialogTitle className="flex flex-wrap items-center gap-3 pr-8">
            <span>Agent Run</span>
            <Badge variant="outline" className="font-mono">
              {formatSession(headerRun.session)}
            </Badge>
            <span className="text-sm font-normal text-muted-foreground">
              {formatDateTimeET(headerRun.started_at)}
            </span>
          </DialogTitle>
        </DialogHeader>

        <div className="max-h-[calc(90vh-88px)] overflow-y-auto px-6 py-5">
          {isLoading ? (
            <div className="space-y-4">
              <Skeleton className="h-20 w-full" />
              <Skeleton className="h-16 w-full" />
              <Skeleton className="h-16 w-full" />
            </div>
          ) : !run ? (
            <div className="rounded-lg border border-border/50 bg-secondary/20 p-4 text-sm text-muted-foreground">
              Run details are unavailable.
            </div>
          ) : (
            <div className="space-y-6 pb-1">
            <div className="grid gap-3 md:grid-cols-4">
              <div className="rounded-lg border border-border/50 bg-secondary/20 p-3">
                <div className="text-xs text-muted-foreground">Status</div>
                <div className="mt-1 font-medium capitalize">{run.status}</div>
              </div>
              <div className="rounded-lg border border-border/50 bg-secondary/20 p-3">
                <div className="text-xs text-muted-foreground">Trades Made</div>
                <div className="mt-1 font-medium">
                  {run.held_all_positions
                    ? "0 trades - held all positions"
                    : run.trades_made}
                </div>
              </div>
              <div className="rounded-lg border border-border/50 bg-secondary/20 p-3">
                <div className="text-xs text-muted-foreground">Run Type</div>
                <div className="mt-1 font-medium">{formatSession(run.run_type)}</div>
              </div>
              <div className="rounded-lg border border-border/50 bg-secondary/20 p-3">
                <div className="text-xs text-muted-foreground">Completed</div>
                <div className="mt-1 font-medium">
                  {run.completed_at ? formatDateTimeET(run.completed_at) : "-"}
                </div>
              </div>
            </div>

            <div>
              <div className="mb-2 text-sm font-medium text-foreground">Summary</div>
              {summaryLines(run.summary).length > 0 ? (
                <div className="rounded-lg border border-border/50 bg-secondary/20 p-4">
                  <ul className="space-y-2 text-sm text-muted-foreground">
                    {summaryLines(run.summary).map((line, index) => (
                      <li key={index} className="wrap-break-word">
                        {line}
                      </li>
                    ))}
                  </ul>
                </div>
              ) : (
                <div className="rounded-lg border border-border/50 bg-secondary/20 p-4 text-sm text-muted-foreground">
                  No summary recorded.
                </div>
              )}
            </div>

            <div>
              <div className="mb-2 text-sm font-medium text-foreground">
                Evaluated Tickers
              </div>
              {run.evaluations.length === 0 ? (
                <div className="rounded-lg border border-border/50 bg-secondary/20 p-4 text-sm text-muted-foreground">
                  No per-ticker details were recorded for this run.
                </div>
              ) : (
                <Accordion type="single" collapsible className="rounded-lg border border-border/50">
                  {run.evaluations.map((item, index) => (
                    <AccordionItem
                      key={`${item.ticker}-${item.action}-${index}`}
                      value={`${item.ticker}-${index}`}
                      className="px-4"
                    >
                      <AccordionTrigger className="hover:no-underline">
                        <div className="flex flex-1 flex-wrap items-center gap-3 pr-4">
                          <span className="font-mono font-semibold text-foreground">
                            {item.ticker}
                          </span>
                          <Badge
                            variant="outline"
                            className={cn("font-mono", getActionColor(item.action))}
                          >
                            {item.action}
                          </Badge>
                          {item.transaction ? (
                            <span className="text-xs text-muted-foreground">
                              {formatShares(item.transaction.shares)} shares at{" "}
                              {formatCurrency(item.transaction.price_at_trade)}
                            </span>
                          ) : (
                            <span className="text-xs text-muted-foreground">
                              HOLD or no transaction executed
                            </span>
                          )}
                        </div>
                      </AccordionTrigger>
                      <AccordionContent className="space-y-4 pt-1">
                        <div>
                          <div className="mb-2 flex items-center gap-2 text-sm font-medium text-foreground">
                            <Bot className="h-4 w-4 text-primary" />
                            LLM Rationale
                          </div>
                          <div className="rounded-lg border border-border/50 bg-secondary/20 p-4 text-sm text-muted-foreground whitespace-pre-wrap wrap-break-word">
                            {item.llm_reasoning || item.summary_line || "No rationale recorded."}
                          </div>
                        </div>

                        <div>
                          <div className="mb-2 flex items-center gap-2 text-sm font-medium text-foreground">
                            <Wrench className="h-4 w-4 text-primary" />
                            Tools Called
                          </div>
                          <div className="rounded-lg border border-border/50 bg-secondary/20 p-4">
                            <pre className="overflow-x-auto whitespace-pre-wrap wrap-break-word text-xs text-muted-foreground">
                              {Object.keys(item.tools_called).length > 0
                                ? JSON.stringify(item.tools_called, null, 2)
                                : "No structured tool payload recorded."}
                            </pre>
                          </div>
                        </div>
                      </AccordionContent>
                    </AccordionItem>
                  ))}
                </Accordion>
              )}
            </div>
            </div>
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
}
