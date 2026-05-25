import { useState, useRef, useEffect } from "react";
import "./App.css";

import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

const API_URL =
  "https://masshoops-api.nicebush-7fc1af01.eastus.azurecontainerapps.io/basketballStream";

const suggestedPrompts = [
  "Who is the greatest basketball player ever?",
  "Explain why Steph Curry changed basketball",
  "Compare Kobe Bryant vs Michael Jordan",
  "Why is Nikola Jokic difficult to guard?",
  "Explain pick and roll defense",
  "Build the perfect NBA starting five",
];

function App() {

  const [question, setQuestion] = useState("");

  const [messages, setMessages] = useState([]);

  const [loading, setLoading] = useState(false);

  const messagesEndRef = useRef(null);

  // =====================================================
  // SESSION
  // =====================================================

  const sessionIdRef = useRef(
    crypto.randomUUID()
  );

  // =====================================================
  // AUTO SCROLL
  // =====================================================

  useEffect(() => {

    messagesEndRef.current?.scrollIntoView({
      behavior: "smooth",
    });

  }, [messages]);

  // =====================================================
  // SEND QUESTION
  // =====================================================

  const sendQuestion = async (
    prompt = null
  ) => {

    const userQuestion =
      prompt || question;

    if (!userQuestion.trim()) return;

    // =================================================
    // USER MESSAGE
    // =================================================

    const userMessage = {
      role: "user",
      content: userQuestion,
    };

    setMessages((prev) => [
      ...prev,
      userMessage,
    ]);

    setQuestion("");

    setLoading(true);

    // =================================================
    // EMPTY ASSISTANT MESSAGE
    // =================================================

    const assistantIndex =
      messages.length + 1;

    setMessages((prev) => [
      ...prev,
      {
        role: "assistant",
        content: "",
      },
    ]);

    try {

      const response = await fetch(
        API_URL,
        {
          method: "POST",

          headers: {
            "Content-Type":
              "application/json",
          },

          body: JSON.stringify({
            message: userQuestion,
            session_id:
              sessionIdRef.current,
          }),
        }
      );

      if (!response.body) {

        throw new Error(
          "No response body."
        );
      }

      const reader =
        response.body.getReader();

      const decoder =
        new TextDecoder();

      let fullText = "";

      while (true) {

        const {
          done,
          value,
        } = await reader.read();

        if (done) break;

        const chunk =
          decoder.decode(value);

        fullText += chunk;

        setMessages((prev) => {

          const updated = [...prev];

          updated[
            assistantIndex
          ] = {
            role: "assistant",
            content: fullText,
          };

          return updated;
        });
      }

    } catch (error) {

      console.error(error);

      setMessages((prev) => {

        const updated = [...prev];

        updated[
          assistantIndex
        ] = {
          role: "assistant",
          content:
            "MassHoops AI had trouble responding.",
        };

        return updated;
      });
    }

    setLoading(false);
  };

  // =====================================================
  // ENTER KEY
  // =====================================================

  const handleKeyDown = (e) => {

    if (
      e.key === "Enter"
      && !e.shiftKey
    ) {

      e.preventDefault();

      sendQuestion();
    }
  };

  // =====================================================
  // RENDER
  // =====================================================

  return (

    <div className="app">

      <div className="chat-container">

        <h1>
          🏀 MassHoops AI
        </h1>

        <p className="subtitle">
          Your AI basketball knowledge assistant
        </p>

        {/* ========================================= */}
        {/* SUGGESTED PROMPTS */}
        {/* ========================================= */}

        {messages.length === 0 && (

          <div className="suggested-prompts">

            {suggestedPrompts.map(
              (
                prompt,
                index
              ) => (

                <button
                  key={index}
                  className="prompt-button"
                  onClick={() =>
                    sendQuestion(prompt)
                  }
                >
                  {prompt}
                </button>

              )
            )}

          </div>
        )}

        {/* ========================================= */}
        {/* MESSAGES */}
        {/* ========================================= */}

        <div className="messages">

          {messages.map(
            (msg, index) => (

              <div
                key={index}
                className={`message ${msg.role}`}
              >

                <div className="message-text">

                  <ReactMarkdown
                    remarkPlugins={[
                      remarkGfm,
                    ]}
                  >
                    {msg.content}
                  </ReactMarkdown>

                </div>

              </div>

            )
          )}

          {/* ===================================== */}
          {/* TYPING */}
          {/* ===================================== */}

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

        {/* ========================================= */}
        {/* INPUT */}
        {/* ========================================= */}

        <div className="input-container">

          <textarea
            value={question}
            onChange={(e) =>
              setQuestion(
                e.target.value
              )
            }
            onKeyDown={
              handleKeyDown
            }
            placeholder="Ask anything about basketball..."
          />

          <button
            onClick={() =>
              sendQuestion()
            }
            disabled={loading}
          >

            {loading
              ? "Thinking..."
              : "Send"}

          </button>

        </div>

      </div>

    </div>
  );
}

export default App;