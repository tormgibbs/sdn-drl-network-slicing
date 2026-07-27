import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "#/components/ui/table";
import { Progress } from "#/components/ui/progress";
import { initialData } from "#/data/dashboard";
import type { MetricsResponse } from "#/lib/schemas";
import type { SliceKey } from "#/types/slice";
import { computeSlaStatus } from "#/lib/sla";

type SliceTableProps = {
  // Live metrics only — null until the first WS tick arrives, in which
  // case every row renders a genuine "no data yet" state rather than any
  // mock/generated fallback.
  metrics: MetricsResponse | null;
  utilisedPct: string;
};

export function SliceTable({ metrics, utilisedPct }: SliceTableProps) {
  return (
    <div className="bg-background p-4">
      <Table>
        <TableHeader>
          <TableRow className="uppercase">
            <TableHead>pr</TableHead>
            <TableHead>slice</TableHead>
            <TableHead>sla</TableHead>
            <TableHead>thrpt(mbps)</TableHead>
            <TableHead>latency(ms)</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {(Object.keys(initialData.slices) as SliceKey[]).map((key) => {
            const slice = initialData.slices[key];
            const metric = metrics?.[key] ?? null;
            // computeSlaStatus takes non-nullable SliceMetrics and only
            // ever returns NOMINAL/WARNING/VIOLATION — it has no concept of
            // "no data". Null must be branched on here, at the call site,
            // before computeSlaStatus is invoked at all.
            const sla = metric === null ? null : computeSlaStatus(metric, slice);
            const slaLabel = sla ?? "NO DATA";
            const slaColor =
              sla === null
                ? "gray"
                : { VIOLATION: "red", WARNING: "yellow", NOMINAL: "green" }[sla];
            const priorityColor = {
              PR1: "#a855f7",
              PR2: "#ef4444",
              PR3: "#f97316",
              PR4: "#22c55e",
              PR5: "#3b82f6",
            }[slice.priority_label];

            return (
              <TableRow key={key}>
                <TableCell style={{ color: priorityColor }}>
                  {slice.priority_label}
                </TableCell>
                <TableCell>{slice.name}</TableCell>
                <TableCell style={{ color: slaColor }}>{slaLabel}</TableCell>
                <TableCell>
                  {metric
                    ? (metric.tx_throughput_bps / 1_000_000).toFixed(1)
                    : "—"}
                </TableCell>
                <TableCell>{metric?.latency_ms ?? "—"}</TableCell>
              </TableRow>
            );
          })}
        </TableBody>
      </Table>

      {/* Total BW Allocation Bar */}
      <div className="mt-4 flex items-center gap-4">
        <span className="text-xs uppercase text-muted-foreground shrink-0">
          Total BW Allocation
        </span>
        <Progress value={Number(utilisedPct)} />
        <span className="text-xs shrink-0">{utilisedPct}% Utilized</span>
      </div>
    </div>
  );
}