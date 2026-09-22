import { useMemo, useState } from "react";
import type { ColumnProfile, MethodSpec } from "../types";

const DTYPE_FALLBACK: Record<string, string[]> = {
  numeric: ["numeric", "binary", "ordinal"],
  ordinal: ["ordinal", "numeric", "binary", "categorical"],
  binary: ["binary", "categorical"],
  categorical: ["categorical", "binary", "ordinal", "identifier"],
};

function allowedDtypes(roleDtypes: string[]): Set<string> {
  const out = new Set<string>();
  for (const d of roleDtypes) {
    out.add(d);
    for (const f of DTYPE_FALLBACK[d] ?? []) out.add(f);
  }
  return out;
}

export interface MethodPickerPrefill {
  method: string;
  variables: Record<string, string | string[]>;
  objectiveIndex?: number | null;
}

interface Props {
  methods: MethodSpec[];
  columns: ColumnProfile[];
  objectives: string[];
  running: boolean;
  prefill?: MethodPickerPrefill | null;
  onRun: (payload: {
    method: string;
    variables: Record<string, string | string[]>;
    params: Record<string, unknown>;
    objective_index: number | null;
  }) => void;
}

export function MethodPicker({ methods, columns, objectives, running, prefill, onRun }: Props) {
  const [methodKey, setMethodKey] = useState<string>(prefill?.method ?? methods[0]?.key ?? "");
  const [vars, setVars] = useState<Record<string, string | string[]>>(prefill?.variables ?? {});
  const [objectiveIndex, setObjectiveIndex] = useState<number | null>(
    prefill?.objectiveIndex ?? null,
  );
  const [alpha, setAlpha] = useState(0.05);

  // The parent remounts this component (via `key`) when `prefill` changes, so
  // initialising state from `prefill` above is sufficient — no effect needed.
  const method = useMemo(() => methods.find((m) => m.key === methodKey), [methods, methodKey]);

  function optionsFor(roleDtypes: string[]): ColumnProfile[] {
    const allowed = allowedDtypes(roleDtypes);
    const filtered = columns.filter((c) => allowed.has(c.dtype));
    return filtered.length > 0 ? filtered : columns;
  }

  function setRole(role: string, arity: "one" | "many", value: string) {
    setVars((prev) => {
      if (arity === "one") return { ...prev, [role]: value };
      const current = new Set(Array.isArray(prev[role]) ? (prev[role] as string[]) : []);
      if (current.has(value)) current.delete(value);
      else current.add(value);
      return { ...prev, [role]: [...current] };
    });
  }

  const ready =
    !!method &&
    method.roles.every((r) => {
      const v = vars[r.name];
      return r.arity === "one" ? !!v : Array.isArray(v) && v.length > 0;
    });

  return (
    <div className="space-y-4">
      <div className="grid gap-3 sm:grid-cols-2">
        <label className="text-sm">
          <span className="text-slate-500">Method</span>
          <select
            value={methodKey}
            onChange={(e) => {
              setMethodKey(e.target.value);
              setVars({});
            }}
            className="mt-1 w-full rounded-md border border-slate-300 px-2 py-1.5 text-sm"
          >
            {methods.map((m) => (
              <option key={m.key} value={m.key}>
                {m.label} {m.bayesian_supported ? "· Bayes factor" : ""}
              </option>
            ))}
          </select>
        </label>

        <label className="text-sm">
          <span className="text-slate-500">Addresses objective (optional)</span>
          <select
            value={objectiveIndex ?? ""}
            onChange={(e) => setObjectiveIndex(e.target.value === "" ? null : Number(e.target.value))}
            className="mt-1 w-full rounded-md border border-slate-300 px-2 py-1.5 text-sm"
          >
            <option value="">— none —</option>
            {objectives.map((o, i) => (
              <option key={i} value={i}>
                {i + 1}. {o.length > 60 ? o.slice(0, 60) + "…" : o}
              </option>
            ))}
          </select>
        </label>
      </div>

      {method && (
        <p className="rounded-md bg-slate-50 px-3 py-2 text-xs text-slate-600">
          <span className="font-medium">{method.label}.</span> {method.description}{" "}
          <span className="italic">When to use: {method.when_to_use}</span>
        </p>
      )}

      {method?.roles.map((role) => (
        <div key={role.name} className="text-sm">
          <span className="text-slate-500 capitalize">
            {role.name.replace(/_/g, " ")}{" "}
            <span className="text-xs text-slate-400">({role.description})</span>
          </span>
          {role.arity === "one" ? (
            <select
              value={(vars[role.name] as string) ?? ""}
              onChange={(e) => setRole(role.name, "one", e.target.value)}
              className="mt-1 w-full rounded-md border border-slate-300 px-2 py-1.5 text-sm"
            >
              <option value="">— select a column —</option>
              {optionsFor(role.dtypes).map((c) => (
                <option key={c.name} value={c.name}>
                  {c.name} ({c.dtype})
                </option>
              ))}
            </select>
          ) : (
            <div className="mt-1 flex flex-wrap gap-2">
              {optionsFor(role.dtypes).map((c) => {
                const selected = Array.isArray(vars[role.name]) && (vars[role.name] as string[]).includes(c.name);
                return (
                  <button
                    type="button"
                    key={c.name}
                    onClick={() => setRole(role.name, "many", c.name)}
                    className={`rounded-full border px-2.5 py-1 text-xs ${
                      selected
                        ? "border-indigo-300 bg-indigo-50 text-indigo-700"
                        : "border-slate-300 text-slate-600 hover:bg-slate-50"
                    }`}
                  >
                    {c.name}
                  </button>
                );
              })}
            </div>
          )}
        </div>
      ))}

      <div className="flex items-center gap-3">
        <label className="text-sm text-slate-500">
          α
          <input
            type="number"
            step="0.01"
            min="0.001"
            max="0.2"
            value={alpha}
            onChange={(e) => setAlpha(Number(e.target.value))}
            className="ml-2 w-20 rounded-md border border-slate-300 px-2 py-1 text-sm"
          />
        </label>
        <button
          type="button"
          disabled={!ready || running}
          onClick={() =>
            onRun({
              method: methodKey,
              variables: vars,
              params: { alpha },
              objective_index: objectiveIndex,
            })
          }
          className="rounded-md bg-indigo-600 px-4 py-1.5 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-50"
        >
          {running ? "Running…" : "Run analysis"}
        </button>
      </div>
    </div>
  );
}
