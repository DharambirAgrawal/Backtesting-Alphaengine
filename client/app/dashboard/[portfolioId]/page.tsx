"use client";

import { useState } from "react";
import { useParams } from "next/navigation";
import { DashboardLayout } from "@/components/layout/dashboard-layout";
import { PortfolioValueCard } from "@/components/dashboard/portfolio-value-card";
import { StatsCard } from "@/components/dashboard/stats-card";
import { AgentStatusBadge } from "@/components/dashboard/agent-status-badge";
import { ValueChart } from "@/components/dashboard/value-chart";
import { HoldingsTable } from "@/components/dashboard/holdings-table";
import { RecentTrades } from "@/components/dashboard/recent-trades";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { useDashboard, useChartData } from "@/hooks/use-dashboard";
import { useAgentRun } from "@/hooks/use-agent-run";
import { formatCurrency, formatPct, formatNumber } from "@/lib/format";
import { Play, Pause, RefreshCw } from "lucide-react";
import { toast } from "sonner";

export default function PortfolioDashboardPage() {
  const params = useParams();
  const portfolioId = params.portfolioId as string;
  const [chartPeriod, setChartPeriod] = useState("1M");

  const { dashboard, isLoading, refresh } = useDashboard(portfolioId);
  const { chartData, isLoading: isChartLoading } = useChartData(
    portfolioId,
    chartPeriod
  );
  const { isRunning, run, pause, resume } = useAgentRun(portfolioId);

  const handleRunAgent = async () => {
    try {
      await run();
      toast.success("Agent run started", {
        description: "The agent is analyzing the market and making decisions.",
      });
      // We no longer need setTimeout; the agent run hook has SWR polling.
      // SWR will pick up the running state and the completed state automatically.
    } catch {
      toast.error("Failed to start agent run");
    }
  };

  const handleTogglePause = async () => {
    try {
      if (dashboard?.portfolio.is_active) {
        await pause();
        toast.success("Agent paused", {
          description: "Scheduled runs are now paused.",
        });
      } else {
        await resume();
        toast.success("Agent resumed", {
          description: "Scheduled runs will continue.",
        });
      }
      refresh();
    } catch {
      toast.error("Failed to update agent status");
    }
  };

  const agentStatus = isRunning
    ? "running"
    : dashboard?.portfolio.is_active
    ? "active"
    : "paused";

  return (
    <DashboardLayout portfolioId={portfolioId}>
      <div className="space-y-6">
        {/* Top Bar */}
        <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex items-center gap-4">
            <AgentStatusBadge
              status={agentStatus}
              nextRun={dashboard?.next_run}
              timezoneLabel="ET"
            />
          </div>
          <div className="flex w-full flex-col gap-2 sm:w-auto sm:flex-row sm:items-center">
            <Button
              variant="outline"
              size="sm"
              onClick={handleTogglePause}
              disabled={isRunning}
              className="w-full sm:w-auto"
            >
              {dashboard?.portfolio.is_active ? (
                <>
                  <Pause className="h-4 w-4" />
                  Pause
                </>
              ) : (
                <>
                  <Play className="h-4 w-4" />
                  Resume
                </>
              )}
            </Button>
            <Button
              size="sm"
              onClick={handleRunAgent}
              disabled={isRunning}
              className="w-full sm:w-auto"
            >
              {isRunning ? (
                <>
                  <RefreshCw className="h-4 w-4 animate-spin" />
                  Running...
                </>
              ) : (
                <>
                  <Play className="h-4 w-4" />
                  Run Now
                </>
              )}
            </Button>
          </div>
        </div>

        {/* Summary Stats Row */}
        {isLoading ? (
          <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
            {[1, 2, 3, 4].map((i) => (
              <Skeleton key={i} className="h-24" />
            ))}
          </div>
        ) : dashboard ? (
          <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
            <PortfolioValueCard
              totalValue={dashboard.portfolio.total_value}
              profitLoss={dashboard.portfolio.profit_loss}
              profitLossPct={dashboard.portfolio.profit_loss_pct}
            />
            <StatsCard
              label="Available Cash"
              value={formatCurrency(dashboard.portfolio.current_cash)}
              subValue={`${formatPct(
                (dashboard.portfolio.current_cash /
                  dashboard.portfolio.total_value) *
                  100,
                { showSign: false }
              )} of portfolio`}
            />
            <StatsCard
              label="Holdings Value"
              value={formatCurrency(dashboard.portfolio.holdings_value)}
              subValue={`Across ${dashboard.holdings.length} positions`}
            />
            <StatsCard
              label="Win Rate"
              value={formatPct(dashboard.performance.win_rate * 100, {
                showSign: false,
              })}
              subValue={`${dashboard.performance.profitable_trades} of ${dashboard.performance.total_trades} sells`}
              trend={dashboard.performance.win_rate >= 0.5 ? "up" : "down"}
            />
          </div>
        ) : null}

        {/* Performance Row */}
        {isLoading ? (
          <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
            {[1, 2, 3].map((i) => (
              <Skeleton key={i} className="h-24" />
            ))}
          </div>
        ) : dashboard ? (
          <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
            <StatsCard
              label="Sharpe Ratio"
              value={formatNumber(dashboard.performance.sharpe_ratio, {
                decimals: 2,
              })}
              subValue={
                dashboard.performance.sharpe_ratio >= 1 ? "Good" : "Low"
              }
              trend={dashboard.performance.sharpe_ratio >= 1 ? "up" : "neutral"}
            />
            <StatsCard
              label="Max Drawdown"
              value={formatPct(dashboard.performance.max_drawdown_pct)}
              trend="down"
            />
            <StatsCard
              label="Best Trade"
              value={
                dashboard.performance.best_trade.gain_pct !== undefined
                  ? `${dashboard.performance.best_trade.ticker} ${formatPct(
                      dashboard.performance.best_trade.gain_pct
                    )}`
                  : dashboard.performance.best_trade.ticker
              }
              trend="up"
            />
          </div>
        ) : null}

        {/* Chart */}
        <ValueChart
          data={chartData}
          period={chartPeriod}
          onPeriodChange={setChartPeriod}
          isLoading={isChartLoading}
        />

        {/* Two Column Layout */}
        <div className="grid gap-6 lg:grid-cols-2">
          <HoldingsTable
            holdings={dashboard?.holdings ?? []}
            isLoading={isLoading}
          />
          <RecentTrades
            transactions={dashboard?.recent_transactions ?? []}
            portfolioId={portfolioId}
            isLoading={isLoading}
          />
        </div>
      </div>
    </DashboardLayout>
  );
}
