import { useState, useEffect, useCallback, useRef } from "react";
import { askQuestion, getDocuments, resetChat } from "./services/api";
import Sidebar from "./components/Sidebar";
import ChatWindow from "./components/ChatWindow";
import QueryInput from "./components/QueryInput";

// ── Tiny toast system ──────────────────────────────────────────────────────────
function useToasts() {
    const [toasts, setToasts] = useState([]);
    const add = useCallback((message, type = "info") => {
        const id = Date.now();
        setToasts((prev) => [...prev, { id, message, type }]);
        setTimeout(() => setToasts((prev) => prev.filter((t) => t.id !== id)), 3500);
    }, []);
    return { toasts, add };
}

// ── Stable session ID for this browser tab ───────────────────────────────────
function getSessionId() {
    let id = sessionStorage.getItem("study_session_id");
    if (!id) {
        id = `session_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`;
        sessionStorage.setItem("study_session_id", id);
    }
    return id;
}

const SESSION_ID = getSessionId();

// ─────────────────────────────────────────────────────────────────────────────

export default function App() {
    const [messages, setMessages] = useState([]);
    const [documents, setDocuments] = useState([]);
    const [isLoading, setIsLoading] = useState(false);
    const { toasts, add: addToast } = useToasts();

    // ── Fetch document list ──────────────────────────────────────────────────
    const fetchDocuments = useCallback(async () => {
        try {
            const res = await getDocuments();
            setDocuments(res.data.documents ?? []);
        } catch {
            // silently ignore on initial load failure
        }
    }, []);

    useEffect(() => {
        fetchDocuments();
    }, [fetchDocuments]);

    // ── Send a question ──────────────────────────────────────────────────────
    const handleSend = useCallback(async (question) => {
        setMessages((prev) => [...prev, { role: "user", content: question }]);
        setIsLoading(true);
        try {
            const res = await askQuestion(question, SESSION_ID);
            const { answer, sources, confidence_score } = res.data;
            setMessages((prev) => [
                ...prev,
                { role: "assistant", content: answer, sources, confidence_score },
            ]);
        } catch (err) {
            const detail = err?.response?.data?.detail ?? "Failed to get a response.";
            setMessages((prev) => [
                ...prev,
                { role: "assistant", content: `⚠️ ${detail}`, sources: [], confidence_score: 0 },
            ]);
            addToast(detail, "error");
        } finally {
            setIsLoading(false);
        }
    }, [addToast]);

    // ── Clear chat ───────────────────────────────────────────────────────────
    const handleClearChat = useCallback(async () => {
        try {
            await resetChat(SESSION_ID);
        } catch {
            // backend memory cleared best-effort
        }
        setMessages([]);
        addToast("Chat cleared.", "info");
    }, [addToast]);

    // ── Stats for topbar ─────────────────────────────────────────────────────
    const totalChunks = documents.reduce((s, d) => s + (d.chunk_count ?? 0), 0);

    return (
        <div className="app-layout">
            {/* Left sidebar: documents + upload */}
            <Sidebar
                documents={documents}
                onDocumentsChange={fetchDocuments}
                onToast={addToast}
            />

            {/* Right: header + chat + input */}
            <div className="main-panel">
                {/* Top bar */}
                <header className="topbar">
                    <div>
                        <div className="topbar-title">CampusGPT</div>
                        <div className="topbar-subtitle">
                            {documents.length > 0
                                ? `${documents.length} document${documents.length > 1 ? "s" : ""} · ${totalChunks} chunks indexed`
                                : "Upload PDF files to get started"}
                        </div>
                    </div>
                    <div className="topbar-actions">
                        <span className="stats-chip">
                            <span className="stats-dot" />
                            AI Online
                        </span>
                    </div>
                </header>

                {/* Chat messages */}
                <ChatWindow messages={messages} isLoading={isLoading} />

                {/* Input bar */}
                <QueryInput
                    onSend={handleSend}
                    onClearChat={handleClearChat}
                    isLoading={isLoading}
                    hasMessages={messages.length > 0}
                />
            </div>

            {/* Toast notifications */}
            <div className="toast-container">
                {toasts.map((t) => (
                    <div key={t.id} className={`toast toast-${t.type}`}>
                        {t.message}
                    </div>
                ))}
            </div>
        </div>
    );
}