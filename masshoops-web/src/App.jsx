import { useState, useEffect, useRef } from 'react'
import './App.css'

function formatMessage(content) {
  // Detect markdown table rows
  if (content.includes('|') && content.includes('---')) {
    const lines = content
      .split('\n')
      .map((line) => line.trim())
      .filter((line) => line)

    const tableLines = lines.filter((line) => line.includes('|'))

    if (tableLines.length >= 3) {
      const headers = tableLines[0]
        .split('|')
        .map((cell) => cell.trim())
        .filter(Boolean)

      const rows = tableLines.slice(2).map((line) =>
        line
          .split('|')
          .map((cell) => cell.trim())
          .filter(Boolean)
      )

      const introText = lines
        .filter((line) => !line.includes('|'))
        .join(' ')

      return (
        <>
          {introText && <p className="message-text">{introText}</p>}

          <div className="table-wrapper">
            <table className="stats-table">
              <thead>
                <tr>
                  {headers.map((header, index) => (
                    <th key={index}>{header}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {rows.map((row, rowIndex) => (
                  <tr key={rowIndex}>
                    {row.map((cell, cellIndex) => (
                      <td key={cellIndex}>{cell}</td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )
    }
  }

  // Regular text
  return <p className="message-text">{content}</p>
}

function App() {
  const [message, setMessage] = useState('')
  const [messages, setMessages] = useState([
    {
      role: 'assistant',
      content:
        '👋 Welcome to MassHoops! Ask me anything about NBA players, teams, stats, and live games.',
    },
  ])
  const [loading, setLoading] = useState(false)

  const messagesEndRef = useRef(null)

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, loading])

  const sendMessage = async () => {
    if (!message.trim()) return

    const userMessage = {
      role: 'user',
      content: message,
    }

    setMessages((prev) => [...prev, userMessage])
    setLoading(true)

    const currentMessage = message
    setMessage('')

    try {
      const response = await fetch('http://127.0.0.1:8000/basketballQuery', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          session_id: 'frontend-demo',
          message: currentMessage,
        }),
      })

      const data = await response.json()

      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          content: data.reply || 'No response received.',
        },
      ])
    } catch (error) {
      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          content: '❌ Error connecting to MassHoops API.',
        },
      ])
    }

    setLoading(false)
  }

  const handleKeyDown = (e) => {
    if (e.key === 'Enter') {
      sendMessage()
    }
  }

  return (
    <div className="app">
      <aside className="sidebar">
        <h1>🏀 MassHoops</h1>
        <p>NBA Analytics AI Assistant</p>
      </aside>

      <main className="chat-container">
        <div className="chat-header">
          <h2>MassHoops Chat</h2>
        </div>

        <div className="messages">
          {messages.map((msg, index) => (
            <div
              key={index}
              className={`message-row ${msg.role}`}
            >
              <div className={`message ${msg.role}`}>
                {formatMessage(msg.content)}
              </div>
            </div>
          ))}

          {loading && (
            <div className="message-row assistant">
              <div className="message assistant">
                <p className="message-text">⏳ Thinking...</p>
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        <div className="input-area">
          <input
            type="text"
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask about LeBron James, Lakers stats, standings..."
          />
          <button onClick={sendMessage}>Send</button>
        </div>
      </main>
    </div>
  )
}

export default App