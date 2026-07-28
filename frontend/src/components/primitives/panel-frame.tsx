// frontend/src/components/primitives/panel-frame.tsx
import type { ReactNode } from "react";
import { cn } from "#/lib/utils";
export function PanelFrame({
	title,
	headerRight,
	children,
	motif = true,
	overflow = "auto",
}: {
	title: string;
	headerRight?: ReactNode;
	children: ReactNode;
	motif?: boolean;
	overflow?: "auto" | "hidden";
}) {
	return (
		<div
			className={cn(
				"bg-background border border-border h-full flex flex-col",
				motif && "bg-grid-small",
			)}
		>
			<div className="px-3 h-9 flex items-center justify-between border-b border-border bg-card shrink-0">
				<span className="text-[11px] font-mono uppercase tracking-wider text-muted-foreground">
					{title}
				</span>
				{headerRight}
			</div>
			<div
				className={cn(
					"p-2 flex-1 min-h-0",
					overflow === "auto" ? "overflow-auto" : "overflow-hidden",
				)}
			>
				{children}
			</div>
		</div>
	);
}
