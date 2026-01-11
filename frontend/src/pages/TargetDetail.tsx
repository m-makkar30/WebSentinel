import { useQuery } from "@tanstack/react-query";
import { AlertCircle, ArrowLeft, ExternalLink, Inbox } from "lucide-react";
import { useState } from "react";
import { Link, useParams } from "react-router-dom";

import { DiffView } from "@/components/changes/DiffView";
import { SeverityBadge } from "@/components/SeverityBadge";
import { StatusBadge } from "@/components/StatusBadge";
import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import { api } from "@/lib/api";
import { cn } from "@/lib/utils";

function fmt(dt: string): string {
  return new Date(dt).toLocaleString();
}

export function TargetDetail() {
  const { uuid } = useParams<{ uuid: string }>();
  const [selectedId, setSelectedId] = useState<number | null>(null);

  const targetQuery = useQuery({
    queryKey: ["target", uuid],
    queryFn: () => api.getTarget(uuid!),
    enabled: Boolean(uuid),
  });
  const changesQuery = useQuery({
    queryKey: ["changes", uuid],
    queryFn: () => api.listChanges(uuid!),
    enabled: Boolean(uuid),
  });

  const target = targetQuery.data;
  const changes = changesQuery.data?.results ?? [];
  const selected = changes.find((c) => c.id === selectedId) ?? changes[0] ?? null;

  return (
    <div className="mx-auto max-w-6xl space-y-6">
      <Link
        to="/targets"
        className="inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground"
      >
        <ArrowLeft className="h-4 w-4" /> Targets
      </Link>

      {targetQuery.isError ? (
        <Card className="flex flex-col items-center gap-3 p-10 text-center">
          <AlertCircle className="h-8 w-8 text-destructive" />
          <p className="text-sm text-muted-foreground">Couldn’t load this target.</p>
        </Card>
      ) : (
        <>
          <div className="space-y-2">
            <div className="flex flex-wrap items-center gap-2">
              <h1 className="text-2xl font-semibold tracking-tight">
                {target?.name ?? "Loading…"}
              </h1>
              {target && <StatusBadge status={target.status} />}
              {target && (
                <Badge variant="secondary" className="capitalize">
                  {target.vertical}
                </Badge>
              )}
            </div>
            {target && (
              <a
                href={target.url}
                target="_blank"
                rel="noreferrer"
                className="inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground"
              >
                {target.url} <ExternalLink className="h-3 w-3" />
              </a>
            )}
            {target && (
              <p className="text-xs text-muted-foreground">
                every {target.check_interval_minutes}m ·{" "}
                {target.last_checked_at
                  ? `last checked ${fmt(target.last_checked_at)}`
                  : "never checked"}
              </p>
            )}
          </div>

          <div className="grid gap-6 lg:grid-cols-[320px_1fr]">
            <div className="space-y-2">
              <h2 className="text-sm font-medium text-muted-foreground">Change timeline</h2>
              {changesQuery.isLoading ? (
                <div className="space-y-2">
                  {[0, 1, 2].map((i) => (
                    <div key={i} className="h-16 animate-pulse rounded-lg border bg-muted/40" />
                  ))}
                </div>
              ) : changes.length === 0 ? (
                <Card className="flex flex-col items-center gap-2 p-8 text-center">
                  <Inbox className="h-6 w-6 text-muted-foreground" />
                  <p className="text-sm text-muted-foreground">No changes detected yet.</p>
                </Card>
              ) : (
                <ol className="space-y-2">
                  {changes.map((c) => {
                    const active = selected?.id === c.id;
                    return (
                      <li key={c.id}>
                        <button
                          onClick={() => setSelectedId(c.id)}
                          className={cn(
                            "w-full rounded-lg border p-3 text-left transition-colors hover:bg-muted",
                            active && "border-accent bg-muted",
                            !c.is_meaningful && "opacity-60",
                          )}
                        >
                          <div className="flex items-center justify-between gap-2">
                            <SeverityBadge severity={c.severity} />
                            <span className="text-xs text-muted-foreground">
                              {fmt(c.detected_at)}
                            </span>
                          </div>
                          <p className="mt-1.5 line-clamp-2 text-sm">{c.summary}</p>
                        </button>
                      </li>
                    );
                  })}
                </ol>
              )}
            </div>

            <div>
              {selected ? (
                <DiffView change={selected} />
              ) : (
                <Card className="flex h-40 items-center justify-center p-6 text-center text-sm text-muted-foreground">
                  Select a change to see what happened and why it matters.
                </Card>
              )}
            </div>
          </div>
        </>
      )}
    </div>
  );
}
