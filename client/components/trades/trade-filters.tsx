"use client";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Search, X } from "lucide-react";
import type { TransactionFilters } from "@/lib/types";

interface TradeFiltersProps {
  tickers: string[];
  filters: TransactionFilters;
  onFiltersChange: (filters: Partial<TransactionFilters>) => void;
}

export function TradeFilters({
  tickers,
  filters,
  onFiltersChange,
}: TradeFiltersProps) {
  const hasFilters =
    filters.ticker || filters.action || filters.search;

  const clearFilters = () => {
    onFiltersChange({
      ticker: undefined,
      action: undefined,
      search: undefined,
    });
  };

  return (
    <div className="flex flex-wrap items-center gap-3">
      <div className="relative flex-1 min-w-[200px]">
        <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
        <Input
          placeholder="Search reasoning..."
          value={filters.search || ""}
          onChange={(e) => onFiltersChange({ search: e.target.value || undefined })}
          className="pl-9 bg-background/50"
        />
      </div>

      <Select
        value={filters.ticker || "all"}
        onValueChange={(value) =>
          onFiltersChange({ ticker: value === "all" ? undefined : value })
        }
      >
        <SelectTrigger className="w-[140px] bg-background/50">
          <SelectValue placeholder="Ticker" />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="all">All Tickers</SelectItem>
          {tickers.map((ticker) => (
            <SelectItem key={ticker} value={ticker}>
              {ticker}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>

      <Select
        value={filters.action || "all"}
        onValueChange={(value) =>
          onFiltersChange({
            action:
              value === "all"
                ? undefined
                : (value as "BUY" | "SELL" | "HOLD"),
          })
        }
      >
        <SelectTrigger className="w-[120px] bg-background/50">
          <SelectValue placeholder="Action" />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="all">All</SelectItem>
          <SelectItem value="BUY">BUY</SelectItem>
          <SelectItem value="SELL">SELL</SelectItem>
          <SelectItem value="HOLD">HOLD</SelectItem>
        </SelectContent>
      </Select>

      {hasFilters && (
        <Button variant="ghost" size="sm" onClick={clearFilters}>
          <X className="h-4 w-4 mr-1" />
          Clear
        </Button>
      )}
    </div>
  );
}
