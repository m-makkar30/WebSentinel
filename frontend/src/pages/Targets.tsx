import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { AlertCircle, Globe, Pause, Pencil, Play, Plus, Trash2 } from "lucide-react";
import { useState } from "react";
import { Link } from "react-router-dom";

import { StatusBadge } from "@/components/StatusBadge";
import { DeleteTargetDialog } from "@/components/targets/DeleteTargetDialog";
import { TargetFormDialog } from "@/components/targets/TargetFormDialog";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { api } from "@/lib/api";
import type { WatchTarget } from "@/lib/types";

export function Targets() {
  const queryClient = useQueryClient();
  const [search, setSearch] = useState("");
  const [vertical, setVertical] = useState("");
  const [status, setStatus] = useState("");

  const [formOpen, setFormOpen] = useState(false);
  const [editing, setEditing] = useState<WatchTarget | null>(null);
  const [deleting, setDeleting] = useState<WatchTarget | null>(null);

  const query = useQuery({
    queryKey: ["targets", { search, vertical, status }],
    queryFn: () => api.listTargets({ search, vertical, status }),
  });

  const statusMutation = useMutation({
    mutationFn: ({ uuid, action }: { uuid: string; action: "pause" | "resume" }) =>
      action === "pause" ? api.pauseTarget(uuid) : api.resumeTarget(uuid),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["targets"] }),
  });

  function openAdd() {
    setEditing(null);
    setFormOpen(true);
  }
  function openEdit(target: WatchTarget) {
    setEditing(target);
    setFormOpen(true);
  }

  const targets = query.data?.results ?? [];

  return (
    <div className="mx-auto max-w-5xl space-y-6">
      <div className="flex items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Watch targets</h1>
          <p className="text-sm text-muted-foreground">
            Pages WebSentinel monitors and what to watch on each.
          </p>
        </div>
        <Button onClick={openAdd}>
          <Plus className="h-4 w-4" /> Add target
        </Button>
      </div>

      <div className="flex flex-wrap gap-2">
        <Input
          className="max-w-xs"
          placeholder="Search name or URL…"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
        <Select className="w-40" value={vertical} onChange={(e) => setVertical(e.target.value)}>
          <option value="">All verticals</option>
          {["pricing", "compliance", "regulatory", "status", "docs", "generic"].map((v) => (
            <option key={v} value={v}>
              {v}
            </option>
          ))}
        </Select>
        <Select className="w-36" value={status} onChange={(e) => setStatus(e.target.value)}>
          <option value="">All statuses</option>
          {["active", "paused", "blocked", "error"].map((s) => (
            <option key={s} value={s}>
              {s}
            </option>
          ))}
        </Select>
      </div>

      {query.isLoading ? (
        <div className="space-y-2">
          {[0, 1, 2].map((i) => (
            <div key={i} className="h-20 animate-pulse rounded-xl border bg-muted/40" />
          ))}
        </div>
      ) : query.isError ? (
        <Card className="flex flex-col items-center gap-3 p-10 text-center">
          <AlertCircle className="h-8 w-8 text-destructive" />
          <p className="text-sm text-muted-foreground">Couldn’t load targets.</p>
          <Button variant="outline" onClick={() => query.refetch()}>
            Retry
          </Button>
        </Card>
      ) : targets.length === 0 ? (
        <Card className="flex flex-col items-center gap-3 p-12 text-center">
          <Globe className="h-8 w-8 text-muted-foreground" />
          <div>
            <p className="font-medium">No targets yet</p>
            <p className="text-sm text-muted-foreground">
              Add a page to start watching for meaningful changes.
            </p>
          </div>
          <Button onClick={openAdd}>
            <Plus className="h-4 w-4" /> Add your first target
          </Button>
        </Card>
      ) : (
        <div className="space-y-2">
          {targets.map((t) => (
            <Card key={t.uuid} className="flex items-center justify-between gap-4 p-4">
              <div className="min-w-0 space-y-1">
                <div className="flex items-center gap-2">
                  <Link to={`/targets/${t.uuid}`} className="font-medium hover:underline">
                    {t.name}
                  </Link>
                  <StatusBadge status={t.status} />
                  <Badge variant="secondary" className="capitalize">
                    {t.vertical}
                  </Badge>
                </div>
                <p className="truncate text-sm text-muted-foreground">{t.url}</p>
                <p className="text-xs text-muted-foreground">
                  every {t.check_interval_minutes}m · {t.snapshots_count} snapshots ·{" "}
                  {t.changes_count} changes · {t.open_alerts_count} open alerts
                </p>
              </div>
              <div className="flex shrink-0 items-center gap-1">
                {t.status === "paused" ? (
                  <Button
                    variant="ghost"
                    size="icon"
                    title="Resume"
                    onClick={() => statusMutation.mutate({ uuid: t.uuid, action: "resume" })}
                  >
                    <Play className="h-4 w-4" />
                  </Button>
                ) : (
                  <Button
                    variant="ghost"
                    size="icon"
                    title="Pause"
                    onClick={() => statusMutation.mutate({ uuid: t.uuid, action: "pause" })}
                  >
                    <Pause className="h-4 w-4" />
                  </Button>
                )}
                <Button variant="ghost" size="icon" title="Edit" onClick={() => openEdit(t)}>
                  <Pencil className="h-4 w-4" />
                </Button>
                <Button variant="ghost" size="icon" title="Delete" onClick={() => setDeleting(t)}>
                  <Trash2 className="h-4 w-4" />
                </Button>
              </div>
            </Card>
          ))}
        </div>
      )}

      <TargetFormDialog open={formOpen} onOpenChange={setFormOpen} target={editing} />
      {deleting && (
        <DeleteTargetDialog
          target={deleting}
          open={Boolean(deleting)}
          onOpenChange={(o) => !o && setDeleting(null)}
        />
      )}
    </div>
  );
}
