import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { extractErrorMessage, projectsApi } from "../api/client";
import type { ProjectSummary } from "../types";

export default function Dashboard() {
  const [projects, setProjects] = useState<ProjectSummary[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    projectsApi
      .list()
      .then(setProjects)
      .catch((err) => setError(extractErrorMessage(err)));
  }, []);

  return (
    <div className="mx-auto max-w-5xl px-6 py-10">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-slate-900">Research Projects</h1>
          <p className="mt-1 text-sm text-slate-500">
            Your research workspaces — objectives, datasets, and analyses in one place.
          </p>
        </div>
        <Link
          to="/projects/new"
          className="rounded-md bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700"
        >
          + New Project
        </Link>
      </div>

      {error && (
        <div className="mt-6 rounded-md border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          {error}
        </div>
      )}

      {!projects && !error && <p className="mt-8 text-sm text-slate-500">Loading projects...</p>}

      {projects && projects.length === 0 && (
        <div className="mt-10 rounded-lg border border-dashed border-slate-300 bg-white p-10 text-center">
          <p className="text-slate-600">No research projects yet.</p>
          <Link
            to="/projects/new"
            className="mt-3 inline-block text-sm font-medium text-indigo-600 hover:text-indigo-800"
          >
            Create your first project &rarr;
          </Link>
        </div>
      )}

      {projects && projects.length > 0 && (
        <ul className="mt-8 grid gap-4 sm:grid-cols-2">
          {projects.map((p) => (
            <li key={p.id}>
              <Link
                to={`/projects/${p.id}`}
                className="block rounded-lg border border-slate-200 bg-white p-5 shadow-sm transition hover:border-indigo-300 hover:shadow-md"
              >
                <h2 className="font-medium text-slate-900">{p.title}</h2>
                <p className="mt-1 line-clamp-2 text-sm text-slate-500">{p.research_aim}</p>
                <div className="mt-3 flex items-center justify-between text-xs text-slate-400">
                  <span>
                    {p.dataset_count} dataset{p.dataset_count === 1 ? "" : "s"}
                  </span>
                  <span>Updated {new Date(p.updated_at).toLocaleDateString()}</span>
                </div>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
