<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
</head>
<body>

  <h1>🏀 MassHoops AI</h1>

  <p>
    MassHoops AI is an AI-powered basketball assistant built with FastAPI,
    React, OpenAI, LangChain, Docker, Azure Container Apps, and Vercel.
  </p>

  <h2>🚀 Live Demo</h2>

  <ul>
    <li><a href="https://masshoops-ai.vercel.app">Frontend App</a></li>
    <li><a href="https://masshoops-api.nicebush-7fc1af01.eastus.azurecontainerapps.io">Backend API</a></li>
    <li><a href="https://masshoops-api.nicebush-7fc1af01.eastus.azurecontainerapps.io/docs">Swagger Docs</a></li>
  </ul>

  <h2>🧠 Features</h2>

  <ul>
    <li>AI basketball knowledge assistant</li>
    <li>Streaming ChatGPT-style responses</li>
    <li>Basketball strategy explanations</li>
    <li>Player comparisons and debates</li>
    <li>NBA history and coaching concepts</li>
    <li>Markdown-rendered responses</li>
    <li>Modern responsive React UI</li>
    <li>FastAPI backend with OpenAI integration</li>
  </ul>

  <h2>🛠️ Tech Stack</h2>

  <h3>Frontend</h3>
  <ul>
    <li>React</li>
    <li>Vite</li>
    <li>JavaScript</li>
    <li>React Markdown</li>
    <li>CSS3</li>
  </ul>

  <h3>Backend</h3>
  <ul>
    <li>Python</li>
    <li>FastAPI</li>
    <li>LangChain</li>
    <li>OpenAI API</li>
    <li>SQLAlchemy</li>
  </ul>

  <h3>Deployment</h3>
  <ul>
    <li>Docker</li>
    <li>Azure Container Apps</li>
    <li>Azure Container Registry</li>
    <li>Vercel</li>
  </ul>

  <h2>🏗️ Architecture</h2>

  <pre>
Frontend React App
        ↓
Streaming API Request
        ↓
FastAPI Backend
        ↓
LangChain + OpenAI
        ↓
Basketball AI Reasoning Engine
  </pre>

  <h2>📡 API Endpoints</h2>

  <ul>
    <li><strong>GET /</strong> - Root API status</li>
    <li><strong>GET /health</strong> - Health check</li>
    <li><strong>POST /basketballQuery</strong> - Standard basketball AI response</li>
    <li><strong>POST /basketballStream</strong> - Streaming basketball AI response</li>
  </ul>

  <h2>💬 Example Prompt</h2>

  <pre>
{
  "message": "Compare Kobe Bryant and Michael Jordan as scorers",
  "session_id": "abc123"
}
  </pre>

  <h2>📂 Project Structure</h2>

  <pre>
masshoops-ai/
│
├── masshoops-web/
├── charts/
├── chatbot.py
├── main.py
├── getData.py
├── requirements.txt
├── Dockerfile
└── README.md
  </pre>

  <h2>⚡ Local Development</h2>

  <h3>Backend</h3>

  <pre>
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python -m uvicorn main:app --reload --port 8000
  </pre>

  <h3>Frontend</h3>

  <pre>
cd masshoops-web
npm install
npm run dev
  </pre>

  <h2>📈 Future Improvements</h2>

  <ul>
    <li>AI personality modes</li>
    <li>Basketball RAG knowledge base</li>
    <li>Saved conversations</li>
    <li>User authentication</li>
    <li>Voice interaction</li>
    <li>AI scouting reports</li>
    <li>Advanced basketball analytics</li>
  </ul>

  <h2>👨‍💻 Author</h2>

  <p>
    Anthony Massaquoi<br />
    <a href="https://github.com/adotmdot">GitHub Profile</a>
  </p>

</body>
</html>
