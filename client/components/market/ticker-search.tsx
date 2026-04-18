"use client";

import { useState, useEffect, useCallback } from "react";
import { Check, ChevronsUpDown, Loader2 } from "lucide-react";
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
import { searchTickers } from "@/lib/api";
import type { TickerSearchResult } from "@/lib/types";

interface TickerSearchProps {
  onSelect: (ticker: TickerSearchResult) => void;
  selectedTickers?: string[];
  placeholder?: string;
}

export function TickerSearch({
  onSelect,
  selectedTickers = [],
  placeholder = "Search tickers...",
}: TickerSearchProps) {
  const [open, setOpen] = useState(false);
  const [search, setSearch] = useState("");
  const [results, setResults] = useState<TickerSearchResult[]>([]);
  const [isLoading, setIsLoading] = useState(false);

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

  // Debounced search
  useEffect(() => {
    const timer = setTimeout(() => {
      fetchResults(search);
    }, 300);

    return () => clearTimeout(timer);
  }, [search, fetchResults]);

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <Button
          variant="outline"
          role="combobox"
          aria-expanded={open}
          className="w-full justify-between bg-background/50"
        >
          <span className="text-muted-foreground">{placeholder}</span>
          <ChevronsUpDown className="ml-2 h-4 w-4 shrink-0 opacity-50" />
        </Button>
      </PopoverTrigger>
      <PopoverContent className="w-[400px] p-0" align="start">
        <Command shouldFilter={false}>
          <CommandInput
            placeholder={placeholder}
            value={search}
            onValueChange={setSearch}
          />
          <CommandList>
            {isLoading && (
              <div className="flex items-center justify-center py-6">
                <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
              </div>
            )}
            {!isLoading && search.length > 0 && results.length === 0 && (
              <CommandEmpty>No tickers found.</CommandEmpty>
            )}
            {!isLoading && results.length > 0 && (
              <CommandGroup heading="Results">
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
                        setSearch("");
                        setOpen(false);
                      }}
                      disabled={isSelected}
                      className="flex items-center justify-between"
                    >
                      <div className="flex items-center gap-2">
                        <span className="font-mono font-semibold text-foreground">
                          {result.ticker}
                        </span>
                        <span className="text-sm text-muted-foreground truncate max-w-[200px]">
                          {result.name}
                        </span>
                      </div>
                      <div className="flex items-center gap-2">
                        <span className="text-xs text-muted-foreground">
                          {result.exchange}
                        </span>
                        {isSelected && (
                          <Check className="h-4 w-4 text-primary" />
                        )}
                      </div>
                    </CommandItem>
                  );
                })}
              </CommandGroup>
            )}
          </CommandList>
        </Command>
      </PopoverContent>
    </Popover>
  );
}
