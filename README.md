# 🏀 MassHoops AI

MassHoops AI is an AI-powered basketball analytics API that converts natural language questions into SQL queries and returns real data insights with optional chart visualizations.

---

## 🚀 Features

- Ask questions like:
  - "Who are the top scorers?"
  - "Show me a chart of points per team"
  - "Which team has the best record?"

- AI translates questions into SQL queries
- Returns structured results
- Generates charts (bar, pie, line)
- Session-based conversation memory

---

## 🧠 Tech Stack

- FastAPI (Backend API)
- LangChain (SQL Agent)
- OpenAI (LLM)
- SQLite (Database)
- Matplotlib (Charts)

---

## 📂 Project Structure
MassHoops-API/
│
├── main.py # API entry point
├── chatbot.py # AI + SQL agent logic
├── getData.py # Database connection
├── basketball.db # SQLite database
├── charts/ # Generated charts
└── README.md


---

## ⚙️ How It Works

1. User sends a question
2. AI converts it into SQL
3. SQL runs against basketball database
4. Results are returned
5. Optional: chart is generated

---

## 📌 Example Request

POST `/basketballQuery`

```json
{
  "message": "Show me top players by points",
  "session_id": "123"
}