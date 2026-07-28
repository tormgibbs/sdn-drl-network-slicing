// frontend/src/components/primitives/slice-dashboard/recent-cycles-panel.tsx
import { cn } from "#/lib/utils";
import type { RecentCycle } from "../../../types/slice1";

const VISIBLE_ROWS = 7;
const ROW_CLASS = "h-8"; // fixed row height, applied identically to every <tr>

function formatNum(value: number): string {
	return value.toFixed(3);
}

export function RecentCyclesPanel({
	cycles,
	cols = ["THRPT", "LAT"],
}: {
	cycles: RecentCycle[];
	cols?: [string, string];
}) {
	return (
		<table className="w-full text-[10px] font-mono">
			<thead>
				<tr className={cn(ROW_CLASS, "border-b border-border")}>
					<th className="w-6 px-3 text-left text-muted-foreground font-normal">
						ST
					</th>
					<th className="px-3 text-left text-muted-foreground font-normal">
						CYCLE ID
					</th>
					<th className="px-3 text-right text-muted-foreground font-normal">
						{cols[0]}
					</th>
					<th className="px-3 text-right text-muted-foreground font-normal">
						{cols[1]}
					</th>
				</tr>
			</thead>
			<tbody>
				{Array.from({ length: VISIBLE_ROWS }).map((_, i) => {
					const c = cycles[i];
					if (!c) {
						return (
							<tr
								key={`empty-${i}`}
								className={cn(
									ROW_CLASS,
									i < VISIBLE_ROWS - 1 && "border-b border-border/50",
								)}
							>
								<td className="px-3">&nbsp;</td>
								<td className="px-3 text-muted-foreground">—</td>
								<td className="px-3 text-right text-muted-foreground">—</td>
								<td className="px-3 text-right text-muted-foreground">—</td>
							</tr>
						);
					}
					const isViolation = c.status === "VIOLATION";
					return (
						<tr
							key={c.id}
							className={cn(
								ROW_CLASS,
								i < VISIBLE_ROWS - 1 && "border-b border-border/50",
								"hover:bg-accent",
							)}
						>
							<td className="px-3">
								<span
									className={cn(
										"inline-block w-1.5 h-1.5 rounded-full",
										isViolation
											? "bg-[#FB2C36]"
											: "bg-transparent border border-border",
									)}
								/>
							</td>
							<td
								className={cn(
									"px-3",
									isViolation ? "text-[#FB2C36]" : "text-muted-foreground",
								)}
							>
								{c.id}
							</td>
							<td
								className={cn(
									"px-3 text-right",
									isViolation ? "text-[#FB2C36]" : "text-muted-foreground",
								)}
							>
								{formatNum(c.thrpt)}
							</td>
							<td
								className={cn(
									"px-3 text-right",
									isViolation ? "text-[#FB2C36]" : "text-muted-foreground",
								)}
							>
								{formatNum(c.lat)}
							</td>
						</tr>
					);
				})}
			</tbody>
		</table>
	);
}
