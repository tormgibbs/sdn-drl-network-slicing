// frontend/src/components/primitives/slice-table.tsx

import { Badge } from "#/components/ui/badge";
import {
	Card,
	CardContent,
	CardFooter,
	CardHeader,
	CardTitle,
} from "#/components/ui/card";
import { Progress } from "#/components/ui/progress";
import {
	Table,
	TableBody,
	TableCell,
	TableHead,
	TableHeader,
	TableRow,
} from "#/components/ui/table";
import { initialData } from "#/data/dashboard";
import type { MetricsResponse } from "#/lib/schemas";
import { computeSlaStatus } from "#/lib/sla";
import type { SliceKey } from "#/types/slice";

type SliceTableProps = {
	metrics: MetricsResponse | null;
	utilisedPct: string;
};

const SLA_BADGE: Record<string, { label: string; className: string }> = {
	VIOLATION: {
		label: "VIOLATION",
		className: "bg-[#FB2C36] text-white border-transparent",
	},
	WARNING: { label: "WARNING", className: "text-[#FF6900] border-[#FF6900]" },
	NOMINAL: {
		label: "NOMINAL",
		className: "bg-[#00C950] text-black border-transparent",
	},
};

export function SliceTable({ metrics, utilisedPct }: SliceTableProps) {
	return (
		<Card className="shadow-none border-border">
			<CardHeader>
				<CardTitle className="text-xl tracking-tight font-medium">
					Network Slice Status
				</CardTitle>
			</CardHeader>

			<CardContent>
				<Table>
					<TableHeader>
						<TableRow>
							<TableHead className="text-[11px] font-mono uppercase tracking-wider text-muted-foreground">
								PR
							</TableHead>
							<TableHead className="text-[11px] font-mono uppercase tracking-wider text-muted-foreground">
								Slice
							</TableHead>
							<TableHead className="text-[11px] font-mono uppercase tracking-wider text-muted-foreground">
								SLA
							</TableHead>
							<TableHead className="w-24 text-[11px] font-mono uppercase tracking-wider text-muted-foreground">
								Thrpt (Mbps)
							</TableHead>
							<TableHead className="w-24 text-[11px] font-mono uppercase tracking-wider text-muted-foreground">
								Latency (ms)
							</TableHead>
						</TableRow>
					</TableHeader>
					<TableBody>
						{(Object.keys(initialData.slices) as SliceKey[]).map((key) => {
							const slice = initialData.slices[key];
							const metric = metrics?.[key] ?? null;
							const sla =
								metric === null ? null : computeSlaStatus(metric, slice);
							const slaBadge = sla ? SLA_BADGE[sla] : null;

							return (
								<TableRow key={key}>
									<TableCell>
										<span className="font-mono text-sm text-muted-foreground">
											{slice.priority_label}
										</span>
									</TableCell>
									<TableCell className="font-mono text-sm">
										{slice.name}
									</TableCell>
									<TableCell>
										{slaBadge ? (
											<Badge variant="outline" className={slaBadge.className}>
												{slaBadge.label}
											</Badge>
										) : (
											<Badge variant="secondary">NO DATA</Badge>
										)}
									</TableCell>
									<TableCell className="font-mono text-sm">
										{metric
											? (metric.tx_throughput_bps / 1_000_000).toFixed(2)
											: "—"}
									</TableCell>
									<TableCell className="font-mono text-sm">
										{metric?.latency_ms !== undefined &&
										metric?.latency_ms !== null
											? metric.latency_ms.toFixed(1)
											: "—"}
									</TableCell>
								</TableRow>
							);
						})}
					</TableBody>
				</Table>
			</CardContent>

			<CardFooter className="flex items-center gap-4 border-t border-dashed">
				<span className="text-[11px] font-mono uppercase tracking-wider text-muted-foreground shrink-0">
					Total BW Allocation
				</span>
				<Progress value={Number(utilisedPct)} />
				<span className="text-xs font-mono shrink-0">
					{utilisedPct}% Utilized
				</span>
			</CardFooter>
		</Card>
	);
}
