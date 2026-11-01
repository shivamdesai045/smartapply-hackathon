import React, { useState, useEffect, useRef } from "react";
import { useLocation } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { sendChatMessage } from "../lib/api";

const QUICK_ACTIONS = [
  { label: "Documents for Passport?", query: "What documents are required for Passport?" },
  { label: "How to correct name in Aadhaar?", query: "How do I correct my name in Aadhaar?" },
  { label: "PAN-Aadhaar mismatch help", query: "My name differs between PAN Card and Aadhaar Card. How do I fix it?" },
  { label: "Track my application", query: "Where can I track the official status of my application?" },
];

const DEVANAGARI_CHARS = {
  vowels: ["अ", "आ", "इ", "ई", "उ", "ऊ", "ए", "ऐ", "ओ", "औ", "अं", "अः"],
  matras: ["ा", "ि", "ी", "ु", "ू", "े", "ै", "ो", "ौ", "ं", "ः", "्"],
  consonants_row1: ["क", "ख", "ग", "घ", "ङ", "च", "छ", "ज", "झ", "ञ"],
  consonants_row2: ["ट", "ठ", "ड", "ढ", "ण", "त", "थ", "द", "ध", "न"],
  consonants_row3: ["प", "फ", "ब", "भ", "म", "य", "र", "ल", "व", "श"],
  consonants_row4: ["ष", "स", "ह", "ळ", "क्ष", "ज्ञ", "।", "॥", "०", "१", "२", "३", "४", "५", "६", "७", "८", "९"],
};

function formatMessage(text) {
  if (!text) return "";
  // Simple markdown renderer for bold, lists, and links
  const lines = text.split("\n");
  return lines.map((line, idx) => {
    let formatted = line;

    // Bold formatting: **text**
    const boldParts = formatted.split(/(\*\*[^*]+\*\*)/g);
    const content = boldParts.map((part, pIdx) => {
      if (part.startsWith("**") && part.endsWith("**")) {
        return <strong key={pIdx} className="font-semibold">{part.slice(2, -2)}</strong>;
      }
      return part;
    });

    if (line.trim().startsWith("- ")) {
      return (
        <li key={idx} className="ml-4 list-disc text-xs sm:text-sm my-0.5">
          {content}
        </li>
      );
    }

    return (
      <p key={idx} className="min-h-[1.2em] my-1 text-xs sm:text-sm leading-relaxed">
        {content}
      </p>
    );
  });
}

function ChatBot() {
  const { i18n } = useTranslation();
  const location = useLocation();

  const [open, setOpen] = useState(false);
  const [messages, setMessages] = useState(() => {
    try {
      const saved = sessionStorage.getItem("sahayak_chat_history");
      if (saved) return JSON.parse(saved);
    } catch (_e) {}
    return [
      {
        from: "bot",
        text: "Namaste! I am Sahayak Assistant. Ask me anything about required documents, official government portals, or resolving spelling and DOB mismatches.",
        sources: [],
        suggestions: [],
      },
    ];
  });

  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [chatLang, setChatLang] = useState("en");
  const [audioEnabled, setAudioEnabled] = useState(false);
  const [keyboardOpen, setKeyboardOpen] = useState(false);
  const [isListening, setIsListening] = useState(false);

  const messagesEndRef = useRef(null);
  const recognitionRef = useRef(null);
  const inputRef = useRef(null);

  // Sync language with i18n
  useEffect(() => {
    if (["en", "hi", "mr"].includes(i18n.language)) {
      setChatLang(i18n.language);
    }
  }, [i18n.language]);

  // Save to sessionStorage
  useEffect(() => {
    try {
      sessionStorage.setItem("sahayak_chat_history", JSON.stringify(messages));
    } catch (_e) {}
  }, [messages]);

  // Scroll to bottom on new message
  useEffect(() => {
    if (open) {
      messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    }
  }, [messages, open]);

  // Speech Recognition setup
  useEffect(() => {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (SpeechRecognition) {
      const recognition = new SpeechRecognition();
      recognition.continuous = false;
      recognition.interimResults = false;

      recognition.onstart = () => setIsListening(true);
      recognition.onend = () => setIsListening(false);
      recognition.onerror = () => setIsListening(false);
      recognition.onresult = (event) => {
        const transcript = event.results[0][0].transcript;
        if (transcript) {
          setInput((prev) => (prev ? `${prev} ${transcript}` : transcript));
        }
      };
      recognitionRef.current = recognition;
    }
  }, []);

  // Detect current service context from URL
  const currentServiceContext = React.useMemo(() => {
    const match = location.pathname.match(/\/checklist\/([^/?#]+)/);
    if (match) {
      return decodeURIComponent(match[1]).replace(/-/g, " ");
    }
    return null;
  }, [location.pathname]);

  const toggleVoiceInput = () => {
    if (!recognitionRef.current) {
      alert("Voice input is not supported in this browser. Please use Chrome or Edge.");
      return;
    }
    if (isListening) {
      recognitionRef.current.stop();
    } else {
      const langMap = { en: "en-IN", hi: "hi-IN", mr: "mr-IN" };
      recognitionRef.current.lang = langMap[chatLang] || "en-IN";
      try {
        recognitionRef.current.start();
      } catch (err) {
        console.warn("Speech recognition error:", err);
      }
    }
  };

  const speakText = (text) => {
    if (!audioEnabled || !window.speechSynthesis) return;
    try {
      window.speechSynthesis.cancel();
      // Strip markdown asterisks and URLs for speech
      const clean = text.replace(/\*\*/g, "").replace(/https?:\/\/\S+/g, "");
      const utterance = new SpeechSynthesisUtterance(clean);
      const langMap = { en: "en-IN", hi: "hi-IN", mr: "mr-IN" };
      utterance.lang = langMap[chatLang] || "en-IN";
      window.speechSynthesis.speak(utterance);
    } catch (e) {
      console.warn("Speech synthesis error:", e);
    }
  };

  const handleSend = async (messageText = input) => {
    const cleanMsg = (messageText || "").trim();
    if (!cleanMsg || loading) return;

    const userMessage = { from: "user", text: cleanMsg };
    setMessages((prev) => [...prev, userMessage]);
    setInput("");
    setLoading(true);

    try {
      const res = await sendChatMessage({
        message: cleanMsg,
        service: currentServiceContext,
        language: chatLang,
      });

      const botMessage = {
        from: "bot",
        text: res.reply || "Sorry, I could not process your query right now.",
        sources: res.sources || [],
        suggestions: res.suggestedQuestions || res.suggestions || [],
        warning: res.warning,
      };

      setMessages((prev) => [...prev, botMessage]);
      speakText(botMessage.text);
    } catch (err) {
      console.error("Chat error:", err);
      setMessages((prev) => [
        ...prev,
        {
          from: "bot",
          text: "I'm having trouble connecting to the backend. Please ensure the server is running on port 5000.",
          sources: [],
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  const handleVirtualKey = (char) => {
    setInput((prev) => prev + char);
    inputRef.current?.focus();
  };

  const handleVirtualBackspace = () => {
    setInput((prev) => prev.slice(0, -1));
    inputRef.current?.focus();
  };

  return (
    <>
      {/* Floating Toggle Button */}
      <button
        onClick={() => setOpen(!open)}
        className="fixed bottom-6 right-6 w-14 h-14 rounded-full bg-brand-600 hover:bg-brand-700 text-white shadow-2xl flex items-center justify-center text-2xl z-40 transition-transform hover:scale-105 active:scale-95 focus:outline-none focus:ring-4 focus:ring-brand-400 print:hidden"
        title="Chat with Sahayak AI"
        aria-label="Chat with Sahayak Assistant"
        aria-expanded={open}
      >
        {open ? "✕" : "💬"}
      </button>

      {/* Chat Window */}
      {open && (
        <aside
          role="complementary"
          aria-label="Sahayak AI Assistant"
          className="fixed bottom-24 right-4 sm:right-6 w-[calc(100vw-2rem)] sm:w-96 md:w-[420px] h-[580px] max-h-[80vh] bg-white dark:bg-gray-800 rounded-2xl shadow-2xl border border-gray-200 dark:border-gray-700 flex flex-col z-40 overflow-hidden animate-fade-in print:hidden"
        >
          {/* Header */}
          <div className="bg-brand-700 text-white px-4 py-3 flex items-center justify-between shadow-md">
            <div className="flex items-center gap-2.5">
              <span className="w-8 h-8 rounded-full bg-white/20 flex items-center justify-center text-base">
                🤖
              </span>
              <div>
                <h3 className="font-bold text-sm leading-tight">Sahayak AI Assistant</h3>
                <p className="text-[11px] text-white/80">
                  {currentServiceContext ? `Context: ${currentServiceContext}` : "Document Guidance & Portal Help"}
                </p>
              </div>
            </div>

            <div className="flex items-center gap-2">
              {/* Language Selector */}
              <select
                value={chatLang}
                onChange={(e) => setChatLang(e.target.value)}
                className="bg-brand-800 text-white text-xs rounded-lg px-2 py-1 outline-none border border-brand-600 cursor-pointer"
                title="Select Language"
              >
                <option value="en">English</option>
                <option value="hi">हिंदी</option>
                <option value="mr">मराठी</option>
              </select>

              {/* Audio Toggle */}
              <button
                onClick={() => setAudioEnabled(!audioEnabled)}
                className={`p-1.5 rounded-lg text-xs transition ${
                  audioEnabled ? "bg-white/30 text-white" : "bg-transparent text-white/60 hover:text-white"
                }`}
                title={audioEnabled ? "Mute Bot Voice" : "Enable Bot Voice"}
                aria-label="Toggle voice output"
              >
                {audioEnabled ? "🔊" : "🔇"}
              </button>

              {/* Close Button */}
              <button
                onClick={() => setOpen(false)}
                className="p-1 rounded-lg hover:bg-white/20 text-white text-base leading-none"
                aria-label="Close chat"
              >
                ✕
              </button>
            </div>
          </div>

          {/* Messages Area */}
          <div className="flex-1 overflow-y-auto p-3.5 space-y-3 bg-gray-50 dark:bg-gray-900/40">
            {messages.map((msg, i) => (
              <div
                key={i}
                className={`flex flex-col ${
                  msg.from === "bot" ? "items-start" : "items-end"
                }`}
              >
                <div
                  className={`px-3.5 py-2.5 rounded-2xl max-w-[88%] shadow-sm ${
                    msg.from === "bot"
                      ? "bg-white dark:bg-gray-800 text-gray-800 dark:text-gray-100 border border-gray-200 dark:border-gray-700 rounded-tl-sm"
                      : "bg-brand-600 text-white rounded-tr-sm"
                  }`}
                >
                  {/* Warning banner if user posted sensitive data */}
                  {msg.warning && (
                    <div className="mb-2 p-1.5 bg-amber-50 dark:bg-amber-950/40 border border-amber-300 dark:border-amber-700 text-amber-800 dark:text-amber-200 rounded text-xs flex items-center gap-1.5">
                      <span>⚠️</span>
                      <span>{msg.warning}</span>
                    </div>
                  )}

                  <div className="break-words">{formatMessage(msg.text)}</div>

                  {/* Verified Sources Links */}
                  {msg.sources && msg.sources.length > 0 && (
                    <div className="mt-2.5 pt-2 border-t border-gray-200 dark:border-gray-700 text-xs">
                      <p className="font-semibold text-gray-600 dark:text-gray-300 mb-1">
                        Verified Official Portals:
                      </p>
                      <div className="flex flex-wrap gap-1.5">
                        {msg.sources.map((s, sIdx) => (
                          <a
                            key={sIdx}
                            href={s.url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="inline-flex items-center gap-1 px-2 py-0.5 rounded bg-brand-50 dark:bg-brand-950 text-brand-700 dark:text-brand-300 hover:underline border border-brand-200 dark:border-brand-800 text-[11px]"
                          >
                            <span>🔗</span> {s.title || "Official Portal"}
                          </a>
                        ))}
                      </div>
                    </div>
                  )}
                </div>

                {/* Follow-up suggestions */}
                {msg.suggestions && msg.suggestions.length > 0 && i === messages.length - 1 && (
                  <div className="mt-2 flex flex-wrap gap-1.5 pl-1 max-w-[95%]">
                    {msg.suggestions.map((sug, sIdx) => (
                      <button
                        key={sIdx}
                        onClick={() => handleSend(sug)}
                        className="text-left text-xs px-2.5 py-1 rounded-full bg-white dark:bg-gray-800 border border-brand-300 dark:border-brand-700 text-brand-700 dark:text-brand-300 hover:bg-brand-50 dark:hover:bg-gray-700 transition shadow-xs"
                      >
                        💬 {sug}
                      </button>
                    ))}
                  </div>
                )}
              </div>
            ))}

            {loading && (
              <div className="flex items-center gap-2 p-3 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-2xl w-fit text-xs text-gray-500 dark:text-gray-400 animate-pulse">
                <span>🤖</span>
                <span>Sahayak is searching verified guidance...</span>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>

          {/* Quick Action Chips (Shown when few messages) */}
          {messages.length <= 2 && (
            <div className="px-3 py-2 bg-gray-100 dark:bg-gray-800/80 border-t border-gray-200 dark:border-gray-700 flex gap-1.5 overflow-x-auto scrollbar-none">
              {QUICK_ACTIONS.map((action, idx) => (
                <button
                  key={idx}
                  onClick={() => handleSend(action.query)}
                  className="px-2.5 py-1 bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-full text-xs text-gray-700 dark:text-gray-200 hover:bg-brand-50 hover:text-brand-700 dark:hover:bg-gray-600 whitespace-nowrap transition"
                >
                  {action.label}
                </button>
              ))}
            </div>
          )}

          {/* Virtual Devanagari Keyboard Drawer */}
          {keyboardOpen && (
            <div className="p-2 bg-gray-100 dark:bg-gray-900 border-t border-gray-300 dark:border-gray-700 max-h-44 overflow-y-auto text-xs select-none">
              <div className="flex items-center justify-between pb-1 text-[11px] text-gray-500 font-semibold">
                <span>Devanagari Keyboard (Hindi / Marathi)</span>
                <button onClick={() => setKeyboardOpen(false)} className="text-gray-600 dark:text-gray-400">✕ Close</button>
              </div>

              {/* Vowels & Matras */}
              <div className="flex flex-wrap gap-1 pb-1">
                {DEVANAGARI_CHARS.vowels.map((ch) => (
                  <button
                    key={ch}
                    onClick={() => handleVirtualKey(ch)}
                    className="w-7 h-7 bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-700 rounded hover:bg-brand-50 dark:hover:bg-gray-700 text-sm font-medium"
                  >
                    {ch}
                  </button>
                ))}
              </div>
              <div className="flex flex-wrap gap-1 pb-1">
                {DEVANAGARI_CHARS.matras.map((ch) => (
                  <button
                    key={ch}
                    onClick={() => handleVirtualKey(ch)}
                    className="w-7 h-7 bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-700 rounded hover:bg-brand-50 dark:hover:bg-gray-700 text-sm font-medium"
                  >
                    {ch}
                  </button>
                ))}
              </div>

              {/* Consonants */}
              <div className="flex flex-wrap gap-1 pb-1">
                {DEVANAGARI_CHARS.consonants_row1.concat(DEVANAGARI_CHARS.consonants_row2).map((ch) => (
                  <button
                    key={ch}
                    onClick={() => handleVirtualKey(ch)}
                    className="w-7 h-7 bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-700 rounded hover:bg-brand-50 dark:hover:bg-gray-700 text-sm font-medium"
                  >
                    {ch}
                  </button>
                ))}
              </div>
              <div className="flex flex-wrap gap-1">
                {DEVANAGARI_CHARS.consonants_row3.concat(DEVANAGARI_CHARS.consonants_row4).map((ch) => (
                  <button
                    key={ch}
                    onClick={() => handleVirtualKey(ch)}
                    className="w-7 h-7 bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-700 rounded hover:bg-brand-50 dark:hover:bg-gray-700 text-sm font-medium"
                  >
                    {ch}
                  </button>
                ))}
                <button
                  onClick={() => handleVirtualKey(" ")}
                  className="px-3 h-7 bg-gray-200 dark:bg-gray-700 rounded hover:bg-gray-300 text-xs font-semibold"
                >
                  Space
                </button>
                <button
                  onClick={handleVirtualBackspace}
                  className="px-2.5 h-7 bg-red-100 dark:bg-red-900/40 text-red-700 dark:text-red-300 rounded hover:bg-red-200 text-xs font-semibold"
                >
                  ⌫ Del
                </button>
              </div>
            </div>
          )}

          {/* Input Bar */}
          <div className="p-2.5 bg-white dark:bg-gray-800 border-t border-gray-200 dark:border-gray-700 flex items-center gap-1.5">
            {/* Keyboard toggle button */}
            <button
              onClick={() => setKeyboardOpen(!keyboardOpen)}
              className={`p-2 rounded-full border transition ${
                keyboardOpen
                  ? "bg-brand-50 dark:bg-gray-700 border-brand-500 text-brand-600"
                  : "border-gray-300 dark:border-gray-600 text-gray-500 hover:bg-gray-100 dark:hover:bg-gray-700"
              }`}
              title="Toggle Devanagari Virtual Keyboard (Hindi/Marathi)"
              aria-label="Toggle Hindi keyboard"
            >
              ⌨️
            </button>

            {/* Voice Input button */}
            <button
              onClick={toggleVoiceInput}
              className={`p-2 rounded-full border transition ${
                isListening
                  ? "bg-red-500 text-white border-red-600 animate-pulse"
                  : "border-gray-300 dark:border-gray-600 text-gray-500 hover:bg-gray-100 dark:hover:bg-gray-700"
              }`}
              title={isListening ? "Listening... click to stop" : "Voice Input (Speak your question)"}
              aria-label="Voice input"
            >
              🎤
            </button>

            {/* Text Input */}
            <input
              ref={inputRef}
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleSend()}
              placeholder={
                chatLang === "hi"
                  ? "अपना प्रश्न यहाँ लिखें..."
                  : chatLang === "mr"
                  ? "तुमचा प्रश्न येथे विचारा..."
                  : "Ask about documents, portals..."
              }
              className="flex-1 px-3.5 py-2 text-sm bg-gray-50 dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-full focus:outline-none focus:ring-2 focus:ring-brand-500 text-gray-900 dark:text-gray-100 placeholder-gray-400"
              disabled={loading}
            />

            {/* Send Button */}
            <button
              onClick={() => handleSend()}
              disabled={!input.trim() || loading}
              className="px-4 py-2 bg-brand-600 hover:bg-brand-700 disabled:opacity-50 text-white rounded-full text-sm font-semibold transition flex items-center justify-center shadow-sm"
              aria-label="Send message"
            >
              ➤
            </button>
          </div>
        </aside>
      )}
    </>
  );
}

export default ChatBot;
