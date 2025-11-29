import React, { useState } from "react";
import ReactMarkdown from "react-markdown";
import { summarize } from "../api.js";

export default function SummaryPanel({ document }) {
  const [summary, setSummary] = useState(null);
  const [focus, setFocus] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);

  async function run() {
    setBusy(true);
    setError(null);
    try {
      const res = await summarize(document.id, {
        focus: focus.trim() || null,
      });
      setSummary(res);
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="panel">
      <div className="summary-controls">
        <input
          type="text"
          placeholder="Optional focus, e.g. 'financial risks' or 'key dates'"
          value={focus}
          onChange={(e) => setFocus(e.target.value)}
        />
        <button onClick={run} disabled={busy}>
          {busy ? "Summarising…" : "Generate summary"}
        </button>
      </div>
      {error && <div className="error">{error}</div>}
      {summary && (
        <div className="summary-body">
          {summary.cached && <span className="muted small">cached result</span>}
          <ReactMarkdown>{summary.summary}</ReactMarkdown>

          {summary.section_summaries?.length > 1 && (
            <details className="sections">
              <summary>
                Section breakdown ({summary.section_summaries.length})
              </summary>
              {summary.section_summaries.map((s, i) => (
                <div key={i} className="section">
                  <h4>Section {i + 1}</h4>
                  <ReactMarkdown>{s}</ReactMarkdown>
                </div>
              ))}
            </details>
          )}
        </div>
      )}
    </div>
  );
}
