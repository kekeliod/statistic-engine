interface Props {
  label: string;
  placeholder: string;
  values: string[];
  onChange: (values: string[]) => void;
  helperText?: string;
}

export function DynamicListInput({ label, placeholder, values, onChange, helperText }: Props) {
  const items = values.length === 0 ? [""] : values;

  function updateAt(index: number, value: string) {
    const next = [...items];
    next[index] = value;
    onChange(next);
  }

  function removeAt(index: number) {
    const next = items.filter((_, i) => i !== index);
    onChange(next.length === 0 ? [""] : next);
  }

  function add() {
    onChange([...items, ""]);
  }

  return (
    <div>
      <label className="block text-sm font-medium text-slate-700">{label}</label>
      {helperText && <p className="mt-0.5 text-xs text-slate-500">{helperText}</p>}
      <div className="mt-2 space-y-2">
        {items.map((value, index) => (
          <div key={index} className="flex gap-2">
            <span className="mt-2 text-xs font-mono text-slate-400 w-5 text-right">{index + 1}.</span>
            <input
              type="text"
              value={value}
              placeholder={placeholder}
              onChange={(e) => updateAt(index, e.target.value)}
              className="flex-1 rounded-md border border-slate-300 px-3 py-2 text-sm focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
            />
            <button
              type="button"
              onClick={() => removeAt(index)}
              className="px-2 text-slate-400 hover:text-red-500"
              aria-label="Remove"
            >
              &times;
            </button>
          </div>
        ))}
      </div>
      <button
        type="button"
        onClick={add}
        className="mt-2 text-sm font-medium text-indigo-600 hover:text-indigo-800"
      >
        + Add another
      </button>
    </div>
  );
}
