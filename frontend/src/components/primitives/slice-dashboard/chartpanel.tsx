import { ResponsiveContainer } from "recharts";
import type { ReactNode } from "react";

export function ChartPanel({
  title,
  height = 170,
  children,
}: {
  title: string;
  height?: number;
  children: ReactNode;
}) {
  return (
    <div className="bg-zinc-950">
      <div className="px-3 h-7 flex items-center border-b border-white/10 bg-white/[0.03]">
        <span className="font-mono text-[10px] text-white/40 uppercase tracking-widest">
          {title}
        </span>
      </div>
      <div style={{ padding: "8px 4px 4px" }}>
        <ResponsiveContainer width="100%" height={height}>
          {children}
        </ResponsiveContainer>
      </div>
    </div>
  );
}