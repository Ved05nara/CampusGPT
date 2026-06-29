import { useState, useRef, useCallback } from "react";

export default function QueryInput({ onSend, onClearChat, isLoading, hasMessages }) {
    const [text, setText] = useState("");
    const textareaRef = useRef(null);

    const autoResize = () => {
        const el = textareaRef.current;
        if (!el) return;
        el.style.height = "auto";
        el.style.height = Math.min(el.scrollHeight, 140) + "px";
    };

    const handleChange = (e) => {
        setText(e.target.value);
        autoResize();
    };

    const handleSend = useCallback(() => {
        const trimmed = text.trim();
        if (!trimmed || isLoading) return;
        onSend(trimmed);
        setText("");
        // reset textarea height
        if (textareaRef.current) {
            textareaRef.current.style.height = "auto";
        }
    }, [text, isLoading, onSend]);

    const handleKeyDown = (e) => {
        if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            handleSend();
        }
    };

    return (
        <div className="query-panel">
            <div className="query-bar">
                <textarea
                    ref={textareaRef}
                    className="query-textarea"
                    rows={1}
                    placeholder="Ask anything about your uploaded notes…"
                    value={text}
                    onChange={handleChange}
                    onKeyDown={handleKeyDown}
                    disabled={isLoading}
                />
                <button
                    id="send-btn"
                    className="query-send-btn"
                    onClick={handleSend}
                    disabled={!text.trim() || isLoading}
                    title="Send (Enter)"
                >
                    {isLoading ? "⏳" : "➤"}
                </button>
            </div>

            <div className="query-actions">
                <span className="query-hint">
                    Press <kbd style={{ fontSize: 10, background: "rgba(255,255,255,0.08)", padding: "1px 5px", borderRadius: 4, border: "1px solid rgba(255,255,255,0.12)" }}>Enter</kbd> to send &nbsp;·&nbsp;
                    <kbd style={{ fontSize: 10, background: "rgba(255,255,255,0.08)", padding: "1px 5px", borderRadius: 4, border: "1px solid rgba(255,255,255,0.12)" }}>Shift+Enter</kbd> for new line
                </span>
                {hasMessages && (
                    <button
                        className="btn btn-ghost"
                        style={{ fontSize: 12, padding: "4px 10px" }}
                        onClick={onClearChat}
                        disabled={isLoading}
                        id="clear-chat-btn"
                    >
                        🗑 Clear Chat
                    </button>
                )}
            </div>
        </div>
    );
}
