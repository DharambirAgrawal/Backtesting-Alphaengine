"use client";

import { useMemo, useState } from "react";
import { useParams } from "next/navigation";
import { ActivitySquare } from "lucide-react";
import { DashboardLayout } from "@/components/layout/dashboard-layout";
import { RunDetailModal } from "@/components/runs/run-detail-modal";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { useAgentRun, useAgentRunDetail } from "@/hooks/use-agent-run";
import { formatDateTimeET } from "@/lib/format";
import { cn } from "@/lib/utils";

function formatSession(value: string | null) {
  if (!value) return "Unknown";
  return value
    .split(/[_\s-]+/)
    .filter(Boolean)
    .map((item) => item.charAt(0).toUpperCase() + item.slice(1))
    .join(" ");
}

function statusClassName(status: string) {
  if (status === "done") return "border-profit/30 bg-profit/10 text-profit";
  if (status === "failed") return "border-loss/30 bg-loss/10 text-loss";
  if (status === "running") return "border-primary/30 bg-primary/10 text-primary";
  return "border-warning/30 bg-warning/10 text-warning";
}

export default function RunsPage() {
  const params = useParams();
  const portfolioId = params.portfolioId as string;
  const { runs, isRunning } = useAgentRun(portfolioId);
  const [selectedRunId, setSelectedRunId] = useState<string | null>(null);
  const selectedRun = useMemo(
    () => runs.find((run) => run.id === selectedRunId) ?? null,
    [runs, selectedRunId]
  );
  const { run: runDetail, isLoading: isDetailLoading } = useAgentRunDetail(
    portfolioId,
    selectedRunId
  );

  return (
    <DashboardLayout portfolioId={portfolioId}>
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-bold text-foreground">Agent Run History</h1>
          <p className="text-muted-foreground">
            Every automated and manual run for this portfolio, including the
            decisions made for each ticker.
          </p>
        </div>

        <Card className="bg-card/50 border-border/50">
          <CardHeader className="flex flex-row items-center justify-between border-b border-border/50">
            <CardTitle className="text-base font-medium">
              Runs
              <span className="ml-2 text-sm font-normal text-muted-foreground">
                ({runs.length} total)
              </span>
            </CardTitle>
            {isRunning && (
              <Badge variant="outline" className="border-primary/30 bg-primary/10 text-primary">
                Active run in progress
              </Badge>
            )}
          </CardHeader>
          <CardContent className="pt-4">
            {runs.length === 0 && !isRunning ? (
              <div className="flex min-h-[240px] flex-col items-center justify-center gap-3 text-center">
                <ActivitySquare className="h-10 w-10 text-muted-foreground" />
                <div>
                  <div className="font-medium text-foreground">No runs recorded yet</div>
                  <div className="text-sm text-muted-foreground">
                    Trigger the agent to start building run history.
                  </div>
                </div>
              </div>
            ) : runs.length === 0 ? (
              <div className="space-y-3">
                {Array.from({ length: 4 }).map((_, index) => (
                  <Skeleton key={index} className="h-12 w-full" />
                ))}
              </div>
            ) : (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Date / Time (ET)</TableHead>
                    <TableHead>Session</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead>Trades</TableHead>
                    <TableHead className="w-full">Summary</TableHead>
                    <TableHead className="text-right">Details</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {runs.map((run) => (
                    <TableRow key={run.id}>
                      <TableCell>{formatDateTimeET(run.started_at)}</TableCell>
                      <TableCell>
                        <Badge variant="outline" className="font-mono">
                          {formatSession(run.session)}
                        </Badge>
                      </TableCell>
                      <TableCell>
                        <Badge
                          variant="outline"
                          className={cn("capitalize", statusClassName(run.status))}
                        >
                          {run.status}
                        </Badge>
                      </TableCell>
                      <TableCell className="whitespace-normal">
                        {run.trades_made === 0 && run.status === "done"
                          ? "0 trades - held all positions"
                          : run.trades_made}
                      </TableCell>
                      <TableCell className="max-w-xl whitespace-normal text-sm text-muted-foreground">
                        <div className="line-clamp-3">
                          {run.summary || "No summary recorded."}
                        </div>
                      </TableCell>
                      <TableCell className="text-right">
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => setSelectedRunId(run.id)}
                        >
                          View Details
                        </Button>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            )}
          </CardContent>
        </Card>
      </div>

      <RunDetailModal
        runSummary={selectedRun}
        run={runDetail}
        isLoading={isDetailLoading}
        open={!!selectedRunId}
        onClose={() => setSelectedRunId(null)}
      />
    </DashboardLayout>
  );
}
