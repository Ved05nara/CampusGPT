import { useEffect, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";

// ── Badge components ───────────────────────────────────────────────────────────

function ConfidenceBadge({ score }) {
    const level = score >= 70 ? "high" : score >= 40 ? "mid" : "low";
    const icon  = score >= 70 ? "✦"   : score >= 40 ? "◈"   : "◇";
    const label = score >= 70 ? "High confidence" : score >= 40 ? "Moderate" : "Low confidence";
    return (
        <span className={`confidence-badge confidence-${level}`}>
            {icon} {label} · {score}%
        </span>
    );
}

function GeneralKnowledgeBadge() {
    return (
        <span className="general-knowledge-badge">
            ◉ General Knowledge · Not from your notes
        </span>
    );
}

function TypingCursor() {
    return <span className="typing-cursor" aria-hidden="true" />;
}

function ThinkingDots() {
    return (
        <div className="typing-indicator">
            <div className="typing-dots">
                <div className="typing-dot" />
                <div className="typing-dot" />
                <div className="typing-dot" />
            </div>
            <span style={{ fontSize: 12, color: "var(--text-muted)" }}>Thinking…</span>
        </div>
    );
}

// ── References panel (shown/hidden via toggle) ─────────────────────────────────
function ReferencesSection({ chunksData }) {
    const [expanded, setExpanded] = useState(null);

    if (!chunksData || chunksData.length === 0) return null;

    return (
        <div className="references-section">
            <div className="references-header">
                <span className="references-icon">📚</span>
                <span className="references-title">References</span>
                <span className="references-count">
                    {chunksData.length} source{chunksData.length !== 1 ? "s" : ""}
                </span>
            </div>

            <div className="references-list">
                {chunksData.map((chunk, i) => {
                    const isOpen  = expanded === i;
                    const score   = chunk.rerank_score;
                    const quality =
                        score >= 5 ? "ref-quality-high" :
                        score >= 0 ? "ref-quality-mid"  : "ref-quality-low";

                    return (
                        <div key={i} className={`reference-item ${isOpen ? "reference-item-open" : ""}`}>
                            <button
                                className="reference-header"
                                onClick={() => setExpanded(isOpen ? null : i)}
                                aria-expanded={isOpen}
                            >
                                <span className="reference-index">[{i + 1}]</span>
                                <span className="reference-meta">
                                    <span className="reference-filename">📄 {chunk.source}</span>
                                    {chunk.page_number > 0 && (
                                        <span className="reference-page">Page {chunk.page_number}</span>
                                    )}
                                </span>
                                {score !== undefined && (
                                    <span className={`reference-score ${quality}`}>
                                        Score: {score.toFixed(2)}
                                    </span>
                                )}
                                <span className="reference-chevron">{isOpen ? "▲" : "▼"}</span>
                            </button>

                            {isOpen && (
                                <div className="reference-body">
                                    <div className="reference-body-label">Retrieved excerpt:</div>
                                    <div className="reference-body-text">{chunk.text}</div>
                                </div>
                            )}
                        </div>
                    );
                })}
            </div>
        </div>
    );
}

// ── Action bar: Copy · Regenerate · References ─────────────────────────────────
function MessageActions({ content, msgIndex, onRegenerate, onToast, chunksData, hasNotes }) {
    const [copied, setCopied]       = useState(false);
    const [showRefs, setShowRefs]   = useState(false);

    const handleCopy = async () => {
        try {
            await navigator.clipboard.writeText(content);
            setCopied(true);
            onToast("Copied!", "success");
            setTimeout(() => setCopied(false), 2000);
        } catch {
            onToast("Copy failed — try selecting the text manually.", "error");
        }
    };

    return (
        <>
            <div className="message-actions">
                <button className="action-btn" onClick={handleCopy} title="Copy answer">
                    {copied ? "✓ Copied" : "⎘ Copy"}
                </button>
                <button
                    className="action-btn"
                    onClick={() => onRegenerate(msgIndex)}
                    title="Regenerate answer"
                >
                    ↻ Regenerate
                </button>
                {hasNotes && chunksData?.length > 0 && (
                    <button
                        className={`action-btn ${showRefs ? "action-btn-active" : ""}`}
                        onClick={() => setShowRefs((v) => !v)}
                        title={showRefs ? "Hide references" : "Show references"}
                    >
                        📚 {showRefs ? "Hide refs" : `References (${chunksData.length})`}
                    </button>
                )}
            </div>

            {showRefs && <ReferencesSection chunksData={chunksData} />}
        </>
    );
}

// ── Main ChatWindow ────────────────────────────────────────────────────────────
export default function ChatWindow({ messages, isLoading, onRegenerate, onToast }) {
    const bottomRef = useRef(null);

    useEffect(() => {
        bottomRef.current?.scrollIntoView({ behavior: "smooth" });
    }, [messages, isLoading]);

    if (messages.length === 0 && !isLoading) {
        return (
            <div className="chat-window">
                <div className="chat-empty">
                    <div className="chat-empty-icon">🎓</div>
                    <h2>Welcome to CampusGPT</h2>
                    <p>
                        Upload your lecture notes or textbooks in the sidebar,
                        then ask anything — answers are grounded strictly in your notes.
                    </p>
                </div>
            </div>
        );
    }

    return (
        <div className="chat-window">
            {messages.map((msg, idx) => (
                <div key={idx} className={`message message-${msg.role}`}>
                    <div className="message-bubble">
                        {msg.role === "user" ? (
                            <span style={{ whiteSpace: "pre-wrap" }}>{msg.content}</span>
                        ) : msg.isStreaming && !msg.content ? (
                            <ThinkingDots />
                        ) : (
                            <>
                                <ReactMarkdown>{msg.content}</ReactMarkdown>
                                {msg.isStreaming && <TypingCursor />}
                            </>
                        )}
                    </div>

                    {msg.role === "assistant" && !msg.isStreaming && (
                        <>
                            <div className="message-footer">
                                {msg.answer_source === "general" ? (
                                    <GeneralKnowledgeBadge />
                                ) : (
                                    typeof msg.confidence_score === "number" && (
                                        <ConfidenceBadge score={msg.confidence_score} />
                                    )
                                )}
                            </div>

                            <MessageActions
                                content={msg.content}
                                msgIndex={idx}
                                onRegenerate={onRegenerate}
                                onToast={onToast}
                                chunksData={msg.chunks_data}
                                hasNotes={msg.answer_source === "notes"}
                            />
                        </>
                    )}
                </div>
            ))}

            <div ref={bottomRef} />
        </div>
    );
}