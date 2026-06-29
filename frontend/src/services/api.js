import axios from "axios";

const API = axios.create({
    baseURL: "http://localhost:8000",
});

// Query
export const askQuestion = (question, sessionId) =>
    API.post("/query", { question, session_id: sessionId });

// Upload single file
export const uploadFile = (file, onProgress) => {
    const form = new FormData();
    form.append("file", file);
    return API.post("/upload", form, {
        headers: { "Content-Type": "multipart/form-data" },
        onUploadProgress: onProgress,
    });
};

// Upload multiple files
export const uploadMultipleFiles = (files, onProgress) => {
    const form = new FormData();
    files.forEach((f) => form.append("files", f));
    return API.post("/upload-multiple", form, {
        headers: { "Content-Type": "multipart/form-data" },
        onUploadProgress: onProgress,
    });
};

// Documents
export const getDocuments = () => API.get("/documents");
export const deleteDocument = (filename) => API.delete(`/documents/${encodeURIComponent(filename)}`);

// Chat
export const resetChat = (sessionId) =>
    API.post(`/reset-chat?session_id=${encodeURIComponent(sessionId)}`);

export default API;