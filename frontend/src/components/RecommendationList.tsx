import { useState } from "react";
import type { MethodSpec, Recommendation } from "../types";

const CONFIDENCE_TONE: Record<string, string> = {
  high: "bg-emerald-50 text-emerald-700",
  medium: "bg-amber-50 text-amber-700",
  low: "bg-slate-100 text-slate-500",
};

interface Props {
  recommendations: Recommendation[];
  methods: MethodSpec[];
  source: "ai" | "rules" | null;
  loading: boolean;
  onRefresh: () => void;
  onAccept: (rec: Recommendation) => void;
}

export function RecommendationList({
  recommendations,
  methods,
  source,
  loading,
  onRefresh,
  onAccept,
}: Props) {
  const [openWhy, setOpenWhy] = useState<number | null>(null);

  return (
    <section className="rounded-lg border border-slate-200 bg-white p-5">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h2 className="font-medium text-slate-900">Recommended Analyses</h2>
        <div className="flex items-center gap-2">
          {source && (
            <span
              className={`rounded px-2 py-0.5 text-[11px] ${
                source === "ai" ? "bg-indigo-50 text-indigo-700" : "bg-slate-100 text-slate-500"
              }`}
            >
              {source === "ai" ? "AI-generated" : "rule-based (no AI key)"}
            </span>
          )}
          <button
            onClick={onRefresh}
            disabled={loading}
            className="rounded-md border border-slate-300 px-3 py-1 text-xs text-slate-600 hover:bg-slate-50 disabled:opacity-50"
          >
            {loading ? "Thinking…" : recommendations.length ? "Refresh" : "Get recommendations"}
          </button>
        </div>
      </div>

      {recommendations.length === 0 && !loading && (
        <p className="mt-3 text-sm text-slate-500">
          Get analysis suggestions mapped to each research objective.
        </p>
      )}

      <div className="mt-4 space-y-3">
        {recommendations.map((rec, i) => {
          const method = methods.find((m) => m.key === rec.method_key);
          const alt = rec.alternative_method_key
            ? methods.find((m) => m.key === rec.alternative_method_key)
            : null;
          return (
            <div key={i} className="rounded-md border border-slate-200 p-3">
              <div className="flex flex-wrap items-start justify-between gap-2">
                <div>
                  {rec.objective_index != null && (
                    <p className="text-[11px] font-medium uppercase tracking-wide text-slate-400">
                      Objective {rec.objective_index + 1}
                    </p>
                  )}
                  <p className="text-sm font-medium text-slate-900">
                    {method?.label ?? rec.method_key}
                    <span
                      className={`ml-2 rounded px-1.5 py-0.5 text-[11px] font-normal ${
                        CONFIDENCE_TONE[rec.confidence] ?? ""
                      }`}
                    >
                      {rec.confidence} confidence
                    </span>
                    {method?.bayesian_supported && (
                      <span className="ml-1 rounded bg-indigo-50 px-1.5 py-0.5 text-[11px] font-normal text-indigo-700">
                        Bayes factor
                      </span>
                    )}
                  </p>
                </div>
                <button
                  onClick={() => onAccept(rec)}
                  className="rounded-md bg-indigo-600 px-3 py-1 text-xs font-medium text-white hover:bg-indigo-700"
                >
                  Use this
                </button>
              </div>

              <p className="mt-1 text-xs text-slate-600">{rec.rationale}</p>

              <p className="mt-1 text-[11px] text-slate-500">
                Variables:{" "}
                {Object.entries(rec.suggested_variables)
                  .map(([k, v]) => `${k} → ${Array.isArray(v) ? v.join(", ") : v}`)
                  .join("  ·  ") || "—"}
              </p>

              <div className="mt-1.5 flex flex-wrap items-center gap-3 text-[11px] text-slate-500">
                {rec.chart_suggestion && <span>Chart: {rec.chart_suggestion}</span>}
                {alt && <span>Alternative: {alt.label}</span>}
                {method && (
                  <button
                    onClick={() => setOpenWhy(openWhy === i ? null : i)}
                    className="text-indigo-600 hover:underline"
                  >
                    {openWhy === i ? "Hide" : "Why this method?"}
                  </button>
                )}
              </div>
              {openWhy === i && method && (
                <p className="mt-1.5 rounded bg-slate-50 px-2 py-1.5 text-[11px] text-slate-600">
                  {method.description} <span className="italic">{method.when_to_use}</span>
                </p>
              )}
            </div>
          );
        })}
      </div>
    </section>
  );
}
