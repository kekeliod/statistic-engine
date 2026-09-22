import { useCallback, useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import {
  analysesApi,
  chartsApi,
  datasetsApi,
  extractErrorMessage,
  getSheetSelectionRequired,
  healthApi,
  methodsApi,
  projectsApi,
  recommendationsApi,
} from "../api/client";
import { AnalysisResult } from "../components/AnalysisResult";
import { ChatPanel } from "../components/ChatPanel";
import { DataQualityPanel } from "../components/DataQualityPanel";
import { MethodPicker, type MethodPickerPrefill } from "../components/MethodPicker";
import { RecommendationList } from "../components/RecommendationList";
import { ReportPanel } from "../components/ReportPanel";
import type {
  Analysis,
  DataQualityReport,
  Dataset,
  DatasetPreview,
  MethodSpec,
  Project,
  Recommendation,
} from "../types";

const PAGE_SIZE = 25;

const WORKFLOW_STEPS = [
  { key: "objective", label: "Research Objective", active: true },
  { key: "data", label: "Dataset", active: true },
  { key: "quality", label: "Data Quality", active: true },
  { key: "recommend", label: "Recommended Analysis", active: true },
  { key: "run", label: "Run Analysis", active: true },
  { key: "interpret", label: "Interpretation", active: true },
  { key: "report", label: "Report", active: true },
];

export default function ProjectDetail() {
  const { id } = useParams<{ id: string }>();
  const projectId = Number(id);

  const [project, setProject] = useState<Project | null>(null);
  const [datasets, setDatasets] = useState<Dataset[]>([]);
  const [selectedDatasetId, setSelectedDatasetId] = useState<number | null>(null);
  const [preview, setPreview] = useState<DatasetPreview | null>(null);
  const [offset, setOffset] = useState(0);
  const [quality, setQuality] = useState<DataQualityReport | null>(null);
  const [qualityLoading, setQualityLoading] = useState(false);
  const [qualityError, setQualityError] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [uploading, setUploading] = useState(false);
  const [methods, setMethods] = useState<MethodSpec[]>([]);
  const [analyses, setAnalyses] = useState<Analysis[]>([]);
  const [running, setRunning] = useState(false);
  const [analysisError, setAnalysisError] = useState<string | null>(null);
  const [expanded, setExpanded] = useState<Set<number>>(new Set());
  const [recommendations, setRecommendations] = useState<Recommendation[]>([]);
  const [recSource, setRecSource] = useState<"ai" | "rules" | null>(null);
  const [recLoading, setRecLoading] = useState(false);
  const [prefill, setPrefill] = useState<MethodPickerPrefill | null>(null);
  const [aiAvailable, setAiAvailable] = useState(false);
  const [sheetChoice, setSheetChoice] = useState<{ file: File; sheets: string[]; selected: string } | null>(
    null
  );

  const loadProjectAndDatasets = useCallback(async () => {
    try {
      const [proj, ds] = await Promise.all([
        projectsApi.get(projectId),
        datasetsApi.listForProject(projectId),
      ]);
      setProject(proj);
      setDatasets(ds);
      const active = ds.find((d) => d.is_active) ?? ds[0] ?? null;
      setSelectedDatasetId(active ? active.id : null);
    } catch (err) {
      setError(extractErrorMessage(err));
    }
  }, [projectId]);

  useEffect(() => {
    loadProjectAndDatasets();
  }, [loadProjectAndDatasets]);

  useEffect(() => {
    methodsApi.list().then(setMethods).catch(() => setMethods([]));
    healthApi.get().then((h) => setAiAvailable(h.ai_available)).catch(() => setAiAvailable(false));
  }, []);

  async function loadRecommendations() {
    if (selectedDatasetId == null) return;
    setRecLoading(true);
    try {
      const recs = await recommendationsApi.forProject(projectId, selectedDatasetId);
      setRecommendations(recs);
      setRecSource(recs[0]?.source ?? "rules");
    } catch (err) {
      setAnalysisError(extractErrorMessage(err));
    } finally {
      setRecLoading(false);
    }
  }

  function acceptRecommendation(rec: Recommendation) {
    setPrefill({
      method: rec.method_key,
      variables: rec.suggested_variables,
      objectiveIndex: rec.objective_index,
    });
    document.getElementById("run-analysis")?.scrollIntoView({ behavior: "smooth" });
  }

  const loadAnalyses = useCallback(() => {
    analysesApi
      .listForProject(projectId)
      .then(setAnalyses)
      .catch(() => setAnalyses([]));
  }, [projectId]);

  useEffect(() => {
    loadAnalyses();
  }, [loadAnalyses]);

  async function runAnalysis(payload: {
    method: string;
    variables: Record<string, string | string[]>;
    params: Record<string, unknown>;
    objective_index: number | null;
  }) {
    if (selectedDatasetId == null) return;
    setRunning(true);
    setAnalysisError(null);
    try {
      const created = await analysesApi.create(projectId, {
        dataset_id: selectedDatasetId,
        ...payload,
      });
      setAnalyses((prev) => [created, ...prev]);
      setExpanded((prev) => new Set(prev).add(created.id));
    } catch (err) {
      setAnalysisError(extractErrorMessage(err));
    } finally {
      setRunning(false);
    }
  }

  async function rerunAnalysis(id: number) {
    const updated = await analysesApi.rerun(id);
    setAnalyses((prev) => prev.map((a) => (a.id === id ? updated : a)));
  }

  async function regenerateChart(analysisId: number, kind: string) {
    const chart = await chartsApi.create(analysisId, kind);
    setAnalyses((prev) =>
      prev.map((a) => (a.id === analysisId ? { ...a, charts: [...a.charts, chart] } : a)),
    );
  }

  async function deleteAnalysis(id: number) {
    await analysesApi.remove(id);
    setAnalyses((prev) => prev.filter((a) => a.id !== id));
  }

  function toggleExpanded(id: number) {
    setExpanded((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  useEffect(() => {
    if (selectedDatasetId == null) {
      setPreview(null);
      setQuality(null);
      return;
    }
    setOffset(0);
    datasetsApi
      .preview(selectedDatasetId, 0, PAGE_SIZE)
      .then(setPreview)
      .catch((err) => setError(extractErrorMessage(err)));

    setQuality(null);
    setQualityError(null);
    setQualityLoading(true);
    datasetsApi
      .quality(selectedDatasetId)
      .then(setQuality)
      .catch((err) => setQualityError(extractErrorMessage(err)))
      .finally(() => setQualityLoading(false));
  }, [selectedDatasetId]);

  useEffect(() => {
    if (selectedDatasetId == null) return;
    datasetsApi
      .preview(selectedDatasetId, offset, PAGE_SIZE)
      .then(setPreview)
      .catch((err) => setError(extractErrorMessage(err)));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [offset]);

  async function doUpload(file: File, sheetName?: string) {
    setUploading(true);
    setUploadError(null);
    try {
      const dataset = await datasetsApi.upload(projectId, file, sheetName);
      await loadProjectAndDatasets();
      setSelectedDatasetId(dataset.id);
      setSheetChoice(null);
    } catch (err) {
      const sheets = getSheetSelectionRequired(err);
      if (sheets && sheets.length > 0) {
        setSheetChoice({ file, sheets, selected: sheets[0] });
      } else {
        setUploadError(extractErrorMessage(err));
      }
    } finally {
      setUploading(false);
    }
  }

  async function handleUpload(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    e.target.value = "";
    if (!file) return;
    await doUpload(file);
  }

  if (error) {
    return (
      <div className="mx-auto max-w-4xl px-6 py-10">
        <div className="rounded-md border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          {error}
        </div>
      </div>
    );
  }

  if (!project) {
    return <div className="mx-auto max-w-4xl px-6 py-10 text-sm text-slate-500">Loading...</div>;
  }

  return (
    <div className="mx-auto max-w-5xl px-6 py-10">
      <h1 className="text-2xl font-semibold text-slate-900">{project.title}</h1>
      <p className="mt-1 text-sm text-slate-600">{project.research_aim}</p>

      {/* Workflow pipeline */}
      <div className="mt-6 flex flex-wrap items-center gap-2 rounded-lg border border-slate-200 bg-white p-3">
        {WORKFLOW_STEPS.map((step, i) => (
          <div key={step.key} className="flex items-center gap-2">
            <span
              className={`rounded-full px-3 py-1 text-xs font-medium ${
                step.active
                  ? "bg-indigo-100 text-indigo-700"
                  : "bg-slate-100 text-slate-400"
              }`}
              title={step.active ? undefined : "Coming in a later phase"}
            >
              {step.label}
            </span>
            {i < WORKFLOW_STEPS.length - 1 && <span className="text-slate-300">&rarr;</span>}
          </div>
        ))}
      </div>

      <div className="mt-8 grid gap-6 md:grid-cols-2">
        <section className="rounded-lg border border-slate-200 bg-white p-5">
          <h2 className="font-medium text-slate-900">Research Context</h2>
          <dl className="mt-3 space-y-3 text-sm">
            <div>
              <dt className="font-medium text-slate-500">Objectives</dt>
              <dd>
                {project.objectives.length === 0 ? (
                  <span className="text-slate-400">None specified</span>
                ) : (
                  <ol className="mt-1 list-decimal space-y-1 pl-5">
                    {project.objectives.map((o, i) => (
                      <li key={i}>{o}</li>
                    ))}
                  </ol>
                )}
              </dd>
            </div>
            <div>
              <dt className="font-medium text-slate-500">Research Questions</dt>
              <dd>
                {project.research_questions.length === 0 ? (
                  <span className="text-slate-400">None specified</span>
                ) : (
                  <ul className="mt-1 list-disc space-y-1 pl-5">
                    {project.research_questions.map((q, i) => (
                      <li key={i}>{q}</li>
                    ))}
                  </ul>
                )}
              </dd>
            </div>
            <div>
              <dt className="font-medium text-slate-500">Hypotheses</dt>
              <dd>
                {project.hypotheses.length === 0 ? (
                  <span className="text-slate-400">None specified</span>
                ) : (
                  <ul className="mt-1 list-disc space-y-1 pl-5">
                    {project.hypotheses.map((h, i) => (
                      <li key={i}>{h}</li>
                    ))}
                  </ul>
                )}
              </dd>
            </div>
          </dl>
        </section>

        <section className="rounded-lg border border-slate-200 bg-white p-5">
          <div className="flex items-center justify-between">
            <h2 className="font-medium text-slate-900">Dataset</h2>
            <label className="cursor-pointer rounded-md bg-indigo-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-indigo-700">
              {uploading ? "Uploading..." : "Upload CSV/XLSX"}
              <input
                type="file"
                accept=".csv,.xlsx,.xls"
                className="hidden"
                onChange={handleUpload}
                disabled={uploading}
              />
            </label>
          </div>

          {uploadError && (
            <p className="mt-2 text-xs text-red-600">{uploadError}</p>
          )}

          {sheetChoice && (
            <div className="mt-3 rounded-md border border-indigo-200 bg-indigo-50 p-3">
              <p className="text-xs text-slate-700">
                <span className="font-medium">{sheetChoice.file.name}</span> has multiple sheets.
                Which one should be uploaded as this dataset?
              </p>
              <div className="mt-2 flex items-center gap-2">
                <select
                  value={sheetChoice.selected}
                  onChange={(e) => setSheetChoice({ ...sheetChoice, selected: e.target.value })}
                  className="flex-1 rounded-md border border-slate-300 px-2 py-1.5 text-sm"
                >
                  {sheetChoice.sheets.map((s) => (
                    <option key={s} value={s}>
                      {s}
                    </option>
                  ))}
                </select>
                <button
                  type="button"
                  disabled={uploading}
                  onClick={() => doUpload(sheetChoice.file, sheetChoice.selected)}
                  className="rounded-md bg-indigo-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-indigo-700 disabled:opacity-50"
                >
                  {uploading ? "Uploading..." : "Upload this sheet"}
                </button>
                <button
                  type="button"
                  onClick={() => setSheetChoice(null)}
                  className="rounded-md border border-slate-300 px-3 py-1.5 text-xs text-slate-600 hover:bg-slate-100"
                >
                  Cancel
                </button>
              </div>
              <p className="mt-2 text-xs text-slate-500">
                Need other sheets too? Upload again after this one finishes &mdash; each sheet
                becomes its own dataset version.
              </p>
            </div>
          )}

          {datasets.length === 0 && !sheetChoice && (
            <p className="mt-3 text-sm text-slate-500">
              No dataset uploaded yet. Upload a CSV or Excel file to see a preview.
            </p>
          )}

          {datasets.length > 0 && (
            <div className="mt-3">
              <select
                value={selectedDatasetId ?? ""}
                onChange={(e) => setSelectedDatasetId(Number(e.target.value))}
                className="w-full rounded-md border border-slate-300 px-2 py-1.5 text-sm"
              >
                {datasets.map((d) => (
                  <option key={d.id} value={d.id}>
                    v{d.version} &mdash; {d.original_filename}
                    {d.sheet_name ? ` [${d.sheet_name.trim()}]` : ""} ({d.n_rows} rows &times;{" "}
                    {d.n_columns} cols)
                    {d.is_active ? " [active]" : ""}
                  </option>
                ))}
              </select>
            </div>
          )}
        </section>
      </div>

      {preview && (
        <section className="mt-8 rounded-lg border border-slate-200 bg-white p-5">
          <div className="flex items-center justify-between">
            <h2 className="font-medium text-slate-900">Raw Data Preview</h2>
            <span className="text-xs text-slate-500">
              Rows {preview.offset + 1}&ndash;
              {Math.min(preview.offset + preview.limit, preview.total_rows)} of {preview.total_rows}
            </span>
          </div>

          <div className="mt-3 overflow-x-auto">
            <table className="min-w-full divide-y divide-slate-200 text-sm">
              <thead>
                <tr>
                  {preview.columns.map((c) => (
                    <th
                      key={c}
                      className="whitespace-nowrap px-3 py-2 text-left font-medium text-slate-600"
                    >
                      {c}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {preview.rows.map((row, i) => (
                  <tr key={i}>
                    {preview.columns.map((c) => (
                      <td key={c} className="whitespace-nowrap px-3 py-2 text-slate-700">
                        {row[c] === null || row[c] === undefined ? (
                          <span className="text-slate-300 italic">null</span>
                        ) : (
                          String(row[c])
                        )}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="mt-3 flex items-center justify-end gap-2">
            <button
              disabled={offset === 0}
              onClick={() => setOffset(Math.max(0, offset - PAGE_SIZE))}
              className="rounded-md border border-slate-300 px-3 py-1 text-xs disabled:opacity-40"
            >
              Previous
            </button>
            <button
              disabled={offset + PAGE_SIZE >= preview.total_rows}
              onClick={() => setOffset(offset + PAGE_SIZE)}
              className="rounded-md border border-slate-300 px-3 py-1 text-xs disabled:opacity-40"
            >
              Next
            </button>
          </div>
        </section>
      )}

      {qualityLoading && (
        <p className="mt-8 text-sm text-slate-500">Assessing data quality...</p>
      )}

      {qualityError && (
        <div className="mt-8 rounded-md border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          {qualityError}
        </div>
      )}

      {quality && (
        <div className="mt-8">
          <DataQualityPanel report={quality} />
        </div>
      )}

      {selectedDatasetId != null && quality && (
        <div className="mt-8">
          <RecommendationList
            recommendations={recommendations}
            methods={methods}
            source={recSource}
            loading={recLoading}
            onRefresh={loadRecommendations}
            onAccept={acceptRecommendation}
          />
        </div>
      )}

      {selectedDatasetId != null && quality && (
        <section id="run-analysis" className="mt-6 rounded-lg border border-slate-200 bg-white p-5">
          <h2 className="font-medium text-slate-900">Run Analysis</h2>
          <p className="mt-1 text-xs text-slate-500">
            Every test reports the frequentist result and, where one is defined, the Bayesian
            Bayes factor side by side.
          </p>
          <div className="mt-4">
            <MethodPicker
              key={prefill ? `${prefill.method}-${JSON.stringify(prefill.variables)}` : "blank"}
              methods={methods}
              columns={quality.columns}
              objectives={project.objectives}
              running={running}
              prefill={prefill}
              onRun={runAnalysis}
            />
          </div>
          {analysisError && <p className="mt-3 text-xs text-red-600">{analysisError}</p>}
        </section>
      )}

      {analyses.length > 0 && (
        <section className="mt-6 space-y-3">
          <h2 className="font-medium text-slate-900">Analyses &amp; Interpretation</h2>
          {analyses.map((a) => {
            const method = methods.find((m) => m.key === a.method);
            const isOpen = expanded.has(a.id);
            return (
              <div key={a.id} className="rounded-lg border border-slate-200 bg-white p-4">
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div>
                    <p className="text-sm font-medium text-slate-900">
                      {method?.label ?? a.method}
                      {a.objective_index != null && (
                        <span className="ml-2 rounded bg-slate-100 px-1.5 py-0.5 text-[11px] font-normal text-slate-500">
                          Objective {a.objective_index + 1}
                        </span>
                      )}
                      <span
                        className={`ml-2 rounded px-1.5 py-0.5 text-[11px] font-normal ${
                          a.status === "complete"
                            ? "bg-emerald-50 text-emerald-700"
                            : a.status === "failed"
                              ? "bg-red-50 text-red-700"
                              : "bg-slate-100 text-slate-500"
                        }`}
                      >
                        {a.status}
                      </span>
                    </p>
                    <p className="mt-0.5 text-xs text-slate-500">
                      {Object.entries(a.variables)
                        .map(([k, v]) => `${k}: ${Array.isArray(v) ? v.join(", ") : v}`)
                        .join("  ·  ")}
                    </p>
                  </div>
                  <div className="flex gap-2 text-xs">
                    {a.status === "complete" && (
                      <button
                        onClick={() => toggleExpanded(a.id)}
                        className="rounded-md border border-slate-300 px-2 py-1 text-slate-600 hover:bg-slate-50"
                      >
                        {isOpen ? "Hide details" : "Show details"}
                      </button>
                    )}
                    <button
                      onClick={() => rerunAnalysis(a.id)}
                      className="rounded-md border border-slate-300 px-2 py-1 text-slate-600 hover:bg-slate-50"
                    >
                      Re-run
                    </button>
                    <button
                      onClick={() => deleteAnalysis(a.id)}
                      className="rounded-md border border-slate-300 px-2 py-1 text-red-600 hover:bg-red-50"
                    >
                      Delete
                    </button>
                  </div>
                </div>

                {a.status === "failed" && (
                  <p className="mt-2 rounded-md border border-red-200 bg-red-50 px-3 py-2 text-xs text-red-700">
                    {a.error}
                  </p>
                )}

                {a.interpretation && (
                  <p className="mt-2 text-sm leading-relaxed text-slate-700">{a.interpretation}</p>
                )}

                {isOpen && a.result && (
                  <div className="mt-4 border-t border-slate-100 pt-4">
                    <AnalysisResult
                      result={a.result}
                      charts={a.charts}
                      onRegenerateChart={(kind) => regenerateChart(a.id, kind)}
                    />
                  </div>
                )}
              </div>
            );
          })}
        </section>
      )}

      {selectedDatasetId != null && quality && analyses.length > 0 && (
        <div className="mt-6">
          <ReportPanel projectId={projectId} analyses={analyses} />
        </div>
      )}

      {selectedDatasetId != null && quality && (
        <div className="mt-6">
          <ChatPanel
            projectId={projectId}
            datasetId={selectedDatasetId}
            aiAvailable={aiAvailable}
            onAnalysesCreated={loadAnalyses}
          />
        </div>
      )}
    </div>
  );
}
