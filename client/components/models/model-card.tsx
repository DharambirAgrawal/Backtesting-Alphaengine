"use client";

import { cn } from "@/lib/utils";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { RelativeDate } from "@/components/ui/relative-date";
import { MODEL_TYPES } from "@/lib/constants";
import { formatNumber } from "@/lib/format";
import type { MLModel } from "@/lib/types";
import { RefreshCw, TrendingUp, Database, Clock } from "lucide-react";

interface ModelCardProps {
  model: MLModel;
  isRetraining: boolean;
  onRetrain: () => void;
  onViewAccuracy: () => void;
}

export function ModelCard({
  model,
  isRetraining,
  onRetrain,
  onViewAccuracy,
}: ModelCardProps) {
  // Backend returns accuracy as 0-1 (e.g. 0.68). Convert to 0-100 for display.
  const accuracyPct =
    model.accuracy <= 1 ? model.accuracy * 100 : model.accuracy;

  const accuracyColor =
    accuracyPct >= 70
      ? "text-profit"
      : accuracyPct >= 50
      ? "text-warning"
      : "text-loss";

  const progressColor =
    accuracyPct >= 70
      ? "bg-profit"
      : accuracyPct >= 50
      ? "bg-warning"
      : "bg-loss";

  return (
    <Card className="bg-card/50 border-border/50">
      <CardContent className="p-4">
        <div className="flex items-start justify-between mb-3">
          <div>
            <h3 className="font-mono font-bold text-lg text-foreground">
              {model.ticker}
            </h3>
            <p className="text-sm text-muted-foreground">
              {MODEL_TYPES[model.model_type]}
            </p>
          </div>
          <div
            className={cn(
              "flex h-2 w-2 rounded-full",
              model.is_active ? "bg-profit" : "bg-muted-foreground"
            )}
          />
        </div>

        {/* Accuracy */}
        <div className="mb-4">
          <div className="flex items-center justify-between mb-1">
            <span className="text-sm text-muted-foreground">Accuracy</span>
            <span className={cn("font-mono font-semibold", accuracyColor)}>
              {formatNumber(accuracyPct, { decimals: 0 })}%
            </span>
          </div>
          <div className="h-2 rounded-full bg-secondary overflow-hidden">
            <div
              className={cn("h-full rounded-full transition-all", progressColor)}
              style={{ width: `${Math.min(100, Math.max(0, accuracyPct))}%` }}
            />
          </div>
        </div>

        {/* Stats */}
        <div className="space-y-2 mb-4">
          <div className="flex items-center gap-2 text-sm">
            <Clock className="h-3.5 w-3.5 text-muted-foreground" />
            <span className="text-muted-foreground">Trained:</span>
            <RelativeDate value={model.trained_at} className="text-foreground" />
          </div>
          <div className="flex items-center gap-2 text-sm">
            <Database className="h-3.5 w-3.5 text-muted-foreground" />
            <span className="text-muted-foreground">Training rows:</span>
            <span className="text-foreground font-mono">
              {model.training_rows.toLocaleString()}
            </span>
          </div>
          <div className="flex items-center gap-2 text-sm">
            <TrendingUp className="h-3.5 w-3.5 text-muted-foreground" />
            <span className="text-muted-foreground">Status:</span>
            <span
              className={cn(
                "font-medium",
                model.is_active ? "text-profit" : "text-muted-foreground"
              )}
            >
              {model.is_active ? "Active" : "Inactive"}
            </span>
          </div>
        </div>

        {/* Actions */}
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={onRetrain}
            disabled={isRetraining}
            className="flex-1"
          >
            {isRetraining ? (
              <>
                <RefreshCw className="h-3.5 w-3.5 animate-spin" />
                Retraining...
              </>
            ) : (
              <>
                <RefreshCw className="h-3.5 w-3.5" />
                Retrain
              </>
            )}
          </Button>
          <Button
            variant="ghost"
            size="sm"
            onClick={onViewAccuracy}
            className="flex-1"
          >
            View Accuracy
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
