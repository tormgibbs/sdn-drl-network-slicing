import { Card, CardContent } from "#/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "#/components/ui/table";
import type { baselineComparison } from "#/data/agent-data.ts";

type BaselineComparisonProps = {
  data: typeof baselineComparison;
};

export function BaselineComparison({ data }: BaselineComparisonProps) {
  return (
    <Card className="bg-muted border-none rounded-none">
      <CardContent className="pt-6">
        <p className="text-xs uppercase tracking-widest text-muted-foreground mb-4">
          Baseline Comparison
        </p>
        <Table>
          <TableHeader>
            <TableRow className="uppercase">
              <TableHead>Mode</TableHead>
              <TableHead>Avg Reward</TableHead>
              <TableHead>SLA Sat</TableHead>
              <TableHead>Violations</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {data.map((row) => {
              const isPositive = row.reward >= 0;
            //   const isAgent = row.mode === "PPO AGENT";
              return (
                <TableRow key={row.mode}>
                  <TableCell>
                    <span
                      className={"text-xs font-mono border px-2 py-0.5 border-muted-foreground text-muted-foreground" }
                    >
                      {row.mode}
                    </span>
                  </TableCell>
                  <TableCell
                    className={`font-mono font-bold ${isPositive ? "text-green-500" : "text-red-500"}`}
                  >
                    {isPositive ? "+" : ""}
                    {row.reward.toFixed(2)}
                  </TableCell>
                  <TableCell className={row.sla_pct < 70 ? "text-red-500" : ""}>
                    {row.sla_pct.toFixed(1)}%
                  </TableCell>
                  <TableCell>{row.violations}</TableCell>
                </TableRow>
              );
            })}
          </TableBody>
        </Table>
      </CardContent>
    </Card>
  );
}
