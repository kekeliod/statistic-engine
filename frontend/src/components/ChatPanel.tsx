import { useEffect, useRef, useState } from "react";
import { chatApi, extractErrorMessage } from "../api/client";
import type { ChatMessage } from "../types";

interface Props {
  projectId: number;
  datasetId: number | null;
  aiAvailable: boolean;
  onAnalysesCreated: () => void;
}

export function ChatPanel({ projectId, datasetId, aiAvailable, onAnalysesCreated }: Props) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [open, setOpen] = useState(false);
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    chatApi.history(projectId).then(setMessages).catch(() => setMessages([]));
  }, [projectId]);

  useEffect(() => {
    if (open) endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, open]);

  async function send() {
    if (!input.trim() || datasetId == null || sending) return;
    const text = input.trim();
    setInput("");
    setSending(true);
    setError(null);
    try {
      const turn = await chatApi.send(projectId, datasetId, text);
      setMessages((prev) => [...prev, turn.user, turn.assistant]);
      if (turn.analysis_ids.length > 0) onAnalysesCreated();
    } catch (err) {
      setError(extractErrorMessage(err));
    } finally {
      setSending(false);
    }
  }

  return (
    <section className="rounded-lg border border-slate-200 bg-white p-5">
      <button
        onClick={() => setOpen((o) => !o)}
        className="flex w-full items-center justify-between text-left"
      >
        <h2 className="font-medium text-slate-900">Ask a question</h2>
        <span className="text-xs text-slate-400">{open ? "Hide" : "Show"}</span>
      </button>

      {open && (
        <div className="mt-3">
          {!aiAvailable && (
            <p className="mb-3 rounded-md border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-800">
              No Anthropic API key is configured, so free-form questions are limited. Simple
              phrasings still work, e.g. <em>"compare systolic_bp between activity_level"</em> or{" "}
              <em>"correlation between bmi and systolic_bp"</em>.
            </p>
          )}

          <div className="max-h-80 space-y-2 overflow-y-auto rounded-md bg-slate-50 p-3">
            {messages.length === 0 && (
              <p className="text-xs text-slate-400">No messages yet.</p>
            )}
            {messages.map((m) => (
              <div
                key={m.id}
                className={`rounded-md px-3 py-2 text-sm ${
                  m.role === "user"
                    ? "ml-8 bg-indigo-600 text-white"
                    : "mr-8 bg-white text-slate-700 shadow-sm"
                }`}
              >
                {m.content}
                {m.meta?.analysis_ids && m.meta.analysis_ids.length > 0 && (
                  <p className="mt-1 text-[11px] opacity-70">
                    Ran {m.meta.analysis_ids.length} analysis
                    {m.meta.analysis_ids.length === 1 ? "" : "es"} — see below.
                  </p>
                )}
              </div>
            ))}
            <div ref={endRef} />
          </div>

          {error && <p className="mt-2 text-xs text-red-600">{error}</p>}

          <div className="mt-2 flex gap-2">
            <input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && send()}
              placeholder={datasetId == null ? "Upload a dataset first" : "Ask about your data…"}
              disabled={datasetId == null || sending}
              className="flex-1 rounded-md border border-slate-300 px-3 py-1.5 text-sm"
            />
            <button
              onClick={send}
              disabled={datasetId == null || sending || !input.trim()}
              className="rounded-md bg-indigo-600 px-4 py-1.5 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-50"
            >
              {sending ? "…" : "Send"}
            </button>
          </div>
        </div>
      )}
    </section>
  );
}
