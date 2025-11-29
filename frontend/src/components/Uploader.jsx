import React, { useRef, useState } from "react";
import { uploadDocument } from "../api.js";

export default function Uploader({ onUploaded }) {
  const inputRef = useRef(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);
  const [dragging, setDragging] = useState(false);

  async function send(file) {
    if (!file) return;
    setBusy(true);
    setError(null);
    try {
      const { document } = await uploadDocument(file);
      onUploaded(document);
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div
      className={`uploader ${dragging ? "dragging" : ""}`}
      onDragOver={(e) => {
        e.preventDefault();
        setDragging(true);
      }}
      onDragLeave={() => setDragging(false)}
      onDrop={(e) => {
        e.preventDefault();
        setDragging(false);
        send(e.dataTransfer.files[0]);
      }}
      onClick={() => inputRef.current?.click()}
    >
      <input
        ref={inputRef}
        type="file"
        accept=".pdf,.docx,.doc,.png,.jpg,.jpeg,.tiff,.bmp,.webp"
        hidden
        onChange={(e) => send(e.target.files[0])}
      />
      <div className="uploader-inner">
        <strong>{busy ? "Uploading…" : "Drop a document here or click to browse"}</strong>
        <span className="hint">PDF (up to ~400 pages), Word, or scanned images</span>
        {error && <span className="error">{error}</span>}
      </div>
    </div>
  );
}
