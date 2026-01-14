import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import type { Stats } from "@/lib/types";

function usd(n: number): string {
  return `$${n.toFixed(n < 0.01 ? 6 : 4)}`;
}

export function CostPanel({ llm }: { llm: Stats["llm"] }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">LLM cost</CardTitle>
        <CardDescription>
          {llm.calls} calls · {llm.tokens.toLocaleString()} tokens · {usd(llm.cost_usd)} est.
        </CardDescription>
      </CardHeader>
      <CardContent>
        {llm.by_operation.length === 0 ? (
          <p className="text-sm text-muted-foreground">No LLM usage recorded yet.</p>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-muted-foreground">
                <th className="pb-2 font-medium">Operation</th>
                <th className="pb-2 text-right font-medium">Calls</th>
                <th className="pb-2 text-right font-medium">Tokens</th>
                <th className="pb-2 text-right font-medium">Cost</th>
              </tr>
            </thead>
            <tbody>
              {llm.by_operation.map((row) => (
                <tr key={row.operation} className="border-t">
                  <td className="py-1.5 capitalize">{row.operation}</td>
                  <td className="py-1.5 text-right">{row.calls}</td>
                  <td className="py-1.5 text-right">{row.tokens.toLocaleString()}</td>
                  <td className="py-1.5 text-right">{usd(row.cost_usd)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </CardContent>
    </Card>
  );
}
