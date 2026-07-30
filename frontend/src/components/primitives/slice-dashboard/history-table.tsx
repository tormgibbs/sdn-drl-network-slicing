// frontend/src/components/primitives/slice-dashboard/history-table.tsx

import { ScrollArea } from "#/components/ui/scroll-area";
import {
	Table,
	TableBody,
	TableCell,
	TableHead,
	TableHeader,
	TableRow,
} from "#/components/ui/table";
import type { HistoryRow } from "../../../types/slice1";
import { StatusBadge } from "../status-badge";

export interface HistoryTableProps {
	rows: HistoryRow[];
	title: string;
	thrptHeader?: string;
	renderThrpt?: (row: HistoryRow) => React.ReactNode;
	renderAlloc?: (row: HistoryRow) => React.ReactNode;
}

function formatTimestamp(ts: string): string {
	return new Date(ts).toLocaleTimeString(undefined, {
		hour: "2-digit",
		minute: "2-digit",
		second: "2-digit",
	});
}

function formatNum(value: number | string): string {
	return typeof value === "number" ? value.toFixed(3) : value;
}

const HEADER_CLASS =
	"text-[11px] font-mono uppercase tracking-wider text-muted-foreground";
const CELL_CLASS = "font-mono text-[11px]";

export function HistoryTable({
	rows,
	title,
	thrptHeader = "THRPT (MBPS)",
	renderThrpt,
	renderAlloc,
}: HistoryTableProps) {
	return (
		<div className="bg-background">
			<div className="flex items-center px-4 h-9 bg-card border-b border-border">
				<span className={HEADER_CLASS}>{title}</span>
			</div>
			<ScrollArea className="h-72 w-full">
				<Table className="min-w-150">
					<TableHeader className="sticky top-0 bg-card z-10">
						<TableRow>
							<TableHead className={HEADER_CLASS}>TIMESTAMP</TableHead>
							<TableHead className={HEADER_CLASS}>CYCLE ID</TableHead>
							<TableHead className={`text-right ${HEADER_CLASS}`}>
								{thrptHeader}
							</TableHead>
							<TableHead className={`text-right ${HEADER_CLASS}`}>
								LAT (MS)
							</TableHead>
							<TableHead className={`text-right ${HEADER_CLASS}`}>
								LOSS (%)
							</TableHead>
							<TableHead className={`text-right ${HEADER_CLASS}`}>
								ALLOC
							</TableHead>
							<TableHead className={`text-right ${HEADER_CLASS}`}>
								SLA STATUS
							</TableHead>
						</TableRow>
					</TableHeader>
					<TableBody>
						{[...rows].reverse().map((row, idx) => {
							const isViolation = row.sla === "VIOLATION";
							return (
								<TableRow key={row.id + idx}>
									<TableCell className={`${CELL_CLASS} text-muted-foreground`}>
										{formatTimestamp(row.ts)}
									</TableCell>
									<TableCell className={CELL_CLASS}>{row.id}</TableCell>
									<TableCell
										className={`text-right ${CELL_CLASS} ${isViolation ? "text-[#FB2C36]" : ""}`}
									>
										{renderThrpt ? renderThrpt(row) : formatNum(row.thrpt)}
									</TableCell>
									<TableCell
										className={`text-right ${CELL_CLASS} ${isViolation ? "text-[#FB2C36]" : ""}`}
									>
										{formatNum(row.lat)}
									</TableCell>
									<TableCell
										className={`text-right ${CELL_CLASS} text-muted-foreground`}
									>
										{formatNum(row.loss)}
									</TableCell>
									<TableCell
										className={`text-right ${CELL_CLASS} text-muted-foreground`}
									>
										{renderAlloc ? renderAlloc(row) : formatNum(row.alloc)}
									</TableCell>
									<TableCell className="text-right">
										<StatusBadge
											label={row.sla}
											className={
												row.sla === "MET"
													? "bg-[#00C950] text-black border-transparent"
													: "bg-[#FB2C36] text-white border-transparent"
											}
										/>
									</TableCell>
								</TableRow>
							);
						})}
					</TableBody>
				</Table>
			</ScrollArea>
		</div>
	);
}
