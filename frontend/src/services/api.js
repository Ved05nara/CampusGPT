import axios from "axios";

const BASE = "http://localhost:8000";

const API = axios.create({ baseURL: BASE });

// ── Streaming query (SSE via native fetch) ─────────────────────────────────────
export const streamQuestion = (question, sessionId, onToken, onDone, onError) => {
    fetch(`${BASE}/query-stream`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question, session_id: sessionId }),
    })
        .then(async (response) => {
            if (!response.ok) throw new Error(`HTTP ${response.status}`);
            const reader = response.body.getReader();
            const decoder = new TextDecoder();
            let buffer = "";

            while (true) {
                const { value, done } = await reader.read();
                if (done) break;
                buffer += decoder.decode(value, { stream: true });
                const lines = buffer.split("\n");
                buffer = lines.pop() ?? "";

                for (const line of lines) {
                    if (!line.startsWith("data: ")) continue;
                    const jsonStr = line.slice(6).trim();
                    if (!jsonStr) continue;
                    try {
                        const data = JSON.parse(jsonStr);
                        if (data.error)  onError(data.error);
                        else if (data.done)  onDone(data);
                        else if (data.token) onToken(data.token);
                    } catch { /* malformed chunk, skip */ }
                }
            }
        })
        .catch((err) => onError(err.message || "Stream failed"));
};

// ── Non-streaming fallback ─────────────────────────────────────────────────────
export const askQuestion = (question, sessionId) =>
    API.post("/query", { question, session_id: sessionId });

// ── Upload ─────────────────────────────────────────────────────────────────────
export const uploadFile = (file, onProgress) => {
    const form = new FormData();
    form.append("file", file);
    return API.post("/upload", form, {
        headers: { "Content-Type": "multipart/form-data" },
        onUploadProgress: onProgress,
    });
};

export const uploadMultipleFiles = (files, onProgress) => {
    const form = new FormData();
    files.forEach((f) => form.append("files", f));
    return API.post("/upload-multiple", form, {
        headers: { "Content-Type": "multipart/form-data" },
        onUploadProgress: onProgress,
    });
};

// ── Documents ──────────────────────────────────────────────────────────────────
export const getDocuments = () => API.get("/documents");
export const deleteDocument = (filename) =>
    API.delete(`/documents/${encodeURIComponent(filename)}`);

// ── Chat ───────────────────────────────────────────────────────────────────────
export const resetChat = (sessionId) =>
    API.post(`/reset-chat?session_id=${encodeURIComponent(sessionId)}`);

export default API;