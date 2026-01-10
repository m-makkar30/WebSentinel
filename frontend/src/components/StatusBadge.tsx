import { Badge } from "@/components/ui/badge";
import type { TargetStatus } from "@/lib/types";
import { cn } from "@/lib/utils";

const STYLES: Record<TargetStatus, string> = {
  active: "bg-emerald-500/15 text-emerald-600 dark:text-emerald-400",
  paused: "bg-muted text-muted-foreground",
  blocked: "bg-amber-500/15 text-amber-600 dark:text-amber-400",
  error: "bg-destructive/15 text-destructive",
};

export function StatusBadge({ status }: { status: TargetStatus }) {
  return (
    <Badge variant="outline" className={cn("border-transparent capitalize", STYLES[status])}>
      {status}
    </Badge>
  );
}
