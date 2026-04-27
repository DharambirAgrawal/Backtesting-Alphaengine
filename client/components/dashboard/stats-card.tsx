"use client";

import { cn } from "@/lib/utils";
import { Card, CardContent } from "@/components/ui/card";
import { TrendingUp, TrendingDown, Minus } from "lucide-react";

interface StatsCardProps {
  label: string;
  value: string;
  subValue?: string;
  trend?: "up" | "down" | "neutral";
  className?: string;
}

export function StatsCard({
  label,
  value,
  subValue,
  trend,
  className,
}: StatsCardProps) {
  return (
    <Card className={cn("bg-card/50 border-border/50", className)}>
      <CardContent className="p-4">
        <p className="text-sm text-muted-foreground">{label}</p>
        <p className="mt-1 break-words text-xl font-semibold font-mono text-foreground sm:text-2xl">
          {value}
        </p>
        {subValue && (
          <div className="mt-1 flex items-start gap-1">
            {trend === "up" && (
              <TrendingUp className="h-3 w-3 text-profit" />
            )}
            {trend === "down" && (
              <TrendingDown className="h-3 w-3 text-loss" />
            )}
            {trend === "neutral" && (
              <Minus className="h-3 w-3 text-muted-foreground" />
            )}
            <span
              className={cn(
                "text-sm font-mono leading-snug break-words",
                trend === "up" && "text-profit",
                trend === "down" && "text-loss",
                trend === "neutral" && "text-muted-foreground"
              )}
            >
              {subValue}
            </span>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
