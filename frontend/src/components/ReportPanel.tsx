import { useEffect, useState } from "react";
import { extractErrorMessage, reportsApi } from "../api/client";
import type { Analysis, Report } from "../types";

interface Props {
  projectId: number;
  analyses: Analysis[];
}

export function ReportPanel({ projectId, analyses }: Props) {
  const [reports, setReports] = useState<Report[]>([]);
  const [selected, setSelected] = useState<Set<number>>(new Set());
  const [format, setFormat] = useState<"html" | "docx">("html");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [previewHtml, setPreviewHtml] = useState<string | null>(null);

  const complete = analyses.filter((a) => a.status === "complete");

  useEffect(() => {
    reportsApi.list(projectId).then(setReports).catch(() => setReports([]));
  }, [projectId]);

  function toggle(id: number) {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  async function generate() {
    setBusy(true);
    setError(null);
    try {
      const report = await reportsApi.create(projectId, format, [...selected]);
      setReports((prev) => [report, ...prev]);
      if (report.format === "html") setPreviewHtml(await reportsApi.fetchHtml(report.id));
    } catch (err) {
      setError(extractErrorMessage(err));
    } finally {
      setBusy(false);
    }
  }

  async function preview(report: Report) {
    if (report.format !== "html") return;
    setPreviewHtml(await reportsApi.fetchHtml(report.id));
  }

  if (complete.length === 0) {
    return (
      <section className="rounded-lg border border-slate-200 bg-white p-5">
        <h2 className="font-medium text-slate-900">Report</h2>
        <p className="mt-2 text-sm text-slate-500">Run at least one analysis to generate a report.</p>
      </section>
    );
  }

  return (
    <section className="rounded-lg border border-slate-200 bg-white p-5">
      <h2 className="font-medium text-slate-900">Report</h2>
      <p className="mt-1 text-xs text-slate-500">
        Assembles project info, data-quality assessment, methods, results (with charts),
        interpretations, limitations and recommendations. PDF export is planned.
      </p>

      <div className="mt-3">
        <p className="text-xs font-medium text-slate-500">
          Include analyses ({selected.size === 0 ? "all" : selected.size} selected)
        </p>
        <div className="mt-1 flex flex-wrap gap-1.5">
          {complete.map((a) => (
            <button
              key={a.id}
              onClick={() => toggle(a.id)}
              className={`rounded-full border px-2.5 py-1 text-xs ${
                selected.has(a.id)
                  ? "border-indigo-300 bg-indigo-50 text-indigo-700"
                  : "border-slate-300 text-slate-600 hover:bg-slate-50"
              }`}
            >
              {a.result?.method_label ?? a.method}
            </button>
          ))}
        </div>
      </div>

      <div className="mt-3 flex items-center gap-3">
        <select
          value={format}
          onChange={(e) => setFormat(e.target.value as "html" | "docx")}
          className="rounded-md border border-slate-300 px-2 py-1.5 text-sm"
        >
          <option value="html">HTML</option>
          <option value="docx">Word (.docx)</option>
        </select>
        <button
          onClick={generate}
          disabled={busy}
          className="rounded-md bg-indigo-600 px-4 py-1.5 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-50"
        >
          {busy ? "Generating…" : "Generate report"}
        </button>
      </div>
      {error && <p className="mt-2 text-xs text-red-600">{error}</p>}

      {reports.length > 0 && (
        <ul className="mt-4 divide-y divide-slate-100 text-sm">
          {reports.map((r) => (
            <li key={r.id} className="flex items-center justify-between py-2">
              <span className="text-slate-700">
                {r.title}{" "}
                <span className="text-xs text-slate-400">
                  · {r.format.toUpperCase()} · {new Date(r.created_at).toLocaleString()}
                </span>
              </span>
              <span className="flex gap-3 text-xs">
                {r.format === "html" && (
                  <button onClick={() => preview(r)} className="text-indigo-600 hover:underline">
                    Preview
                  </button>
                )}
                <a
                  href={reportsApi.downloadUrl(r.id)}
                  target="_blank"
                  rel="noreferrer"
                  className="text-indigo-600 hover:underline"
                >
                  Download
                </a>
              </span>
            </li>
          ))}
        </ul>
      )}

      {previewHtml && (
        <div className="mt-4">
          <div className="flex items-center justify-between">
            <p className="text-xs font-medium text-slate-500">Preview</p>
            <button onClick={() => setPreviewHtml(null)} className="text-xs text-slate-400 hover:text-slate-600">
              Close
            </button>
          </div>
          <iframe
            title="Report preview"
            srcDoc={previewHtml}
            className="mt-1 h-[32rem] w-full rounded-md border border-slate-200 bg-white"
          />
        </div>
      )}
    </section>
  );
}
