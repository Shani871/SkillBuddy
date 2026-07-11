import React, { useState, useEffect, useRef } from "react";
import api from "../services/api";
import { Send, Bot, User, RefreshCw, AlertCircle } from "lucide-react";

const Chatbot = () => {
  const [messages, setMessages] = useState([
    {
      role: "model",
      text: "Hello! I am SkillBuddy AI Assistant. I can guide you through your course roadmaps, recommend projects, or help answer your academic questions. What are we studying today?",
    },
  ]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const chatEndRef = useRef(null);

  const scrollToBottom = () => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSend = async (e) => {
    e.preventDefault();
    if (!input.trim() || loading) return;

    const userMessage = input.trim();
    setInput("");
    setError("");

    // Append user message
    const updatedMessages = [...messages, { role: "user", text: userMessage }];
    setMessages(updatedMessages);
    setLoading(true);

    try {
      // Map React roles ('model') to Gemini standard 'model' roles
      const apiHistory = messages.map((m) => ({
        role: m.role,
        text: m.text,
      }));

      const response = await api.post("/api/chatbot/", {
        message: userMessage,
        history: apiHistory,
      });

      setMessages((prev) => [
        ...prev,
        { role: "model", text: response.data.reply },
      ]);
    } catch (err) {
      console.error(err);
      setError(err.response?.data?.detail || "Could not retrieve tutor response.");
    } finally {
      setLoading(false);
    }
  };

  const handleClear = () => {
    setMessages([
      {
        role: "model",
        text: "Hello! I am SkillBuddy AI Assistant. I can guide you through your course roadmaps, recommend projects, or help answer your academic questions. What are we studying today?",
      },
    ]);
    setError("");
  };

  return (
    <div className="flex flex-col h-[75vh] bg-slate-900/40 border border-slate-800/80 rounded-2xl overflow-hidden shadow-2xl">
      {/* Header */}
      <div className="bg-slate-950/80 border-b border-slate-800/80 px-6 py-4 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 bg-blue-500/10 border border-blue-500/20 rounded-xl flex items-center justify-center text-blue-400">
            <Bot size={22} />
          </div>
          <div>
            <h3 className="font-bold text-white text-sm">SkillBuddy AI Tutor</h3>
            <span className="text-xs text-emerald-400 font-semibold flex items-center gap-1.5">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
              Online
            </span>
          </div>
        </div>

        <button
          onClick={handleClear}
          className="text-slate-400 hover:text-slate-200 text-xs flex items-center gap-1.5 transition-colors border border-slate-800 rounded-lg px-3 py-1.5"
        >
          <RefreshCw size={14} />
          Clear Conversation
        </button>
      </div>

      {/* Message Area */}
      <div className="flex-1 overflow-y-auto p-6 space-y-6">
        {messages.map((msg, index) => {
          const isModel = msg.role === "model";
          return (
            <div key={index} className={`flex gap-4 ${!isModel && "flex-row-reverse"}`}>
              <div
                className={`w-9 h-9 rounded-full flex items-center justify-center text-sm shrink-0 ${
                  isModel
                    ? "bg-blue-500/10 border border-blue-500/20 text-blue-400"
                    : "bg-indigo-500/10 border border-indigo-500/20 text-indigo-400"
                }`}
              >
                {isModel ? <Bot size={18} /> : <User size={18} />}
              </div>
              <div
                className={`max-w-[70%] rounded-2xl px-4 py-3 text-sm leading-relaxed shadow-lg ${
                  isModel
                    ? "bg-slate-900/90 border border-slate-800/80 text-slate-100"
                    : "bg-blue-600 text-white"
                }`}
              >
                <div className="whitespace-pre-line">{msg.text}</div>
              </div>
            </div>
          );
        })}

        {loading && (
          <div className="flex gap-4">
            <div className="w-9 h-9 rounded-full bg-blue-500/10 border border-blue-500/20 text-blue-400 flex items-center justify-center shrink-0">
              <Bot size={18} className="animate-spin" />
            </div>
            <div className="bg-slate-900/90 border border-slate-800/80 text-slate-400 rounded-2xl px-4 py-3 text-sm flex items-center gap-1">
              Thinking...
            </div>
          </div>
        )}

        {error && (
          <div className="bg-red-500/10 border border-red-500/20 text-red-400 text-sm rounded-xl p-4 flex items-center gap-2 max-w-lg mx-auto">
            <AlertCircle size={18} className="shrink-0" />
            <span>{error}</span>
          </div>
        )}

        <div ref={chatEndRef} />
      </div>

      {/* Input Box */}
      <form onSubmit={handleSend} className="bg-slate-950/80 border-t border-slate-800/80 p-4">
        <div className="flex gap-3">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            disabled={loading}
            placeholder="Ask a question about algorithms, programming, or roadmaps..."
            className="flex-1 bg-slate-900/60 border border-slate-800 focus:border-blue-500 focus:ring-1 focus:ring-blue-500 rounded-xl px-4 py-3.5 text-white text-sm outline-none transition-all placeholder:text-slate-600"
          />
          <button
            type="submit"
            disabled={loading || !input.trim()}
            className="bg-blue-600 hover:bg-blue-500 disabled:bg-blue-800 text-white rounded-xl px-5 flex items-center justify-center transition-colors shadow-lg shadow-blue-500/10"
          >
            <Send size={18} />
          </button>
        </div>
      </form>
    </div>
  );
};

export default Chatbot;
