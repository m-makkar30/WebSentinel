import { useQuery } from "@tanstack/react-query";

import { api } from "@/lib/api";
import type { RunStatus } from "@/lib/types";
import { cn } from "@/lib/utils";

const DOT: Record<RunStatus, string> = {
  ok: "bg-emerald-500",
  skipped: "bg-slate-400",
  blocked: "bg-amber-500",
  error: "bg-red-500",
};

export function RunHistory({ targetUuid }: { targetUuid: string }) {
  const query = useQuery({
    queryKey: ["runs", targetUuid],
    queryFn: () => api.listRuns(targetUuid),
  });
  const runs = (query.data?.results ?? []).slice(0, 16);
  if (runs.length === 0) return null;

  return (
    <div className="flex items-center gap-1.5">
      <span className="mr-1 text-xs text-muted-foreground">Recent runs</span>
      {runs.map((r) => (
        <span
          key={r.id}
          className={cn("h-2.5 w-2.5 rounded-full", DOT[r.status])}
          title={
            `${r.status} · ${r.fetch_method || "—"} · HTTP ${r.http_status ?? "—"} · ` +
            `${new Date(r.started_at).toLocaleString()}` +
            (r.error ? ` · ${r.error}` : "")
          }
        />
      ))}
    </div>
  );
}
