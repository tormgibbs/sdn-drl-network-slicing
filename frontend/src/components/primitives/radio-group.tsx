type RadioGroupProps<T extends string> = {
  options: { value: T; label: string }[];
  value: T;
  onChange: (value: T) => void;
};

export function RadioGroup<T extends string>({
  options,
  value,
  onChange,
}: RadioGroupProps<T>) {
  return (
    <div className="flex flex-col gap-4">
      {options.map((option) => (
        <label
          key={option.value}
          className={`${value === option.value ? "bg-white text-black" : ""} p-2 flex gap-2 cursor-pointer`}
        >
          <input
            type="radio"
            value={option.value}
            checked={value === option.value}
            onChange={(e) => onChange(e.target.value as T)}
            className="accent-green-500"
          />
          <span>{option.label}</span>
        </label>
      ))}
    </div>
  );
}
