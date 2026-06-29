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

// ── Typing cursor (blinks inside streaming bubble) ─────────────────────────────
function TypingCursor() {
    return <span className="typing-cursor" aria-hidden="true" />;
}

// ── Dots shown before first token arrives ─────────────────────────────────────
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

// ── Source pill that expands to show the retrieved chunk ───────────────────────
function SourcePill({ src, chunksData, isExpanded, onToggle }) {
    const chunk = chunksData?.find((c) => c.source === src);
    return (
        <div className="source-pill-wrapper">
            <button
                className={`source-pill${isExpanded ? " source-pill-active" : ""}`}
                onClick={onToggle}
                title={isExpanded ? "Collapse chunk" : "Click to view retrieved text"}
            >
                📄 {src} <span style={{ fontSize: 9, opacity: 0.7 }}>{isExpanded ? "▲" : "▼"}</span>
            </button>
            {isExpanded && chunk && (
                <div className="chunk-panel">
                    <div className="chunk-panel-header">📌 Retrieved from: {chunk.source}</div>
                    <div className="chunk-panel-text">{chunk.text}</div>
                </div>
            )}
        </div>
    );
}

// ── Copy + Regenerate action bar ───────────────────────────────────────────────
function MessageActions({ content, msgIndex, onRegenerate, onToast }) {
    const [copied, setCopied] = useState(false);

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
        </div>
    );
}

// ── Main ChatWindow ────────────────────────────────────────────────────────────
export default function ChatWindow({ messages, isLoading, onRegenerate, onToast }) {
    const bottomRef = useRef(null);
    // Track which source pills are expanded: key = `${msgIdx}-${src}`
    const [expanded, setExpanded] = useState({});

    useEffect(() => {
        bottomRef.current?.scrollIntoView({ behavior: "smooth" });
    }, [messages, isLoading]);

    const toggleChunk = (msgIdx, src) => {
        const key = `${msgIdx}-${src}`;
        setExpanded((prev) => ({ ...prev, [key]: !prev[key] }));
    };

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
                            // Waiting for first token
                            <ThinkingDots />
                        ) : (
                            <>
                                <ReactMarkdown>{msg.content}</ReactMarkdown>
                                {msg.isStreaming && <TypingCursor />}
                            </>
                        )}
                    </div>

                    {/* Footer + actions — only when done streaming */}
                    {msg.role === "assistant" && !msg.isStreaming && (
                        <>
                            <div className="message-footer">
                                {msg.answer_source === "general" ? (
                                    <GeneralKnowledgeBadge />
                                ) : (
                                    <>
                                        {typeof msg.confidence_score === "number" && (
                                            <ConfidenceBadge score={msg.confidence_score} />
                                        )}
                                        {msg.sources?.map((src, i) => (
                                            <SourcePill
                                                key={i}
                                                src={src}
                                                chunksData={msg.chunks_data}
                                                isExpanded={!!expanded[`${idx}-${src}`]}
                                                onToggle={() => toggleChunk(idx, src)}
                                            />
                                        ))}
                                    </>
                                )}
                            </div>

                            <MessageActions
                                content={msg.content}
                                msgIndex={idx}
                                onRegenerate={onRegenerate}
                                onToast={onToast}
                            />
                        </>
                    )}
                </div>
            ))}

            <div ref={bottomRef} />
        </div>
    );
}
