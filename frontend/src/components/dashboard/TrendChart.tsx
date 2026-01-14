import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import type { Stats } from "@/lib/types";

export function TrendChart({ trend }: { trend: Stats["changes"]["trend"] }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Change trend (7 days)</CardTitle>
        <CardDescription>Meaningful changes vs. suppressed noise per day.</CardDescription>
      </CardHeader>
      <CardContent>
        {trend.length === 0 ? (
          <div className="flex h-[220px] items-center justify-center text-sm text-muted-foreground">
            No changes detected yet.
          </div>
        ) : (
          <ResponsiveContainer width="100%" height={220}>
            <BarChart data={trend} margin={{ top: 4, right: 8, left: -16, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="hsl(240 5% 88%)" vertical={false} />
              <XAxis dataKey="date" tick={{ fontSize: 11 }} tickLine={false} axisLine={false} />
              <YAxis
                allowDecimals={false}
                tick={{ fontSize: 11 }}
                tickLine={false}
                axisLine={false}
              />
              <Tooltip
                contentStyle={{
                  fontSize: 12,
                  borderRadius: 8,
                  border: "1px solid hsl(240 6% 90%)",
                }}
              />
              <Legend wrapperStyle={{ fontSize: 12 }} />
              <Bar dataKey="meaningful" stackId="a" fill="hsl(221 83% 53%)" radius={[0, 0, 0, 0]} />
              <Bar dataKey="noise" stackId="a" fill="hsl(240 5% 75%)" radius={[3, 3, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        )}
      </CardContent>
    </Card>
  );
}
