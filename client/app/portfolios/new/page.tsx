"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
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
import { Badge } from "@/components/ui/badge";
import { TickerSearch } from "@/components/market/ticker-search";
import { createPortfolio } from "@/lib/api";
import { formatCurrency } from "@/lib/format";
import { toast } from "sonner";
import { X, Loader2, Check, ChevronRight, ChevronLeft } from "lucide-react";
import type { TickerSearchResult } from "@/lib/types";

type Step = 1 | 2 | 3;

export default function NewPortfolioPage() {
  const router = useRouter();
  const [step, setStep] = useState<Step>(1);
  const [isCreating, setIsCreating] = useState(false);

  // Form state
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [startingCapital, setStartingCapital] = useState(10000);
  const [tickers, setTickers] = useState<TickerSearchResult[]>([]);

  const canProceed = () => {
    if (step === 1) return name.trim().length > 0 && startingCapital >= 100;
    if (step === 2) return tickers.length >= 1 && tickers.length <= 20;
    return true;
  };

  const handleAddTicker = (ticker: TickerSearchResult) => {
    if (tickers.length >= 20) {
      toast.error("Maximum 20 tickers allowed");
      return;
    }
    setTickers([...tickers, ticker]);
  };

  const handleRemoveTicker = (tickerSymbol: string) => {
    setTickers(tickers.filter((t) => t.ticker !== tickerSymbol));
  };

  const handleCreate = async () => {
    setIsCreating(true);
    try {
      const portfolio = await createPortfolio({
        name: name.trim(),
        description: description.trim() || undefined,
        starting_capital: startingCapital,
        tickers: tickers.map((t) => t.ticker),
      });

      toast.success("Portfolio created!", {
        description: "Models are being trained for your tickers.",
      });

      router.push(`/dashboard/${portfolio.id}`);
    } catch (error) {
      toast.error("Failed to create portfolio", {
        description:
          error instanceof Error ? error.message : "Please try again.",
      });
      setIsCreating(false);
    }
  };

  return (
    <DashboardLayout title="Create Portfolio">
      <div className="mx-auto max-w-2xl">
        {/* Progress Steps */}
        <div className="mb-8 flex items-center justify-center gap-2">
          {[1, 2, 3].map((s) => (
            <div key={s} className="flex items-center">
              <div
                className={`flex h-8 w-8 items-center justify-center rounded-full border-2 text-sm font-medium ${
                  step >= s
                    ? "border-primary bg-primary text-primary-foreground"
                    : "border-border text-muted-foreground"
                }`}
              >
                {step > s ? <Check className="h-4 w-4" /> : s}
              </div>
              {s < 3 && (
                <div
                  className={`mx-2 h-0.5 w-12 ${
                    step > s ? "bg-primary" : "bg-border"
                  }`}
                />
              )}
            </div>
          ))}
        </div>

        {/* Step 1: Portfolio Details */}
        {step === 1 && (
          <Card className="bg-card/50 border-border/50">
            <CardHeader>
              <CardTitle>Portfolio Details</CardTitle>
              <CardDescription>
                Set up your portfolio name and starting capital
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <Field>
                <FieldLabel htmlFor="name">Portfolio Name</FieldLabel>
                <Input
                  id="name"
                  placeholder="My Tech Portfolio"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  className="bg-background/50"
                />
              </Field>

              <Field>
                <FieldLabel htmlFor="description">
                  Description (Optional)
                </FieldLabel>
                <Textarea
                  id="description"
                  placeholder="Focus on high-growth tech stocks..."
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  className="bg-background/50 resize-none"
                  rows={3}
                />
              </Field>

              <Field>
                <FieldLabel htmlFor="capital">Starting Capital</FieldLabel>
                <Input
                  id="capital"
                  type="number"
                  min={100}
                  step={100}
                  value={startingCapital}
                  onChange={(e) => setStartingCapital(Number(e.target.value))}
                  className="bg-background/50 font-mono"
                />
                <p className="mt-1 text-sm text-muted-foreground">
                  Your portfolio starts with{" "}
                  <span className="font-mono font-medium text-foreground">
                    {formatCurrency(startingCapital)}
                  </span>
                </p>
              </Field>
            </CardContent>
          </Card>
        )}

        {/* Step 2: Add Tickers */}
        {step === 2 && (
          <Card className="bg-card/50 border-border/50">
            <CardHeader>
              <CardTitle>Add Tickers</CardTitle>
              <CardDescription>
                Select stocks for the agent to analyze and trade (1-20 tickers)
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <TickerSearch
                onSelect={handleAddTicker}
                selectedTickers={tickers.map((t) => t.ticker)}
                placeholder="Search for stocks..."
              />

              {tickers.length > 0 && (
                <div className="flex flex-wrap gap-2">
                  {tickers.map((ticker) => (
                    <Badge
                      key={ticker.ticker}
                      variant="outline"
                      className="px-3 py-1.5 text-sm bg-secondary/30"
                    >
                      <span className="font-mono font-semibold mr-1">
                        {ticker.ticker}
                      </span>
                      <span className="text-muted-foreground text-xs mr-2">
                        {ticker.name.slice(0, 20)}
                        {ticker.name.length > 20 ? "..." : ""}
                      </span>
                      <button
                        onClick={() => handleRemoveTicker(ticker.ticker)}
                        className="text-muted-foreground hover:text-foreground"
                      >
                        <X className="h-3 w-3" />
                      </button>
                    </Badge>
                  ))}
                </div>
              )}

              <p className="text-sm text-muted-foreground">
                {tickers.length}/20 tickers selected. Models will be trained for
                each ticker after creation (~60 sec).
              </p>
            </CardContent>
          </Card>
        )}

        {/* Step 3: Review & Create */}
        {step === 3 && (
          <Card className="bg-card/50 border-border/50">
            <CardHeader>
              <CardTitle>Review & Create</CardTitle>
              <CardDescription>
                Confirm your portfolio settings
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="rounded-lg bg-secondary/30 border border-border/50 p-4 space-y-3">
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Name</span>
                  <span className="font-medium">{name}</span>
                </div>
                {description && (
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Description</span>
                    <span className="text-sm text-right max-w-[200px] truncate">
                      {description}
                    </span>
                  </div>
                )}
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Starting Capital</span>
                  <span className="font-mono font-medium">
                    {formatCurrency(startingCapital)}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Tickers</span>
                  <span className="font-mono">
                    {tickers.map((t) => t.ticker).join(", ")}
                  </span>
                </div>
              </div>

              {isCreating && (
                <div className="flex items-center gap-2 text-sm text-primary">
                  <Loader2 className="h-4 w-4 animate-spin" />
                  Creating portfolio... Training models for{" "}
                  {tickers.map((t) => t.ticker).join(", ")}...
                </div>
              )}
            </CardContent>
          </Card>
        )}

        {/* Navigation */}
        <div className="mt-6 flex justify-between">
          <Button
            variant="outline"
            onClick={() => setStep((s) => (s - 1) as Step)}
            disabled={step === 1 || isCreating}
          >
            <ChevronLeft className="h-4 w-4" />
            Back
          </Button>

          {step < 3 ? (
            <Button
              onClick={() => setStep((s) => (s + 1) as Step)}
              disabled={!canProceed()}
            >
              Next
              <ChevronRight className="h-4 w-4" />
            </Button>
          ) : (
            <Button onClick={handleCreate} disabled={isCreating}>
              {isCreating ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" />
                  Creating...
                </>
              ) : (
                "Create Portfolio"
              )}
            </Button>
          )}
        </div>
      </div>
    </DashboardLayout>
  );
}
