export const CustomTooltip = ({ active, payload }: any) => {
  if (!active || !payload?.length) return null;
  return (
    <div className="bg-background border border-border px-2 py-1 text-xs font-mono">
      {payload.map((p: any) => (
        <div key={p.dataKey} style={{ color: p.color }}>
          {p.dataKey}: {Number(p.value).toFixed(1)}
        </div>
      ))}
    </div>
  );
};
