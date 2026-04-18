"use client";

import { useMemo } from "react";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from "recharts";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { useModelAccuracy } from "@/hooks/use-models";
import { MODEL_TYPES, CHART_COLORS } from "@/lib/constants";
import { formatCurrency, formatDate } from "@/lib/format";
import { Skeleton } from "@/components/ui/skeleton";

interface AccuracyChartProps {
  ticker: string | null;
  modelType: string | null;
  open: boolean;
  onClose: () => void;
}

export function AccuracyChart({
  ticker,
  modelType,
  open,
  onClose,
}: AccuracyChartProps) {
  const { accuracy, isLoading } = useModelAccuracy(ticker, modelType);

  const chartData = useMemo(() => {
    if (!accuracy) return [];
    return accuracy.dates.map((date, i) => ({
      date,
      predicted: accuracy.predicted[i],
      actual: accuracy.actual[i],
    }));
  }, [accuracy]);

  return (
    <Dialog open={open} onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="max-w-3xl bg-card border-border">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <span className="font-mono font-bold">{ticker}</span>
            <span className="text-muted-foreground font-normal">
              {modelType && MODEL_TYPES[modelType as keyof typeof MODEL_TYPES]}{" "}
              Accuracy
            </span>
          </DialogTitle>
        </DialogHeader>

        <div className="mt-4">
          {isLoading ? (
            <Skeleton className="h-[300px] w-full" />
          ) : chartData.length === 0 ? (
            <div className="flex h-[300px] items-center justify-center text-muted-foreground">
              No accuracy data available
            </div>
          ) : (
            <ResponsiveContainer width="100%" height={300}>
              <LineChart
                data={chartData}
                margin={{ top: 10, right: 10, left: 0, bottom: 0 }}
              >
                <XAxis
                  dataKey="date"
                  axisLine={false}
                  tickLine={false}
                  tick={{ fill: "#94a3b8", fontSize: 12 }}
                  tickFormatter={(value) => formatDate(value)}
                  interval="preserveStartEnd"
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
                          <p className="text-xs text-muted-foreground mb-2">
                            {formatDate(data.date, "long")}
                          </p>
                          <div className="space-y-1">
                            <div className="flex items-center gap-2">
                              <div
                                className="h-2 w-2 rounded-full"
                                style={{ background: CHART_COLORS.primary }}
                              />
                              <span className="text-sm">
                                Predicted:{" "}
                                <span className="font-mono font-medium">
                                  {formatCurrency(data.predicted)}
                                </span>
                              </span>
                            </div>
                            <div className="flex items-center gap-2">
                              <div
                                className="h-2 w-2 rounded-full"
                                style={{ background: CHART_COLORS.green }}
                              />
                              <span className="text-sm">
                                Actual:{" "}
                                <span className="font-mono font-medium">
                                  {formatCurrency(data.actual)}
                                </span>
                              </span>
                            </div>
                          </div>
                        </div>
                      );
                    }
                    return null;
                  }}
                />
                <Legend
                  wrapperStyle={{ paddingTop: 16 }}
                  formatter={(value) => (
                    <span className="text-sm text-muted-foreground">{value}</span>
                  )}
                />
                <Line
                  type="monotone"
                  dataKey="predicted"
                  name="Predicted"
                  stroke={CHART_COLORS.primary}
                  strokeWidth={2}
                  dot={false}
                  animationDuration={750}
                />
                <Line
                  type="monotone"
                  dataKey="actual"
                  name="Actual"
                  stroke={CHART_COLORS.green}
                  strokeWidth={2}
                  dot={false}
                  animationDuration={750}
                />
              </LineChart>
            </ResponsiveContainer>
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
}
