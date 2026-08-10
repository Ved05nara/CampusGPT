import { useState, useRef, useCallback } from "react";

export default function QueryInput({ onSend, onClearChat, isLoading, hasMessages, topK, onTopKChange }) {
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

                <div className="query-controls">
                    {/* Top-K slider */}
                    <label className="topk-control" title="Number of note chunks sent to the AI (higher = more context, slower)">
                        <span className="topk-label">Context</span>
                        <input
                            id="topk-slider"
                            type="range"
                            min={1}
                            max={15}
                            step={1}
                            value={topK}
                            onChange={(e) => onTopKChange(Number(e.target.value))}
                            disabled={isLoading}
                            className="topk-slider"
                        />
                        <span className="topk-value">{topK}</span>
                    </label>

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
        </div>
    );
}
