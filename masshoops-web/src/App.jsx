import { useState, useRef, useEffect } from "react";
import axios from "axios";
import "./App.css";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { getPlayerHeadshot, getTeamLogo } from "./utils/imageHelpers";

const API_URL =
  "https://masshoops-api.nicebush-7fc1af01.eastus.azurecontainerapps.io/basketballQuery";

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
          ? (
              response.data.chart_url.startsWith("http")
                ? response.data.chart_url
                : `https://masshoops-api.nicebush-7fc1af01.eastus.azurecontainerapps.io${response.data.chart_url}`
            )
          : null,

        // New fields for player/team images
        player_id: response.data.player_id,
        player_name: response.data.player_name,
        team_id: response.data.team_id,
        team_name: response.data.team_name,
        season: response.data.season,
        games: response.data.games,
        points_per_game: response.data.points_per_game,
        rebounds_per_game: response.data.rebounds_per_game,
        assists_per_game: response.data.assists_per_game,
        fg_pct: response.data.fg_pct,
        three_pct: response.data.three_pct,
        ft_pct: response.data.ft_pct,
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
              {!msg.player_id && (
                <div className="message-text">
                  <ReactMarkdown remarkPlugins={[remarkGfm]}>
                    {msg.content}
                  </ReactMarkdown>
                </div>
              )}

              {/* Player Card */}
              {msg.player_id && (
                <div className="premium-player-card">
                  {/* Header */}
                  <div className="player-card-header">
                    <img
                      src={getTeamLogo(msg.team_id)}
                      alt={msg.team_name}
                      className="header-team-logo"
                    />
                    <div>
                      <h2>{msg.player_name}</h2>
                      <p>{msg.team_name} • {msg.season}</p>
                    </div>
                  </div>

                  {/* Body */}
                  <div className="player-card-body">
                    {/* Left */}
                    <div className="player-left">
                      <img
                        src={getPlayerHeadshot(msg.player_id)}
                        alt={msg.player_name}
                        className="premium-headshot"
                      />
                    </div>

                    {/* Center */}
                    <div className="player-main-stat">
                      <div className="main-stat-value">
                        {msg.points_per_game}
                      </div>
                      <div className="main-stat-label">PPG</div>
                    </div>

                    {/* Right Stats */}
                    <div className="player-stats-grid">
                      <div>
                        <span className="stat-value">{msg.rebounds_per_game}</span>
                        <span className="stat-label">RPG</span>
                      </div>

                      <div>
                        <span className="stat-value">{msg.assists_per_game}</span>
                        <span className="stat-label">APG</span>
                      </div>

                      <div>
                        <span className="stat-value">{msg.fg_pct}%</span>
                        <span className="stat-label">FG%</span>
                      </div>

                      <div>
                        <span className="stat-value">{msg.three_pct}%</span>
                        <span className="stat-label">3PT%</span>
                      </div>

                      <div>
                        <span className="stat-value">{msg.ft_pct}%</span>
                        <span className="stat-label">FT%</span>
                      </div>

                      <div>
                        <span className="stat-value">{msg.games}</span>
                        <span className="stat-label">GP</span>
                      </div>
                    </div>
                  </div>
                </div>
              )}

              {/* Chart */}
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