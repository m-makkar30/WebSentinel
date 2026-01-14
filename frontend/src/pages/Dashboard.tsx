import { useQuery } from "@tanstack/react-query";
import { AlertCircle } from "lucide-react";

import { AlertsFeed } from "@/components/dashboard/AlertsFeed";
import { CostPanel } from "@/components/dashboard/CostPanel";
import { TrendChart } from "@/components/dashboard/TrendChart";
import { StatCard } from "@/components/StatCard";
import { Card } from "@/components/ui/card";
import { api } from "@/lib/api";

function usd(n: number): string {
  return `$${n.toFixed(n < 0.01 ? 6 : 4)}`;
}

export function Dashboard() {
  const stats = useQuery({ queryKey: ["stats"], queryFn: api.getStats });

  return (
    <div className="mx-auto max-w-6xl space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Dashboard</h1>
        <p className="text-sm text-muted-foreground">
          Overview of monitored targets, detected changes, and cost.
        </p>
      </div>

      {stats.isError ? (
        <Card className="flex flex-col items-center gap-3 p-10 text-center">
          <AlertCircle className="h-8 w-8 text-destructive" />
          <p className="text-sm text-muted-foreground">Couldn’t load dashboard stats.</p>
        </Card>
      ) : (
        <>
          <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
            <StatCard
              label="Targets"
              value={stats.data ? `${stats.data.targets.active}/${stats.data.targets.total}` : "—"}
              hint="active / total"
            />
            <StatCard
              label="Meaningful changes"
              value={stats.data?.changes.meaningful ?? "—"}
              hint={stats.data ? `${stats.data.changes.noise} noise suppressed` : undefined}
            />
            <StatCard label="Open alerts" value={stats.data?.alerts.open ?? "—"} />
            <StatCard
              label="LLM cost (est.)"
              value={stats.data ? usd(stats.data.llm.cost_usd) : "—"}
              hint={stats.data ? `${stats.data.llm.tokens.toLocaleString()} tokens` : undefined}
            />
          </div>

          <div className="grid gap-6 lg:grid-cols-2">
            <TrendChart trend={stats.data?.changes.trend ?? []} />
            <CostPanel
              llm={stats.data?.llm ?? { calls: 0, tokens: 0, cost_usd: 0, by_operation: [] }}
            />
          </div>

          <AlertsFeed />
        </>
      )}
    </div>
  );
}
