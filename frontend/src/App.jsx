import React, { useEffect, useState, useCallback } from "react";
import Uploader from "./components/Uploader.jsx";
import DocumentList from "./components/DocumentList.jsx";
import SummaryPanel from "./components/SummaryPanel.jsx";
import ChatPanel from "./components/ChatPanel.jsx";
import { listDocuments, deleteDocument } from "./api.js";

export default function App() {
  const [documents, setDocuments] = useState([]);
  const [selectedId, setSelectedId] = useState(null);
  const [tab, setTab] = useState("summary"); // "summary" | "chat"

  const refresh = useCallback(async () => {
    try {
      setDocuments(await listDocuments());
    } catch (_) {
      /* backend may be starting up */
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  // Poll while any document is still being processed.
  useEffect(() => {
    const anyProcessing = documents.some(
      (d) => d.status !== "ready" && d.status !== "failed"
    );
    if (!anyProcessing) return;
    const id = setInterval(refresh, 2000);
    return () => clearInterval(id);
  }, [documents, refresh]);

  const selected = documents.find((d) => d.id === selectedId) || null;

  async function handleDelete(id) {
    await deleteDocument(id);
    if (selectedId === id) setSelectedId(null);
    refresh();
  }

  return (
    <div className="app">
      <aside className="sidebar">
        <h1>📄 Document Processor</h1>
        <Uploader
          onUploaded={(doc) => {
            setSelectedId(doc.id);
            refresh();
          }}
        />
        <h3>Documents</h3>
        <DocumentList
          documents={documents}
          selectedId={selectedId}
          onSelect={(d) => setSelectedId(d.id)}
          onDelete={handleDelete}
        />
      </aside>

      <main className="main">
        {!selected && (
          <div className="empty-state">
            <p>Select or upload a document to summarise or chat with it.</p>
          </div>
        )}

        {selected && (
          <>
            <header className="doc-header">
              <h2>{selected.filename}</h2>
              <div className="tabs">
                <button
                  className={tab === "summary" ? "active" : ""}
                  onClick={() => setTab("summary")}
                >
                  Summary
                </button>
                <button
                  className={tab === "chat" ? "active" : ""}
                  onClick={() => setTab("chat")}
                >
                  Chat
                </button>
              </div>
            </header>

            {selected.status !== "ready" ? (
              <div className="empty-state">
                <p>
                  This document is <strong>{selected.status}</strong>. It will be
                  ready to summarise and chat with once processing finishes.
                </p>
              </div>
            ) : tab === "summary" ? (
              <SummaryPanel document={selected} />
            ) : (
              <ChatPanel document={selected} />
            )}
          </>
        )}
      </main>
    </div>
  );
}
