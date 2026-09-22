import { chartsApi } from "../api/client";
import type { AssumptionCheck, Chart, ResultTable, StatResult } from "../types";

function fmt(v: number | string | null | undefined, digits = 4): string {
  if (v === null || v === undefined) return "—";
  if (typeof v === "string") return v;
  if (Number.isInteger(v)) return String(v);
  const abs = Math.abs(v);
  if (abs !== 0 && (abs < 1e-3 || abs >= 1e5)) return v.toExponential(2);
  return Number(v.toFixed(digits)).toString();
}

function pValueText(p: number | null): string {
  if (p === null) return "—";
  return p < 0.0001 ? "< 0.0001" : p.toFixed(4);
}

function ResultTableView({ table }: { table: ResultTable }) {
  return (
    <div className="mt-3">
      <p className="text-xs font-medium text-slate-500">{table.title}</p>
      <div className="mt-1 overflow-x-auto">
        <table className="min-w-full divide-y divide-slate-200 text-xs">
          <thead>
            <tr>
              {table.columns.map((c) => (
                <th key={c} className="whitespace-nowrap px-2 py-1.5 text-left font-medium text-slate-600">
                  {c}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {table.rows.map((row, i) => (
              <tr key={i}>
                {row.map((cell, j) => (
                  <td key={j} className="whitespace-nowrap px-2 py-1.5 text-slate-700">
                    {cell === null ? "—" : String(cell)}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function AssumptionRow({ a }: { a: AssumptionCheck }) {
  const tone =
    a.passed === true
      ? "border-emerald-200 bg-emerald-50 text-emerald-800"
      : a.passed === false
        ? "border-amber-200 bg-amber-50 text-amber-800"
        : "border-slate-200 bg-slate-50 text-slate-600";
  const mark = a.passed === true ? "✓" : a.passed === false ? "!" : "?";
  return (
    <li className={`rounded-md border px-3 py-2 text-xs ${tone}`}>
      <span className="font-semibold">{mark} {a.label}</span>
      <p className="mt-0.5">{a.detail}</p>
      {a.recommendation && <p className="mt-0.5 italic">{a.recommendation}</p>}
    </li>
  );
}

interface Props {
  result: StatResult;
  charts?: Chart[];
  onRegenerateChart?: (kind: string) => void;
}

export function AnalysisResult({ result, charts = [], onRegenerateChart }: Props) {
  const f = result.frequentist;
  const b = result.bayesian;
  const chart = charts.length > 0 ? charts[charts.length - 1] : null;
  const kinds = chart?.spec.available_kinds ?? [];

  return (
    <div className="space-y-4">
      <p className="text-xs text-slate-500">
        {result.method_label} · n = {result.n_used}
        {result.n_excluded > 0 && ` (${result.n_excluded} row(s) excluded for missing data)`}
      </p>

      <div className="grid gap-4 md:grid-cols-2">
        {/* Frequentist */}
        <div className="rounded-lg border border-slate-200 bg-white p-4">
          <h4 className="text-sm font-semibold text-slate-900">Frequentist</h4>
          <dl className="mt-2 space-y-1 text-sm">
            {f.statistic.name !== "—" && (
              <div className="flex justify-between gap-4">
                <dt className="text-slate-500">{f.statistic.name}{f.df != null ? ` (df ${fmt(f.df)})` : ""}</dt>
                <dd className="font-medium text-slate-800">{fmt(f.statistic.value)}</dd>
              </div>
            )}
            {f.p_value !== null && (
              <div className="flex justify-between gap-4">
                <dt className="text-slate-500">p-value</dt>
                <dd className="font-medium text-slate-800">{pValueText(f.p_value)}</dd>
              </div>
            )}
            {f.estimate && f.estimate.value !== null && (
              <div className="flex justify-between gap-4">
                <dt className="text-slate-500">{f.estimate.name}</dt>
                <dd className="font-medium text-slate-800">
                  {fmt(f.estimate.value)}
                  {f.estimate.ci_low !== null && (
                    <span className="ml-1 text-xs font-normal text-slate-500">
                      [{fmt(f.estimate.ci_low, 3)}, {fmt(f.estimate.ci_high, 3)}]
                    </span>
                  )}
                </dd>
              </div>
            )}
            {f.effect_size && f.effect_size.value !== null && (
              <div className="flex justify-between gap-4">
                <dt className="text-slate-500">{f.effect_size.name}</dt>
                <dd className="font-medium text-slate-800">
                  {fmt(f.effect_size.value, 3)}
                  {f.effect_size.magnitude && (
                    <span className="ml-1 text-xs font-normal text-slate-500">({f.effect_size.magnitude})</span>
                  )}
                </dd>
              </div>
            )}
          </dl>
          {f.summary && <p className="mt-2 text-xs leading-relaxed text-slate-600">{f.summary}</p>}
        </div>

        {/* Bayesian */}
        <div
          className={`rounded-lg border p-4 ${
            b.available ? "border-slate-200 bg-white" : "border-slate-200 bg-slate-50"
          }`}
        >
          <h4 className="text-sm font-semibold text-slate-900">Bayesian</h4>
          {b.available && b.bayes_factor_10 !== null ? (
            <>
              <dl className="mt-2 space-y-1 text-sm">
                <div className="flex justify-between gap-4">
                  <dt className="text-slate-500">Bayes factor (BF₁₀)</dt>
                  <dd className="font-medium text-slate-800">{fmt(b.bayes_factor_10, 3)}</dd>
                </div>
                {b.bayes_factor_10 < 1 && (
                  <div className="flex justify-between gap-4">
                    <dt className="text-slate-500">BF₀₁</dt>
                    <dd className="font-medium text-slate-800">{fmt(1 / b.bayes_factor_10, 2)}</dd>
                  </div>
                )}
              </dl>
              {b.interpretation && (
                <p className="mt-2 text-xs font-medium capitalize text-slate-700">{b.interpretation}</p>
              )}
              {b.prior && <p className="mt-1 text-[11px] text-slate-400">Prior: {b.prior}</p>}
              <p className="mt-2 text-[11px] italic text-slate-500">
                A Bayes factor is not a p-value and does not by itself denote "significance".
              </p>
            </>
          ) : (
            <p className="mt-2 text-xs leading-relaxed text-slate-500">
              {b.note ?? "No Bayes factor is available for this test."}
            </p>
          )}
        </div>
      </div>

      {chart && (
        <div>
          <div className="flex flex-wrap items-center justify-between gap-2">
            <h4 className="text-xs font-semibold uppercase tracking-wide text-slate-500">Chart</h4>
            {kinds.length > 1 && onRegenerateChart && (
              <div className="flex flex-wrap gap-1.5">
                {kinds.map((k) => (
                  <button
                    key={k}
                    onClick={() => onRegenerateChart(k)}
                    className={`rounded-full border px-2 py-0.5 text-[11px] ${
                      k === chart.kind
                        ? "border-indigo-300 bg-indigo-50 text-indigo-700"
                        : "border-slate-300 text-slate-500 hover:bg-slate-50"
                    }`}
                  >
                    {k.replace(/_/g, " ")}
                  </button>
                ))}
              </div>
            )}
          </div>
          <img
            src={chartsApi.imageUrl(chart.id)}
            alt={chart.title}
            className="mt-2 max-w-full rounded-md border border-slate-200"
          />
        </div>
      )}

      {result.assumptions.length > 0 && (
        <div>
          <h4 className="text-xs font-semibold uppercase tracking-wide text-slate-500">Assumption checks</h4>
          <ul className="mt-2 space-y-1.5">
            {result.assumptions.map((a) => (
              <AssumptionRow key={a.key} a={a} />
            ))}
          </ul>
        </div>
      )}

      {result.tables.map((t, i) => (
        <ResultTableView key={i} table={t} />
      ))}
    </div>
  );
}
