import { Skeleton } from "@/components/ui/skeleton";

export default function PortfolioSettingsLoading() {
  return (
    <div className="mx-auto max-w-2xl space-y-6 p-6">
      <Skeleton className="h-10 w-72" />
      <Skeleton className="h-64 w-full" />
      <Skeleton className="h-56 w-full" />
      <Skeleton className="h-44 w-full" />
    </div>
  );
}
