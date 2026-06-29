import { useState, useEffect, useCallback } from "react";
import { streamQuestion, getDocuments, resetChat } from "./services/api";
import Sidebar from "./components/Sidebar";
import ChatWindow from "./components/ChatWindow";
import QueryInput from "./components/QueryInput";

// ── Toast system ───────────────────────────────────────────────────────────────
function useToasts() {
    const [toasts, setToasts] = useState([]);
    const add = useCallback((message, type = "info") => {
        const id = Date.now() + Math.random();
        setToasts((prev) => [...prev, { id, message, type }]);
        setTimeout(() => setToasts((prev) => prev.filter((t) => t.id !== id)), 3500);
    }, []);
    return { toasts, add };
}

// ── Theme ──────────────────────────────────────────────────────────────────────
function useTheme() {
    const [theme, setTheme] = useState(
        () => localStorage.getItem("campusgpt-theme") || "dark"
    );
    useEffect(() => {
        document.documentElement.setAttribute("data-theme", theme);
        localStorage.setItem("campusgpt-theme", theme);
    }, [theme]);
    const toggle = useCallback(
        () => setTheme((t) => (t === "dark" ? "light" : "dark")),
        []
    );
    return { theme, toggle };
}

// ── Stable session ID per browser tab ─────────────────────────────────────────
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
    const [messages, setMessages]   = useState([]);
    const [documents, setDocuments] = useState([]);
    const [isLoading, setIsLoading] = useState(false);
    const { toasts, add: addToast } = useToasts();
    const { theme, toggle: toggleTheme } = useTheme();

    // ── Fetch documents ────────────────────────────────────────────────────────
    const fetchDocuments = useCallback(async () => {
        try {
            const res = await getDocuments();
            setDocuments(res.data.documents ?? []);
        } catch { /* silent */ }
    }, []);

    useEffect(() => { fetchDocuments(); }, [fetchDocuments]);

    // ── Core streaming logic ───────────────────────────────────────────────────
    const streamAndAppend = useCallback((question) => {
        setIsLoading(true);

        // Push a streaming placeholder as the last message
        setMessages((prev) => [
            ...prev,
            {
                role: "assistant",
                content: "",
                sources: [],
                chunks_data: [],
                confidence_score: null,
                answer_source: null,
                isStreaming: true,
            },
        ]);

        streamQuestion(
            question,
            SESSION_ID,
            // onToken — append each token to the last message
            (token) => {
                setMessages((prev) => {
                    const updated = [...prev];
                    const last = updated[updated.length - 1];
                    if (last?.role === "assistant") {
                        updated[updated.length - 1] = {
                            ...last,
                            content: last.content + token,
                        };
                    }
                    return updated;
                });
            },
            // onDone — attach metadata to the last message
            ({ confidence_score, sources, answer_source, chunks_data }) => {
                setMessages((prev) => {
                    const updated = [...prev];
                    const last = updated[updated.length - 1];
                    if (last?.role === "assistant") {
                        updated[updated.length - 1] = {
                            ...last,
                            confidence_score,
                            sources: sources ?? [],
                            answer_source,
                            chunks_data: chunks_data ?? [],
                            isStreaming: false,
                        };
                    }
                    return updated;
                });
                setIsLoading(false);
            },
            // onError
            (error) => {
                setMessages((prev) => {
                    const updated = [...prev];
                    const last = updated[updated.length - 1];
                    if (last?.role === "assistant") {
                        updated[updated.length - 1] = {
                            ...last,
                            content: `⚠️ ${error}`,
                            isStreaming: false,
                        };
                    }
                    return updated;
                });
                setIsLoading(false);
                addToast(error, "error");
            }
        );
    }, [addToast]);

    // ── Send ───────────────────────────────────────────────────────────────────
    const handleSend = useCallback((question) => {
        setMessages((prev) => [...prev, { role: "user", content: question }]);
        streamAndAppend(question);
    }, [streamAndAppend]);

    // ── Regenerate ─────────────────────────────────────────────────────────────
    const handleRegenerate = useCallback((msgIndex) => {
        if (isLoading) return;
        // Find the nearest user message before this assistant message
        const userMsg = messages
            .slice(0, msgIndex)
            .reverse()
            .find((m) => m.role === "user");
        if (!userMsg) return;
        // Remove the assistant message being regenerated
        setMessages((prev) => prev.slice(0, msgIndex));
        streamAndAppend(userMsg.content);
    }, [messages, isLoading, streamAndAppend]);

    // ── Clear chat ─────────────────────────────────────────────────────────────
    const handleClearChat = useCallback(async () => {
        try { await resetChat(SESSION_ID); } catch { /* best-effort */ }
        setMessages([]);
        addToast("Chat cleared.", "info");
    }, [addToast]);

    const totalChunks = documents.reduce((s, d) => s + (d.chunk_count ?? 0), 0);

    return (
        <div className="app-layout">
            <Sidebar
                documents={documents}
                onDocumentsChange={fetchDocuments}
                onToast={addToast}
            />

            <div className="main-panel">
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
                        <button
                            className="theme-toggle"
                            onClick={toggleTheme}
                            title={`Switch to ${theme === "dark" ? "light" : "dark"} mode`}
                            aria-label="Toggle dark/light mode"
                        >
                            {theme === "dark" ? "☀️" : "🌙"}
                        </button>
                        <span className="stats-chip">
                            <span className="stats-dot" />
                            AI Online
                        </span>
                    </div>
                </header>

                <ChatWindow
                    messages={messages}
                    isLoading={isLoading}
                    onRegenerate={handleRegenerate}
                    onToast={addToast}
                />

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