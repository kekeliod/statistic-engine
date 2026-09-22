import type { DataQualityReport } from "../types";

function scoreColor(score: number): string {
  if (score >= 90) return "text-emerald-600 bg-emerald-50 border-emerald-200";
  if (score >= 70) return "text-amber-600 bg-amber-50 border-amber-200";
  return "text-red-600 bg-red-50 border-red-200";
}

function ScoreBadge({ label, score }: { label: string; score: number }) {
  return (
    <div className={`rounded-md border px-3 py-2 text-center ${scoreColor(score)}`}>
      <div className="text-lg font-semibold">{score}</div>
      <div className="text-[11px] uppercase tracking-wide">{label}</div>
    </div>
  );
}

function formatNumber(n: number | null): string {
  if (n === null) return "—";
  return Number.isInteger(n) ? String(n) : n.toFixed(3).replace(/\.?0+$/, "");
}

export function DataQualityPanel({ report }: { report: DataQualityReport }) {
  const { score } = report;

  return (
    <div className="space-y-6">
      <section className="rounded-lg border border-slate-200 bg-white p-5">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div>
            <h2 className="font-medium text-slate-900">Data Quality Score</h2>
            <p className="mt-1 text-xs text-slate-500">{score.formula}</p>
          </div>
          <div className={`rounded-lg border px-5 py-3 text-center ${scoreColor(score.overall)}`}>
            <div className="text-3xl font-bold">{score.overall}</div>
            <div className="text-xs uppercase tracking-wide">out of 100</div>
          </div>
        </div>

        <div className="mt-4 grid grid-cols-2 gap-2 sm:grid-cols-5">
          <ScoreBadge label="Completeness" score={score.completeness} />
          <ScoreBadge label="Validity" score={score.validity} />
          <ScoreBadge label="Consistency" score={score.consistency} />
          <ScoreBadge label="Duplicates" score={score.duplicates} />
          <ScoreBadge label="Outliers" score={score.outliers} />
        </div>

        {score.notes.length > 0 && (
          <ul className="mt-4 space-y-1 text-xs text-slate-500">
            {score.notes.map((note, i) => (
              <li key={i}>&middot; {note}</li>
            ))}
          </ul>
        )}
      </section>

      <section className="rounded-lg border border-slate-200 bg-white p-5">
        <h2 className="font-medium text-slate-900">Column Profile</h2>
        <div className="mt-3 overflow-x-auto">
          <table className="min-w-full divide-y divide-slate-200 text-sm">
            <thead>
              <tr>
                {["Column", "Type", "Missing", "Unique", "Mean", "Median", "Min", "Max", "Top values"].map(
                  (h) => (
                    <th
                      key={h}
                      className="whitespace-nowrap px-3 py-2 text-left font-medium text-slate-600"
                    >
                      {h}
                    </th>
                  )
                )}
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {report.columns.map((c) => (
                <tr key={c.name}>
                  <td className="whitespace-nowrap px-3 py-2 font-medium text-slate-800">{c.name}</td>
                  <td className="whitespace-nowrap px-3 py-2 text-slate-600">{c.dtype}</td>
                  <td className="whitespace-nowrap px-3 py-2 text-slate-600">
                    {c.missing_count} ({c.missing_pct}%)
                  </td>
                  <td className="whitespace-nowrap px-3 py-2 text-slate-600">{c.unique_count}</td>
                  <td className="whitespace-nowrap px-3 py-2 text-slate-600">{formatNumber(c.mean)}</td>
                  <td className="whitespace-nowrap px-3 py-2 text-slate-600">{formatNumber(c.median)}</td>
                  <td className="whitespace-nowrap px-3 py-2 text-slate-600">{formatNumber(c.min)}</td>
                  <td className="whitespace-nowrap px-3 py-2 text-slate-600">{formatNumber(c.max)}</td>
                  <td className="px-3 py-2 text-slate-600">
                    {c.top_values
                      ?.map((t) => `${t.value} (${t.count})`)
                      .join(", ") ?? "—"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section className="rounded-lg border border-slate-200 bg-white p-5">
        <h2 className="font-medium text-slate-900">Duplicate Rows</h2>
        {report.duplicates.duplicate_row_count === 0 ? (
          <p className="mt-2 text-sm text-slate-500">No exact duplicate rows detected.</p>
        ) : (
          <>
            <p className="mt-2 text-sm text-slate-700">
              {report.duplicates.duplicate_row_count} duplicate row
              {report.duplicates.duplicate_row_count === 1 ? "" : "s"} (
              {report.duplicates.duplicate_row_pct}% of the dataset). Not removed automatically &mdash;
              review before deciding whether to exclude them.
            </p>
            <ul className="mt-2 space-y-1 text-xs text-slate-500">
              {report.duplicates.example_groups.map((group, i) => (
                <li key={i}>Rows {group.map((r) => r + 1).join(", ")} are identical</li>
              ))}
            </ul>
          </>
        )}
      </section>

      <section className="rounded-lg border border-slate-200 bg-white p-5">
        <h2 className="font-medium text-slate-900">Potential Outliers</h2>
        {report.outliers.length === 0 ? (
          <p className="mt-2 text-sm text-slate-500">No potential outliers detected (IQR method).</p>
        ) : (
          <div className="mt-2 space-y-3">
            {report.outliers.map((o) => (
              <div key={o.column} className="rounded-md border border-amber-200 bg-amber-50 p-3 text-sm">
                <p className="font-medium text-slate-800">
                  {o.column} &mdash; {o.count} potential outlier{o.count === 1 ? "" : "s"} ({o.pct}%)
                </p>
                <p className="mt-1 text-xs text-slate-600">
                  {o.method}. Plausible range: {formatNumber(o.lower_bound)} to{" "}
                  {formatNumber(o.upper_bound)}. Not removed automatically &mdash; review before
                  deciding whether to exclude them.
                </p>
                <p className="mt-1 text-xs text-slate-500">
                  Examples: {o.example_values.map(formatNumber).join(", ")} (rows{" "}
                  {o.example_row_indices.map((r) => r + 1).join(", ")})
                </p>
              </div>
            ))}
          </div>
        )}
      </section>

      <section className="rounded-lg border border-slate-200 bg-white p-5">
        <h2 className="font-medium text-slate-900">Potential Invalid Values</h2>
        {report.invalid_values.length === 0 ? (
          <p className="mt-2 text-sm text-slate-500">No suspicious values detected.</p>
        ) : (
          <div className="mt-2 space-y-3">
            {report.invalid_values.map((v, i) => (
              <div key={i} className="rounded-md border border-red-200 bg-red-50 p-3 text-sm">
                <p className="font-medium text-slate-800">
                  {v.column} &mdash; {v.count} flagged value{v.count === 1 ? "" : "s"}
                </p>
                <p className="mt-1 text-xs text-slate-600">{v.detail}</p>
                <p className="mt-1 text-xs text-slate-500">Examples: {v.examples.join(", ")}</p>
              </div>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}
