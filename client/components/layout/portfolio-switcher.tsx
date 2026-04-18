"use client";

import { useRouter } from "next/navigation";
import { Check, ChevronsUpDown, Plus, Briefcase } from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import {
  Command,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
  CommandSeparator,
} from "@/components/ui/command";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import type { Portfolio } from "@/lib/types";
import { useState } from "react";
import { formatCurrency } from "@/lib/format";

interface PortfolioSwitcherProps {
  portfolios: Portfolio[];
  currentPortfolioId?: string;
}

export function PortfolioSwitcher({
  portfolios,
  currentPortfolioId,
}: PortfolioSwitcherProps) {
  const router = useRouter();
  const [open, setOpen] = useState(false);

  const currentPortfolio = portfolios.find((p) => p.id === currentPortfolioId);

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <Button
          variant="outline"
          role="combobox"
          aria-expanded={open}
          className="w-[280px] justify-between bg-background/50"
        >
          <div className="flex items-center gap-2">
            <Briefcase className="h-4 w-4 text-muted-foreground" />
            <span className="truncate">
              {currentPortfolio?.name || "Select portfolio"}
            </span>
          </div>
          <ChevronsUpDown className="ml-2 h-4 w-4 shrink-0 opacity-50" />
        </Button>
      </PopoverTrigger>
      <PopoverContent className="w-[280px] p-0" align="start">
        <Command>
          <CommandInput placeholder="Search portfolios..." />
          <CommandList>
            <CommandEmpty>No portfolios found.</CommandEmpty>
            <CommandGroup heading="Portfolios">
              {portfolios.map((portfolio) => (
                <CommandItem
                  key={portfolio.id}
                  value={portfolio.name}
                  onSelect={() => {
                    router.push(`/dashboard/${portfolio.id}`);
                    setOpen(false);
                  }}
                  className="flex items-center justify-between"
                >
                  <div className="flex items-center gap-2">
                    <Check
                      className={cn(
                        "h-4 w-4",
                        currentPortfolioId === portfolio.id
                          ? "opacity-100"
                          : "opacity-0"
                      )}
                    />
                    <div>
                      <p className="font-medium">{portfolio.name}</p>
                      <p className="text-xs text-muted-foreground">
                        {formatCurrency(portfolio.total_value)}
                      </p>
                    </div>
                  </div>
                  <span
                    className={cn(
                      "text-xs font-mono",
                      portfolio.profit_loss >= 0
                        ? "text-profit"
                        : "text-loss"
                    )}
                  >
                    {portfolio.profit_loss >= 0 ? "+" : ""}
                    {portfolio.profit_loss_pct.toFixed(2)}%
                  </span>
                </CommandItem>
              ))}
            </CommandGroup>
            <CommandSeparator />
            <CommandGroup>
              <CommandItem
                onSelect={() => {
                  router.push("/portfolios/new");
                  setOpen(false);
                }}
              >
                <Plus className="mr-2 h-4 w-4" />
                Create New Portfolio
              </CommandItem>
            </CommandGroup>
          </CommandList>
        </Command>
      </PopoverContent>
    </Popover>
  );
}
