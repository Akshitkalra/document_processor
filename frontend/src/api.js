// Thin API client. Uses relative URLs; Vite proxies them to the backend in dev.
// In production set VITE_API_BASE to the backend origin.
const BASE = import.meta.env.VITE_API_BASE || "";

async function handle(res) {
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      if (typeof body.detail === "string") {
        detail = body.detail;
      } else if (Array.isArray(body.detail)) {
        // FastAPI validation errors come back as an array of objects.
        detail = body.detail.map((e) => e.msg || JSON.stringify(e)).join("; ");
      }
    } catch (_) {
      /* ignore */
    }
    throw new Error(detail);
  }
  return res.json();
}

export async function uploadDocument(file) {
  const form = new FormData();
  form.append("file", file);
  const res = await fetch(`${BASE}/api/documents`, {
    method: "POST",
    body: form,
  });
  return handle(res);
}

export async function listDocuments() {
  return handle(await fetch(`${BASE}/api/documents`));
}

export async function getDocument(id) {
  return handle(await fetch(`${BASE}/api/documents/${id}`));
}

export async function deleteDocument(id) {
  return handle(await fetch(`${BASE}/api/documents/${id}`, { method: "DELETE" }));
}

export async function summarize(id, { focus = null, maxWords = 600 } = {}) {
  const res = await fetch(`${BASE}/api/documents/${id}/summary`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ focus, max_words: maxWords }),
  });
  return handle(res);
}

export async function chat(id, question, history = []) {
  const res = await fetch(`${BASE}/api/documents/${id}/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question, history }),
  });
  return handle(res);
}
