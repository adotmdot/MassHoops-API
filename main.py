from fastapi import FastAPI, Request, HTTPException
from pydantic import BaseModel

from chatbot import CustomerChatbot, DatasetSpec
from getData import build_sql_database

# =========================

# App

# =========================

app = FastAPI(title="MassHoops API", version="1.0.0")

# =========================

# API Key

# =========================

API_KEY = "askhoops-demo"

def require_api_key(request: Request):
    if request.headers.get("x-api-key") != API_KEY:
        raise HTTPException(status_code=403, detail="Invalid API Key")

# =========================

# Chatbot Setup (REUSED)

# =========================

def build_dataset():
    return [
        DatasetSpec(
            key="basketball",
            display_name="Basketball Stats",
            description="NBA player stats",
            sql_database=build_sql_database(),
            allowed_objects=None
        )
    ]


chatbot = CustomerChatbot(build_dataset(), charts_dir="charts")

# =========================

# Models

# =========================

class QueryRequest(BaseModel):
    message: str
    session_id: str

# =========================

# Routes

# =========================

@app.get("/")
def root():
    return {"message": "MassHoops API is running"}

@app.post("/basketballQuery")
def basketball_query(payload: QueryRequest, request: Request):
    #require_api_key(request)

    response = chatbot.answer(
        session_id=payload.session_id,
        message=payload.message
    )
    return response
