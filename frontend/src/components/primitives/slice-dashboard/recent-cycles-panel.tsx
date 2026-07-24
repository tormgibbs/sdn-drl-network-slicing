import type { RecentCycle } from "../../../types/slice1";

export function RecentCyclesPanel({ cycles, cols = ["THRPT", "LAT"] }: { cycles: RecentCycle[]; cols?: [string, string] }) {
  return (
    <div className="flex flex-col flex-1 overflow-hidden border-b border-white/10">
      <div className="px-4 h-8 flex items-center border-b border-white/10 bg-white/[0.03] shrink-0">
        <span className="font-mono text-[10px] text-white/40 uppercase tracking-widest">Recent Cycles</span>
      </div>
      <div className="overflow-y-auto flex-1">
        <table className="w-full text-[10px] font-mono">
          <thead>
            <tr className="border-b border-white/10">
              <th className="w-6 px-3 py-1.5 text-left text-white/30 font-normal">ST</th>
              <th className="px-3 py-1.5 text-left text-white/30 font-normal">CYCLE ID</th>
              <th className="px-3 py-1.5 text-right text-white/30 font-normal">{cols[0]}</th>
              <th className="px-3 py-1.5 text-right text-white/30 font-normal">{cols[1]}</th>
            </tr>
          </thead>
          <tbody>
            {cycles.slice(0, 7).map((c) => {
              const isViolation = c.status === "VIOLATION";
              return (
                <tr key={c.id} className="border-b border-white/5 hover:bg-white/[0.02]">
                  <td className="px-3 py-1.5">
                    <span className={[
                      "inline-block w-1.5 h-1.5 rounded-full",
                      isViolation ? "bg-amber-400" : "bg-transparent border border-white/15",
                    ].join(" ")} />
                  </td>
                  <td className={["px-3 py-1.5", isViolation ? "text-amber-400" : "text-white/60"].join(" ")}>{c.id}</td>
                  <td className={["px-3 py-1.5 text-right", isViolation ? "text-amber-400" : "text-white/60"].join(" ")}>{c.thrpt}</td>
                  <td className={["px-3 py-1.5 text-right", isViolation ? "text-amber-400" : "text-white/60"].join(" ")}>{c.lat}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}