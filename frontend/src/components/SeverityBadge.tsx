import { Badge } from "@/components/ui/badge";
import type { Severity } from "@/lib/types";
import { cn } from "@/lib/utils";

const STYLES: Record<Severity, string> = {
  info: "bg-slate-500/15 text-slate-600 dark:text-slate-300",
  low: "bg-sky-500/15 text-sky-600 dark:text-sky-400",
  medium: "bg-amber-500/15 text-amber-600 dark:text-amber-400",
  high: "bg-orange-500/15 text-orange-600 dark:text-orange-400",
  critical: "bg-red-500/15 text-red-600 dark:text-red-400",
};

export function SeverityBadge({ severity }: { severity: Severity }) {
  return (
    <Badge variant="outline" className={cn("border-transparent capitalize", STYLES[severity])}>
      {severity}
    </Badge>
  );
}
