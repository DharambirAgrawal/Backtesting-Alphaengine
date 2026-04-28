"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { DashboardLayout } from "@/components/layout/dashboard-layout";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  CardDescription,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Field, FieldLabel } from "@/components/ui/field";
import { Switch } from "@/components/ui/switch";
import { Badge } from "@/components/ui/badge";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog";
import { TickerSearch } from "@/components/market/ticker-search";
import { usePortfolio } from "@/hooks/use-portfolio";
import {
  updatePortfolio,
  deletePortfolio,
  addTickers,
  removeTicker,
  depositToPortfolio,
  withdrawFromPortfolio,
} from "@/lib/api";
import { formatCurrency, formatDate } from "@/lib/format";
import { toast } from "sonner";
import { Skeleton } from "@/components/ui/skeleton";
import { X, Loader2, Trash2, Save } from "lucide-react";
import type { TickerSearchResult } from "@/lib/types";

export default function PortfolioSettingsPage() {
  const params = useParams();
  const router = useRouter();
  const portfolioId = params.portfolioId as string;

  const { portfolio, isLoading, refresh } = usePortfolio(portfolioId);

  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [isActive, setIsActive] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);
  const [isAddingTicker, setIsAddingTicker] = useState(false);
  const [removingTicker, setRemovingTicker] = useState<string | null>(null);
  const [localTickers, setLocalTickers] = useState<string[]>([]);
  const [cashAmount, setCashAmount] = useState("");
  const [isProcessingCash, setIsProcessingCash] = useState(false);
  // Preserve company names returned from search so badges show "AAPL · Apple Inc."
  const [tickerNameMap, setTickerNameMap] = useState<Record<string, string>>({});

  useEffect(() => {
    if (!portfolio) {
      return;
    }

    setName(portfolio.name);
    setDescription(portfolio.description || "");
    setIsActive(portfolio.is_active);
    setLocalTickers(portfolio.tickers || []);
  }, [portfolio]);

  const handleSave = async () => {
    setIsSaving(true);
    try {
      await updatePortfolio(portfolioId, {
        name: name.trim(),
        description: description.trim() || undefined,
        is_active: isActive,
      });
      toast.success("Settings saved");
      await refresh();
    } catch (error) {
      toast.error("Failed to save settings", {
        description:
          error instanceof Error ? error.message : "Please try again.",
      });
    } finally {
      setIsSaving(false);
    }
  };

  const handleAddTicker = async (ticker: TickerSearchResult) => {
    setIsAddingTicker(true);
    try {
      setLocalTickers((prev) =>
        prev.includes(ticker.ticker) ? prev : [...prev, ticker.ticker]
      );
      // Store the company name so the badge can display it
      if (ticker.name && ticker.name !== ticker.ticker) {
        setTickerNameMap((prev) => ({ ...prev, [ticker.ticker]: ticker.name }));
      }
      await addTickers(portfolioId, [ticker.ticker]);
      toast.success(`Added ${ticker.ticker}`, {
        description: ticker.name !== ticker.ticker ? ticker.name : "Training models...",
      });
      await refresh();
    } catch (error) {
      setLocalTickers((prev) => prev.filter((t) => t !== ticker.ticker));
      toast.error(`Failed to add ${ticker.ticker}`, {
        description:
          error instanceof Error ? error.message : "Please try again.",
      });
    } finally {
      setIsAddingTicker(false);
    }
  };

  const handleRemoveTicker = async (ticker: string) => {
    setRemovingTicker(ticker);
    try {
      setLocalTickers((items) => items.filter((t) => t !== ticker));
      await removeTicker(portfolioId, ticker);
      toast.success(`Removed ${ticker}`);
      await refresh();
    } catch (error) {
      setLocalTickers(portfolio?.tickers ?? []);
      toast.error(`Failed to remove ${ticker}`, {
        description:
          error instanceof Error ? error.message : "Please close the position first.",
      });
    } finally {
      setRemovingTicker(null);
    }
  };

  const handleDelete = async () => {
    setIsDeleting(true);
    try {
      await deletePortfolio(portfolioId);
      toast.success("Portfolio deleted");
      router.replace("/dashboard");
    } catch (error) {
      toast.error("Failed to delete portfolio", {
        description:
          error instanceof Error ? error.message : "Please try again.",
      });
      setIsDeleting(false);
    }
  };

  if (isLoading) {
    return (
      <DashboardLayout portfolioId={portfolioId}>
        <div className="mx-auto max-w-2xl space-y-6">
          <Skeleton className="h-48" />
          <Skeleton className="h-48" />
        </div>
      </DashboardLayout>
    );
  }

  return (
    <DashboardLayout portfolioId={portfolioId}>
      <div className="mx-auto max-w-2xl space-y-6">
        <div>
          <h1 className="text-2xl font-bold text-foreground">
            Portfolio Settings
          </h1>
          <p className="text-muted-foreground">
            Manage your portfolio configuration
          </p>
        </div>

        {/* General Settings */}
        <Card className="bg-card/50 border-border/50">
          <CardHeader>
            <CardTitle className="text-base">General</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <Field>
              <FieldLabel htmlFor="name">Portfolio Name</FieldLabel>
              <Input
                id="name"
                value={name}
                onChange={(e) => setName(e.target.value)}
                className="bg-background/50"
              />
            </Field>

            <Field>
              <FieldLabel htmlFor="description">Description</FieldLabel>
              <Textarea
                id="description"
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                className="bg-background/50 resize-none"
                rows={3}
              />
            </Field>

            <div className="flex items-center justify-between">
              <div>
                <p className="font-medium">Agent Status</p>
                <p className="text-sm text-muted-foreground">
                  {isActive
                    ? "Agent will run on schedule"
                    : "Agent runs are paused"}
                </p>
              </div>
              <Switch checked={isActive} onCheckedChange={setIsActive} />
            </div>

            <Button onClick={handleSave} disabled={isSaving}>
              {isSaving ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" />
                  Saving...
                </>
              ) : (
                <>
                  <Save className="h-4 w-4" />
                  Save Changes
                </>
              )}
            </Button>
          </CardContent>
        </Card>

        {/* Tickers */}
        <Card className="bg-card/50 border-border/50">
          <CardHeader>
            <CardTitle className="text-base">Tickers</CardTitle>
            <CardDescription>
              Add or remove tickers from this portfolio
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <TickerSearch
              onSelect={handleAddTicker}
              selectedTickers={localTickers}
              placeholder="Add a ticker..."
            />

            {isAddingTicker && (
              <p className="text-sm text-muted-foreground flex items-center gap-2">
                <Loader2 className="h-3 w-3 animate-spin" />
                Adding ticker and training models...
              </p>
            )}

            {localTickers.length > 0 && (
              <div className="flex flex-wrap gap-2">
                {localTickers.map((ticker) => {
                  const companyName = tickerNameMap[ticker];
                  return (
                    <Badge
                      key={ticker}
                      variant="outline"
                      className="px-3 py-1.5 text-sm bg-secondary/30 transition-all duration-150"
                    >
                      <span className="font-mono font-semibold">
                        {ticker}
                      </span>
                      {companyName && (
                        <span className="text-muted-foreground text-xs ml-1.5 mr-1">
                          · {companyName.length > 22 ? companyName.slice(0, 22) + "…" : companyName}
                        </span>
                      )}
                      <button
                        onClick={() => handleRemoveTicker(ticker)}
                        disabled={removingTicker === ticker}
                        className="ml-1.5 text-muted-foreground hover:text-foreground disabled:opacity-50 transition-colors"
                      >
                        {removingTicker === ticker ? (
                          <Loader2 className="h-3 w-3 animate-spin" />
                        ) : (
                          <X className="h-3 w-3" />
                        )}
                      </button>
                    </Badge>
                  );
                })}
              </div>
            )}
          </CardContent>
        </Card>

        {/* Capital Info */}
        <Card className="bg-card/50 border-border/50">
          <CardHeader>
            <CardTitle className="text-base">Capital History</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3 text-sm">
              <div className="flex justify-between">
                <span className="text-muted-foreground">Starting Capital</span>
                <span className="font-mono font-medium">
                  {formatCurrency(portfolio?.starting_capital ?? 0)}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Current Value</span>
                <span className="font-mono font-medium">
                  {formatCurrency(portfolio?.total_value ?? 0)}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Created</span>
                <span>
                  {portfolio?.created_at
                    ? formatDate(portfolio.created_at, "long")
                    : "-"}
                </span>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Deposit / Withdraw */}
        <Card className="bg-card/50 border-border/50">
          <CardHeader>
            <CardTitle className="text-base">Adjust Cash</CardTitle>
            <CardDescription>
              Deposit or withdraw cash from this portfolio. Deposits increase
              starting capital so performance metrics remain comparable.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex gap-2">
              <Input
                placeholder="Amount (e.g. 1000.00)"
                value={cashAmount}
                onChange={(e) => setCashAmount(e.target.value)}
                className="w-full bg-background/50"
                inputMode="decimal"
              />
              <Button
                onClick={async () => {
                  const amt = parseFloat(cashAmount);
                  if (isNaN(amt) || amt <= 0) {
                    toast.error("Enter a valid amount to deposit");
                    return;
                  }
                  setIsProcessingCash(true);
                  try {
                    await depositToPortfolio(portfolioId, amt);
                    toast.success(`Deposited ${formatCurrency(amt)}`);
                    setCashAmount("");
                    await refresh();
                  } catch (err) {
                    toast.error("Deposit failed", { description: err instanceof Error ? err.message : undefined });
                  } finally {
                    setIsProcessingCash(false);
                  }
                }}
                disabled={isProcessingCash}
              >
                Deposit
              </Button>
              <Button
                variant="outline"
                onClick={async () => {
                  const amt = parseFloat(cashAmount);
                  if (isNaN(amt) || amt <= 0) {
                    toast.error("Enter a valid amount to withdraw");
                    return;
                  }
                  setIsProcessingCash(true);
                  try {
                    await withdrawFromPortfolio(portfolioId, amt);
                    toast.success(`Withdrew ${formatCurrency(amt)}`);
                    setCashAmount("");
                    await refresh();
                  } catch (err) {
                    toast.error("Withdrawal failed", { description: err instanceof Error ? err.message : undefined });
                  } finally {
                    setIsProcessingCash(false);
                  }
                }}
                disabled={isProcessingCash}
              >
                Withdraw
              </Button>
            </div>
          </CardContent>
        </Card>

        {/* Danger Zone */}
        <Card className="bg-card/50 border-destructive/30">
          <CardHeader>
            <CardTitle className="text-base text-destructive">
              Danger Zone
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex items-center justify-between">
              <div>
                <p className="font-medium">Delete Portfolio</p>
                <p className="text-sm text-muted-foreground">
                  Permanently delete this portfolio and its stored history
                </p>
              </div>
              <AlertDialog>
                <AlertDialogTrigger asChild>
                  <Button variant="destructive" disabled={isDeleting}>
                    <Trash2 className="h-4 w-4" />
                    Delete
                  </Button>
                </AlertDialogTrigger>
                <AlertDialogContent className="bg-card border-border">
                  <AlertDialogHeader>
                    <AlertDialogTitle>Delete Portfolio?</AlertDialogTitle>
                    <AlertDialogDescription>
                      This will permanently delete &quot;{portfolio?.name}&quot;
                      and all associated transactions, holdings, snapshots, and
                      agent history. Model records for tickers not used anywhere
                      else will also be removed. This action cannot be undone.
                    </AlertDialogDescription>
                  </AlertDialogHeader>
                  <AlertDialogFooter>
                    <AlertDialogCancel>Cancel</AlertDialogCancel>
                    <AlertDialogAction
                      onClick={handleDelete}
                      className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
                    >
                      {isDeleting ? (
                        <>
                          <Loader2 className="h-4 w-4 animate-spin" />
                          Deleting...
                        </>
                      ) : (
                        "Delete Portfolio"
                      )}
                    </AlertDialogAction>
                  </AlertDialogFooter>
                </AlertDialogContent>
              </AlertDialog>
            </div>
          </CardContent>
        </Card>
      </div>
    </DashboardLayout>
  );
}
