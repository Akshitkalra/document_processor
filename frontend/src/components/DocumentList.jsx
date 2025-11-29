import React from "react";

const STATUS_LABEL = {
  pending: "Queued",
  extracting: "Extracting + OCR",
  embedding: "Embedding",
  ready: "Ready",
  failed: "Failed",
};

function bytes(n) {
  if (n < 1024) return `${n} B`;
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(0)} KB`;
  return `${(n / 1024 / 1024).toFixed(1)} MB`;
}

export default function DocumentList({ documents, selectedId, onSelect, onDelete }) {
  if (documents.length === 0) {
    return <p className="muted">No documents yet. Upload one to get started.</p>;
  }
  return (
    <ul className="doc-list">
      {documents.map((d) => (
        <li
          key={d.id}
          className={`doc-item ${d.id === selectedId ? "selected" : ""}`}
          onClick={() => onSelect(d)}
        >
          <div className="doc-row">
            <span className="doc-name" title={d.filename}>
              {d.filename}
            </span>
            <button
              className="link-btn danger"
              onClick={(e) => {
                e.stopPropagation();
                onDelete(d.id);
              }}
            >
              ✕
            </button>
          </div>
          <div className="doc-meta">
            <span className={`badge ${d.status}`}>
              {STATUS_LABEL[d.status] || d.status}
            </span>
            <span>{bytes(d.size_bytes)}</span>
            {d.page_count > 0 && <span>{d.page_count} pages</span>}
            {d.ocr_pages > 0 && <span>{d.ocr_pages} OCR</span>}
          </div>
          {d.status !== "ready" && d.status !== "failed" && (
            <div className="progress">
              <div
                className="progress-bar"
                style={{ width: `${Math.round((d.progress || 0) * 100)}%` }}
              />
            </div>
          )}
          {d.status === "failed" && <div className="error">{d.error}</div>}
        </li>
      ))}
    </ul>
  );
}
