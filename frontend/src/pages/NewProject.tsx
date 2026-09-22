import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { extractErrorMessage, projectsApi } from "../api/client";
import { DynamicListInput } from "../components/DynamicListInput";

export default function NewProject() {
  const navigate = useNavigate();
  const [title, setTitle] = useState("");
  const [aim, setAim] = useState("");
  const [objectives, setObjectives] = useState<string[]>([""]);
  const [questions, setQuestions] = useState<string[]>([""]);
  const [hypotheses, setHypotheses] = useState<string[]>([""]);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const isValid = title.trim().length > 0 && aim.trim().length > 0;

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!isValid || submitting) return;
    setSubmitting(true);
    setError(null);
    try {
      const project = await projectsApi.create({
        title: title.trim(),
        research_aim: aim.trim(),
        objectives: objectives.filter((o) => o.trim()),
        research_questions: questions.filter((q) => q.trim()),
        hypotheses: hypotheses.filter((h) => h.trim()),
      });
      navigate(`/projects/${project.id}`);
    } catch (err) {
      setError(extractErrorMessage(err));
      setSubmitting(false);
    }
  }

  return (
    <div className="mx-auto max-w-2xl px-6 py-10">
      <h1 className="text-2xl font-semibold text-slate-900">New Research Project</h1>
      <p className="mt-1 text-sm text-slate-500">
        Your research aim and objectives give the AI the context it needs to recommend
        statistically appropriate analyses later — this isn't just a project name.
      </p>

      <form onSubmit={handleSubmit} className="mt-8 space-y-6">
        <div>
          <label className="block text-sm font-medium text-slate-700">Project title</label>
          <input
            type="text"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="e.g. Effect of physical activity on blood pressure among university students"
            className="mt-2 w-full rounded-md border border-slate-300 px-3 py-2 text-sm focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-slate-700">Research aim</label>
          <textarea
            value={aim}
            onChange={(e) => setAim(e.target.value)}
            rows={3}
            placeholder="e.g. To investigate the relationship between physical activity and blood pressure."
            className="mt-2 w-full rounded-md border border-slate-300 px-3 py-2 text-sm focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
          />
        </div>

        <DynamicListInput
          label="Specific objectives"
          placeholder="e.g. Compare blood pressure between physically active and inactive participants."
          values={objectives}
          onChange={setObjectives}
        />

        <DynamicListInput
          label="Research questions"
          placeholder="e.g. Is physical activity associated with blood pressure?"
          values={questions}
          onChange={setQuestions}
        />

        <DynamicListInput
          label="Hypotheses (optional)"
          placeholder="e.g. Physically active participants have lower systolic blood pressure."
          values={hypotheses}
          onChange={setHypotheses}
          helperText="Leave blank if this is an exploratory study without formal hypotheses."
        />

        {error && (
          <div className="rounded-md border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
            {error}
          </div>
        )}

        <div className="flex items-center gap-3 pt-2">
          <button
            type="submit"
            disabled={!isValid || submitting}
            className="rounded-md bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 disabled:cursor-not-allowed disabled:bg-slate-300"
          >
            {submitting ? "Creating..." : "Create Project"}
          </button>
        </div>
      </form>
    </div>
  );
}
