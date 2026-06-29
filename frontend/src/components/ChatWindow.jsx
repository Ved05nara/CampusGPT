import { useEffect, useRef } from "react";
import ReactMarkdown from "react-markdown";

function ConfidenceBadge({ score }) {
    const level = score >= 70 ? "high" : score >= 40 ? "mid" : "low";
    const icon  = score >= 70 ? "✦"  : score >= 40 ? "◈"  : "◇";
    const label = score >= 70 ? "High confidence" : score >= 40 ? "Moderate" : "Low confidence";
    return (
        <span className={`confidence-badge confidence-${level}`}>
            {icon} {label} · {score}%
        </span>
    );
}

function TypingIndicator() {
    return (
        <div className="message message-assistant">
            <div className="message-bubble" style={{ padding: "14px 16px" }}>
                <div className="typing-indicator">
                    <div className="typing-dots">
                        <div className="typing-dot" />
                        <div className="typing-dot" />
                        <div className="typing-dot" />
                    </div>
                    <span style={{ fontSize: 12, color: "var(--text-muted)" }}>Thinking…</span>
                </div>
            </div>
        </div>
    );
}

export default function ChatWindow({ messages, isLoading }) {
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
                <p>Upload your lecture notes or textbooks in the sidebar, then ask anything — answers are grounded strictly in your notes.</p>
            </div>
        </div>
        );
    }

    return (
        <div className="chat-window">
            {messages.map((msg, idx) => (
                <div
                    key={idx}
                    className={`message message-${msg.role}`}
                >
                    <div className="message-bubble">
                        {msg.role === "user" ? (
                            <span style={{ whiteSpace: "pre-wrap" }}>{msg.content}</span>
                        ) : (
                            <ReactMarkdown>{msg.content}</ReactMarkdown>
                        )}
                    </div>

                    {/* Footer: confidence + sources (assistant only) */}
                    {msg.role === "assistant" && (
                        <div className="message-footer">
                            {typeof msg.confidence_score === "number" && (
                                <ConfidenceBadge score={msg.confidence_score} />
                            )}
                            {msg.sources?.map((src, i) => (
                                <span key={i} className="source-pill" title={src}>
                                    📄 {src}
                                </span>
                            ))}
                        </div>
                    )}
                </div>
            ))}

            {isLoading && <TypingIndicator />}
            <div ref={bottomRef} />
        </div>
    );
}
