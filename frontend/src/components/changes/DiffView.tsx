import { SeverityBadge } from "@/components/SeverityBadge";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { Change } from "@/lib/types";
import { cn } from "@/lib/utils";

function diffLineClass(line: string): string {
  if (line.startsWith("+++") || line.startsWith("---") || line.startsWith("@@")) {
    return "text-muted-foreground";
  }
  if (line.startsWith("+")) return "bg-emerald-500/10 text-emerald-700 dark:text-emerald-300";
  if (line.startsWith("-")) return "bg-red-500/10 text-red-700 dark:text-red-300";
  return "text-muted-foreground";
}

export function DiffView({ change }: { change: Change }) {
  const lines = (change.text_diff || "").split("\n");

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Why it matters</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3 text-sm">
          <p>{change.why_it_matters || change.summary}</p>
          <div className="flex flex-wrap items-center gap-2">
            <SeverityBadge severity={change.severity} />
            <Badge variant="secondary" className="capitalize">
              {change.change_type}
            </Badge>
            <Badge variant="outline" className="capitalize">
              {change.detection_method}
            </Badge>
            {!change.is_meaningful && (
              <Badge variant="outline" className="text-muted-foreground">
                noise · suppressed
              </Badge>
            )}
          </div>
        </CardContent>
      </Card>

      {change.field_diffs.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Field changes</CardTitle>
          </CardHeader>
          <CardContent>
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-muted-foreground">
                  <th className="pb-2 font-medium">Field</th>
                  <th className="pb-2 font-medium">Before</th>
                  <th className="pb-2 font-medium">After</th>
                </tr>
              </thead>
              <tbody>
                {change.field_diffs.map((f, i) => (
                  <tr key={i} className="border-t">
                    <td className="py-1.5 font-medium">{f.field}</td>
                    <td className="py-1.5 text-red-600 dark:text-red-400">{String(f.old)}</td>
                    <td className="py-1.5 text-emerald-600 dark:text-emerald-400">
                      {String(f.new)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </CardContent>
        </Card>
      )}

      {change.text_diff && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Text diff</CardTitle>
          </CardHeader>
          <CardContent>
            <pre className="max-h-96 overflow-auto rounded-md bg-muted/40 p-3 text-xs leading-relaxed">
              {lines.map((line, i) => (
                <div key={i} className={cn("whitespace-pre-wrap", diffLineClass(line))}>
                  {line || " "}
                </div>
              ))}
            </pre>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
