"use client";

import { useParams } from "next/navigation";
import { DashboardLayout } from "@/components/layout/dashboard-layout";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { TradeFilters } from "@/components/trades/trade-filters";
import { TransactionTable } from "@/components/trades/transaction-table";
import { useTransactions } from "@/hooks/use-transactions";
import { usePortfolio } from "@/hooks/use-portfolio";
import { ChevronLeft, ChevronRight } from "lucide-react";

export default function TradesPage() {
  const params = useParams();
  const portfolioId = params.portfolioId as string;

  const { portfolio } = usePortfolio(portfolioId);
  const {
    transactions,
    total,
    isLoading,
    filters,
    updateFilters,
    nextPage,
    prevPage,
    currentPage,
    totalPages,
  } = useTransactions(portfolioId);

  return (
    <DashboardLayout portfolioId={portfolioId}>
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-bold text-foreground">
            Transaction History
          </h1>
          <p className="text-muted-foreground">
            Full log of all agent trades and decisions
          </p>
        </div>

        <Card className="bg-card/50 border-border/50">
          <CardHeader className="border-b border-border/50">
            <CardTitle className="text-base font-medium">Filters</CardTitle>
          </CardHeader>
          <CardContent className="pt-4">
            <TradeFilters
              tickers={portfolio?.tickers ?? []}
              filters={filters}
              onFiltersChange={updateFilters}
            />
          </CardContent>
        </Card>

        <Card className="bg-card/50 border-border/50">
          <CardHeader className="flex flex-row items-center justify-between border-b border-border/50">
            <CardTitle className="text-base font-medium">
              Transactions
              {total > 0 && (
                <span className="ml-2 text-sm font-normal text-muted-foreground">
                  ({total} total)
                </span>
              )}
            </CardTitle>
          </CardHeader>
          <CardContent className="pt-4">
            <TransactionTable
              transactions={transactions}
              isLoading={isLoading}
            />

            {/* Pagination */}
            {totalPages > 1 && (
              <div className="mt-4 flex items-center justify-between border-t border-border/50 pt-4">
                <p className="text-sm text-muted-foreground">
                  Page {currentPage + 1} of {totalPages}
                </p>
                <div className="flex items-center gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={prevPage}
                    disabled={currentPage === 0}
                  >
                    <ChevronLeft className="h-4 w-4" />
                    Previous
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={nextPage}
                    disabled={currentPage >= totalPages - 1}
                  >
                    Next
                    <ChevronRight className="h-4 w-4" />
                  </Button>
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </DashboardLayout>
  );
}
