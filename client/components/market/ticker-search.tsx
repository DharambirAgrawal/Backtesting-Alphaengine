"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import { Search, Check, Loader2, Plus } from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import {
  Command,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
} from "@/components/ui/command";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import { Badge } from "@/components/ui/badge";
import { searchTickers } from "@/lib/api";
import type { TickerSearchResult } from "@/lib/types";

interface TickerSearchProps {
  onSelect: (ticker: TickerSearchResult) => void;
  selectedTickers?: string[];
  placeholder?: string;
  disabled?: boolean;
}

export function TickerSearch({
  onSelect,
  selectedTickers = [],
  placeholder = "Search stocks by name or ticker...",
  disabled = false,
}: TickerSearchProps) {
  const [open, setOpen] = useState(false);
  const [search, setSearch] = useState("");
  const [results, setResults] = useState<TickerSearchResult[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const triggerRef = useRef<HTMLButtonElement>(null);

  const fetchResults = useCallback(async (query: string) => {
    if (query.length < 1) {
      setResults([]);
      return;
    }

    setIsLoading(true);
    try {
      const data = await searchTickers(query);
      setResults(data);
    } catch {
      setResults([]);
    } finally {
      setIsLoading(false);
    }
  }, []);

  // Debounce: 280ms feels snappy without hammering the API
  useEffect(() => {
    const timer = setTimeout(() => {
      fetchResults(search);
    }, 280);
    return () => clearTimeout(timer);
  }, [search, fetchResults]);

  // Reset search when popover closes
  useEffect(() => {
    if (!open) {
      setSearch("");
      setResults([]);
    }
  }, [open]);

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <Button
          ref={triggerRef}
          variant="outline"
          role="button"
          aria-expanded={open}
          disabled={disabled}
          className={cn(
            "w-full justify-start gap-2 bg-background/50 border-border/60",
            "hover:border-primary/40 hover:bg-background/80 transition-all duration-200",
            "text-muted-foreground font-normal"
          )}
        >
          <Search className="h-4 w-4 shrink-0 text-muted-foreground/60" />
          <span>{placeholder}</span>
        </Button>
      </PopoverTrigger>

      <PopoverContent
        className="p-0 shadow-xl shadow-black/30 border-border/60"
        style={{
          width: triggerRef.current
            ? `${triggerRef.current.offsetWidth}px`
            : "400px",
          minWidth: "320px",
        }}
        align="start"
        sideOffset={6}
      >
        <Command shouldFilter={false}>
          <div className="flex items-center border-b border-border/50 px-3">
            <Search className="h-4 w-4 shrink-0 text-muted-foreground/50 mr-2" />
            <CommandInput
              placeholder="Type ticker or company name..."
              value={search}
              onValueChange={setSearch}
              className="border-0 focus:ring-0 py-3"
            />
            {isLoading && (
              <Loader2 className="h-4 w-4 animate-spin text-muted-foreground/60 shrink-0" />
            )}
          </div>

          <CommandList className="max-h-72">
            {/* Empty state */}
            {!isLoading && search.length > 0 && results.length === 0 && (
              <CommandEmpty className="py-8 text-center">
                <p className="text-sm text-muted-foreground">
                  No results for &quot;{search}&quot;
                </p>
                <p className="text-xs text-muted-foreground/60 mt-1">
                  Try an exact symbol like AAPL, TSLA, NVDA
                </p>
              </CommandEmpty>
            )}

            {/* Prompt state — nothing typed yet */}
            {!isLoading && search.length === 0 && (
              <div className="py-6 text-center">
                <p className="text-xs text-muted-foreground/60">
                  Search by company name or ticker symbol
                </p>
              </div>
            )}

            {/* Results */}
            {!isLoading && results.length > 0 && (
              <CommandGroup>
                {results.map((result) => {
                  const isSelected = selectedTickers.includes(result.ticker);
                  return (
                    <CommandItem
                      key={result.ticker}
                      value={result.ticker}
                      onSelect={() => {
                        if (!isSelected) {
                          onSelect(result);
                        }
                        setOpen(false);
                      }}
                      disabled={isSelected}
                      className={cn(
                        "flex items-center justify-between px-3 py-2.5 cursor-pointer",
                        "transition-colors duration-100",
                        isSelected && "opacity-50 cursor-not-allowed"
                      )}
                    >
                      {/* Left: symbol + company name */}
                      <div className="flex items-center gap-3 min-w-0">
                        <span className="font-mono font-bold text-sm text-foreground shrink-0">
                          {result.ticker}
                        </span>
                        <span className="text-sm text-muted-foreground truncate">
                          {result.name}
                        </span>
                      </div>

                      {/* Right: exchange badge + check */}
                      <div className="flex items-center gap-2 shrink-0 ml-2">
                        {result.exchange && (
                          <Badge
                            variant="outline"
                            className="text-xs px-1.5 py-0 h-5 font-normal border-border/50 text-muted-foreground/70 bg-transparent"
                          >
                            {result.exchange}
                          </Badge>
                        )}
                        {isSelected ? (
                          <Check className="h-3.5 w-3.5 text-primary" />
                        ) : (
                          <Plus className="h-3.5 w-3.5 text-muted-foreground/40" />
                        )}
                      </div>
                    </CommandItem>
                  );
                })}
              </CommandGroup>
            )}
          </CommandList>

          {/* Footer hint */}
          {results.length > 0 && (
            <div className="border-t border-border/40 px-3 py-1.5">
              <p className="text-xs text-muted-foreground/50">
                {results.length} result{results.length !== 1 ? "s" : ""} · Click to add
              </p>
            </div>
          )}
        </Command>
      </PopoverContent>
    </Popover>
  );
}
