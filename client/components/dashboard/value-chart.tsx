"use client";

import { useMemo } from "react";
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { CHART_PERIODS, CHART_COLORS } from "@/lib/constants";
import { formatCurrency, formatDate } from "@/lib/format";
import type { ChartData } from "@/lib/types";
import { Skeleton } from "@/components/ui/skeleton";

interface ValueChartProps {
  data?: ChartData;
  period: string;
  onPeriodChange: (period: string) => void;
  isLoading?: boolean;
}

export function ValueChart({
  data,
  period,
  onPeriodChange,
  isLoading,
}: ValueChartProps) {
  const chartData = useMemo(() => {
    if (!data) return [];
    return data.labels.map((label, i) => ({
      date: label,
      value: data.total_value[i],
      cash: data.cash[i],
    }));
  }, [data]);

  const isPositive =
    chartData.length > 0 &&
    chartData[chartData.length - 1].value >= chartData[0].value;

  const gradientColor = isPositive ? CHART_COLORS.green : CHART_COLORS.red;
  const lineColor = CHART_COLORS.primary;
  const chartHeight = 260;

  return (
    <Card className="bg-card/50 border-border/50">
      <CardHeader className="flex flex-col gap-3 pb-2 sm:flex-row sm:items-center sm:justify-between">
        <CardTitle className="text-base font-medium">Portfolio Value</CardTitle>
        <Tabs value={period} onValueChange={onPeriodChange}>
          <TabsList className="h-8 w-full justify-start overflow-x-auto bg-secondary/50 sm:w-auto">
            {CHART_PERIODS.map((p) => (
              <TabsTrigger
                key={p.value}
                value={p.value}
                className="h-7 shrink-0 px-3 text-xs data-[state=active]:bg-primary data-[state=active]:text-primary-foreground"
              >
                {p.label}
              </TabsTrigger>
            ))}
          </TabsList>
        </Tabs>
      </CardHeader>
      <CardContent>
        {isLoading ? (
          <Skeleton className="h-[260px] w-full sm:h-[300px]" />
        ) : (
          <ResponsiveContainer width="100%" height={chartHeight}>
            <AreaChart
              data={chartData}
              margin={{ top: 10, right: 10, left: 0, bottom: 0 }}
            >
              <defs>
                <linearGradient id="colorValue" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor={gradientColor} stopOpacity={0.3} />
                  <stop offset="95%" stopColor={gradientColor} stopOpacity={0} />
                </linearGradient>
              </defs>
              <XAxis
                dataKey="date"
                axisLine={false}
                tickLine={false}
                tick={{ fill: "#94a3b8", fontSize: 12 }}
                tickFormatter={(value) => formatDate(value)}
                interval="preserveStartEnd"
                minTickGap={24}
              />
              <YAxis
                axisLine={false}
                tickLine={false}
                tick={{ fill: "#94a3b8", fontSize: 12 }}
                tickFormatter={(value) =>
                  formatCurrency(value, { compact: true })
                }
                domain={["auto", "auto"]}
                width={70}
              />
              <Tooltip
                content={({ active, payload }) => {
                  if (active && payload && payload.length) {
                    const data = payload[0].payload;
                    return (
                      <div className="rounded-lg border border-border bg-card p-3 shadow-lg">
                        <p className="text-xs text-muted-foreground">
                          {formatDate(data.date, "long")}
                        </p>
                        <p className="mt-1 text-lg font-mono font-semibold text-foreground">
                          {formatCurrency(data.value)}
                        </p>
                        <p className="text-xs text-muted-foreground">
                          Cash: {formatCurrency(data.cash)}
                        </p>
                      </div>
                    );
                  }
                  return null;
                }}
              />
              <Area
                type="monotone"
                dataKey="value"
                stroke={lineColor}
                strokeWidth={2}
                fill="url(#colorValue)"
                animationDuration={750}
              />
            </AreaChart>
          </ResponsiveContainer>
        )}
      </CardContent>
    </Card>
  );
}
