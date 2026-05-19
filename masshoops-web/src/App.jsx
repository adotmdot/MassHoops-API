import { useState, useRef, useEffect } from "react";
import axios from "axios";
import "./App.css";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

const API_URL = "http://localhost:8000/basketballQuery";

const suggestedPrompts = [
  "Top scorers this season",
  "Show Lakers roster",
  "Compare LeBron James vs Michael Jordan",
  "Eastern Conference standings",
  "Who leads the league in assists?",
  "Show a chart of points per game leaders",
];

function App() {
  const [question, setQuestion] = useState("");
  const [messages, setMessages] = useState([]);
  const [loading, setLoading] = useState(false);

  const messagesEndRef = useRef(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  const sendQuestion = async (prompt = null) => {
    const userQuestion = prompt || question;
    if (!userQuestion.trim()) return;

    const userMessage = {
      role: "user",
      content: userQuestion,
    };

    setMessages((prev) => [...prev, userMessage]);
    setQuestion("");
    setLoading(true);

    try {
      const response = await axios.post(API_URL, {
        message: userQuestion,
        session_id: "masshoops-session-1",
      });

      const botMessage = {
        role: "assistant",
        content:
          response.data.reply ||
          response.data.answer ||
          response.data.response ||
          "No response returned.",
        chartUrl: response.data.chart_url
          ? `http://localhost:8000${response.data.chart_url}`
          : null,
      };

      setMessages((prev) => [...prev, botMessage]);
    } catch (error) {
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: "Error connecting to MassHoops API.",
        },
      ]);
    }

    setLoading(false);
  };

  const handleKeyDown = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendQuestion();
    }
  };

  return (
    <div className="app">
      <div className="chat-container">
        <h1>🏀 MassHoops AI</h1>

        {messages.length === 0 && (
          <div className="suggested-prompts">
            {suggestedPrompts.map((prompt, index) => (
              <button
                key={index}
                className="prompt-button"
                onClick={() => sendQuestion(prompt)}
              >
                {prompt}
              </button>
            ))}
          </div>
        )}

        <div className="messages">
          {messages.map((msg, index) => (
            <div key={index} className={`message ${msg.role}`}>
              <div className="message-text">
                <ReactMarkdown remarkPlugins={[remarkGfm]}>
                  {msg.content}
                </ReactMarkdown>
              </div>

              {msg.chartUrl && (
                <img
                  src={msg.chartUrl}
                  alt="Chart"
                  className="chart-image"
                />
              )}
            </div>
          ))}

          {loading && (
            <div className="message assistant">
              <div className="typing-indicator">
                <span></span>
                <span></span>
                <span></span>
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        <div className="input-container">
          <textarea
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask anything about basketball..."
          />
          <button onClick={() => sendQuestion()}>Send</button>
        </div>
      </div>
    </div>
  );
}

export default App;