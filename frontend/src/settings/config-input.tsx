export function ConfigInput({
  label,
  value,
  onChange,
  hint,
  readOnly,
}: {
  label:     string;
  value:     string | number;
  onChange?: (v: string) => void;
  hint?:     string;
  readOnly?: boolean;
}) {
  return (
    <div className="flex flex-col gap-1">
      <label className="font-mono text-[9px] font-medium tracking-widest uppercase text-neutral-500">
        {label}
      </label>

      {readOnly ? (
        <div className="h-8 border border-neutral-800 flex items-center px-2 font-mono text-[13px] text-neutral-100 bg-black">
          {value}
        </div>
      ) : (
        <input
          type="text"
          value={value}
          onChange={(e) => onChange?.(e.target.value)}
          className="h-8 bg-black border border-neutral-800 outline-none px-2 font-mono text-[13px] text-neutral-100 w-full focus:border-neutral-100 transition-colors"
        />
      )}

      {hint && (
        <span className="font-mono text-[10px] text-neutral-500 mt-0.5">{hint}</span>
      )}
    </div>
  );
}