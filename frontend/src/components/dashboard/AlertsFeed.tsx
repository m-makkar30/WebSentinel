import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { BellOff, Check } from "lucide-react";
import { Link } from "react-router-dom";

import { SeverityBadge } from "@/components/SeverityBadge";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { api } from "@/lib/api";

function fmt(dt: string): string {
  return new Date(dt).toLocaleString();
}

export function AlertsFeed() {
  const queryClient = useQueryClient();
  const query = useQuery({
    queryKey: ["alerts", "open"],
    queryFn: () => api.listAlerts({ status: "new" }),
  });

  const ack = useMutation({
    mutationFn: (id: number) => api.acknowledgeAlert(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["alerts"] });
      queryClient.invalidateQueries({ queryKey: ["stats"] });
    },
  });

  const alerts = query.data?.results ?? [];

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Open alerts</CardTitle>
        <CardDescription>Meaningful changes and targets needing attention.</CardDescription>
      </CardHeader>
      <CardContent>
        {query.isLoading ? (
          <div className="space-y-2">
            {[0, 1, 2].map((i) => (
              <div key={i} className="h-14 animate-pulse rounded-lg bg-muted/40" />
            ))}
          </div>
        ) : alerts.length === 0 ? (
          <div className="flex flex-col items-center gap-2 py-8 text-center">
            <BellOff className="h-6 w-6 text-muted-foreground" />
            <p className="text-sm text-muted-foreground">No open alerts. All quiet.</p>
          </div>
        ) : (
          <ul className="divide-y">
            {alerts.map((a) => (
              <li key={a.id} className="flex items-start justify-between gap-3 py-3">
                <div className="min-w-0 space-y-1">
                  <div className="flex flex-wrap items-center gap-2">
                    <SeverityBadge severity={a.level} />
                    <Badge variant="outline" className="capitalize">
                      {a.kind}
                    </Badge>
                    <Link
                      to={`/targets/${a.target}`}
                      className="text-xs text-muted-foreground hover:underline"
                    >
                      {a.target_name}
                    </Link>
                  </div>
                  <p className="text-sm font-medium">{a.title}</p>
                  {a.body && <p className="line-clamp-2 text-xs text-muted-foreground">{a.body}</p>}
                  <p className="text-xs text-muted-foreground">{fmt(a.created_at)}</p>
                </div>
                <Button
                  variant="ghost"
                  size="sm"
                  title="Acknowledge"
                  onClick={() => ack.mutate(a.id)}
                  disabled={ack.isPending}
                >
                  <Check className="h-4 w-4" /> Ack
                </Button>
              </li>
            ))}
          </ul>
        )}
      </CardContent>
    </Card>
  );
}
