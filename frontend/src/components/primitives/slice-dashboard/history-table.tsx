import { Download } from "lucide-react";
import type { HistoryRow } from "../../../types/slice1";

export interface HistoryTableProps {
  rows:          HistoryRow[];
  title:         string;
  thrptHeader?:  string;
  renderThrpt?:  (row: HistoryRow) => React.ReactNode;
  renderAlloc?:  (row: HistoryRow) => React.ReactNode;
}

export function HistoryTable({ rows, title, thrptHeader = "THRPT (MBPS)", renderThrpt, renderAlloc }: HistoryTableProps) {
  return (
    <div className="border-t border-white/10">
      <div className="flex items-center justify-between px-4 h-8 bg-zinc-950 border-b border-white/10 sticky top-0 z-10">
        <span className="font-mono text-[10px] text-white/40 uppercase tracking-widest">{title}</span>
        <button className="text-white/30 hover:text-white/60 transition-colors cursor-pointer bg-transparent border-none p-0">
          <Download size={12} />
        </button>
      </div>
      <div className="max-h-72 overflow-y-auto overflow-x-auto">
        <table className="w-full text-[10px] font-mono min-w-[600px]">
          <thead className="sticky top-0 bg-zinc-950 z-10">
            <tr className="border-b border-white/10">
              <th className="px-3 py-2 text-left text-white/30 font-normal">TIMESTAMP</th>
              <th className="px-3 py-2 text-left text-white/30 font-normal">CYCLE ID</th>
              <th className="px-3 py-2 text-right text-white/30 font-normal">{thrptHeader}</th>
              <th className="px-3 py-2 text-right text-white/30 font-normal">LAT (MS)</th>
              <th className="px-3 py-2 text-right text-white/30 font-normal">LOSS (%)</th>
              <th className="px-3 py-2 text-right text-white/30 font-normal">ALLOC</th>
              <th className="px-3 py-2 text-right text-white/30 font-normal">SLA STATUS</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row, idx) => {
              const isViolation = row.sla === "VIOLATION";
              return (
                <tr
                  key={row.id + idx}
                  className={["border-b border-white/5", idx % 2 === 0 ? "bg-transparent" : "bg-white/[0.02]"].join(" ")}
                >
                  <td className="px-3 py-1.5 text-white/40">{row.ts}</td>
                  <td className="px-3 py-1.5 text-white/60">{row.id}</td>
                  <td className={["px-3 py-1.5 text-right", isViolation ? "text-red-400" : "text-white/60"].join(" ")}>
                    {renderThrpt ? renderThrpt(row) : row.thrpt}
                  </td>
                  <td className={["px-3 py-1.5 text-right", isViolation ? "text-red-400" : "text-white/60"].join(" ")}>{row.lat}</td>
                  <td className="px-3 py-1.5 text-right text-white/50">{row.loss}</td>
                  <td className="px-3 py-1.5 text-right text-white/50">{renderAlloc ? renderAlloc(row) : row.alloc}</td>
                  <td className="px-3 py-1.5 text-right">
                    <span className={[
                      "font-mono text-[9px] px-1.5 py-0.5 rounded border uppercase tracking-widest",
                      row.sla === "MET"
                        ? "text-emerald-400 border-emerald-500/30 bg-emerald-500/10"
                        : "text-red-400 border-red-500/30 bg-red-500/10",
                    ].join(" ")}>
                      {row.sla}
                    </span>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}