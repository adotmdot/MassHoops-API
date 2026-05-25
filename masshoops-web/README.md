# 🏀 MassHoops AI

MassHoops AI is an AI-powered basketball assistant built with FastAPI, React, OpenAI, and LangChain.

The platform allows users to ask basketball-related questions and receive intelligent AI-generated responses about:

- NBA history
- Player comparisons
- Basketball strategy
- Team building
- Coaching concepts
- Analytics discussions
- Basketball debates
- Basketball knowledge

MassHoops AI was designed to simulate a modern AI assistant experience similar to ChatGPT or Copilot, but focused entirely on basketball.

---

# 🚀 Live Demo

Frontend:
https://masshoops-ai.vercel.app

Backend API:
https://masshoops-api.nicebush-7fc1af01.eastus.azurecontainerapps.io

Swagger Docs:
https://masshoops-api.nicebush-7fc1af01.eastus.azurecontainerapps.io/docs

---

# 🧠 Features

## AI Basketball Assistant
Ask natural language basketball questions such as:

- "Who is the greatest basketball player ever?"
- "Explain why Steph Curry changed basketball"
- "Compare Kobe Bryant vs Michael Jordan"
- "Explain pick and roll defense"
- "Build the perfect NBA starting five"

---

## Modern AI Chat UI
- ChatGPT-inspired interface
- Typing indicators
- Responsive mobile layout
- Suggested prompts
- Markdown rendering
- Dark mode design

---

## Data Visualization
MassHoops AI supports dynamic basketball charts and visualizations using:

- Pandas
- Matplotlib

---

## FastAPI Backend
- REST API architecture
- Health check endpoints
- AI response handling
- Error handling
- Chart generation support

---

## Cloud Deployment
Frontend:
- Vercel

Backend:
- Azure Container Apps

Containerization:
- Docker

---

# 🛠️ Tech Stack

## Frontend
- React
- Vite
- Axios
- React Markdown

## Backend
- FastAPI
- Python
- LangChain
- OpenAI API
- SQLAlchemy

## Data & Visualization
- Pandas
- Matplotlib

## Deployment
- Docker
- Azure Container Apps
- Vercel

---

# 📂 Project Structure

```bash
masshoops-ai/
│
├── masshoops-web/        # React frontend
├── charts/               # Generated chart images
├── chatbot.py            # AI chatbot logic
├── main.py               # FastAPI backend
├── getData.py            # Database utilities
├── requirements.txt
├── Dockerfile
└── README.md
```

---

# ⚡ Local Development

## Backend Setup

Create virtual environment:

```bash
python -m venv .venv
```

Activate virtual environment:

### Windows
```bash
.venv\Scripts\activate
```

### Mac/Linux
```bash
source .venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Run backend:

```bash
python -m uvicorn main:app --reload --port 8000
```

Backend runs at:

```bash
http://127.0.0.1:8000
```

---

## Frontend Setup

Navigate to frontend:

```bash
cd masshoops-web
```

Install dependencies:

```bash
npm install
```

Run frontend:

```bash
npm run dev
```

Frontend runs at:

```bash
http://localhost:5173
```

---

# 📡 API Endpoints

## Root
```http
GET /
```

## Health Check
```http
GET /health
```

## Basketball Query
```http
POST /basketballQuery
```

Example request:

```json
{
  "message": "Explain triangle offense",
  "session_id": "abc123"
}
```

---

# 📈 Future Improvements

Planned features include:

- Streaming AI responses
- User authentication
- Saved conversations
- Basketball knowledge base (RAG)
- Voice interaction
- AI coach/scout personalities
- Advanced analytics visualizations

---

# 👨‍💻 Author

Anthony Massaquoi

GitHub:
https://github.com/adotmdot

---

# 📜 License

This project is for educational and portfolio purposes.