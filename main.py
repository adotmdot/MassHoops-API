from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import StreamingResponse

from pydantic import BaseModel

from chatbot import (
    CustomerChatbot,
    DatasetSpec,
)

from getData import build_sql_database

import traceback

# =====================================================
# APP SETUP
# =====================================================

app = FastAPI(
    title="MassHoops AI API",
    version="2.0.0",
    description=(
        "MassHoops AI is an AI-powered basketball assistant."
    ),
)

# =====================================================
# STATIC FILES
# =====================================================

app.mount(
    "/charts",
    StaticFiles(directory="charts"),
    name="charts",
)

# =====================================================
# CORS
# =====================================================

app.add_middleware(
    CORSMiddleware,

    allow_origins=["*"],

    allow_credentials=True,

    allow_methods=["*"],

    allow_headers=["*"],
)

# =====================================================
# API KEY
# =====================================================

API_KEY = "masshoops-demo-key"

def require_api_key(request: Request):

    incoming_key = request.headers.get(
        "x-api-key"
    )

    if incoming_key != API_KEY:

        raise HTTPException(
            status_code=403,
            detail="Invalid API key.",
        )

# =====================================================
# DATASETS
# =====================================================

def build_datasets():

    return [

        DatasetSpec(
            key="basketball",

            display_name=(
                "Basketball Knowledge Base"
            ),

            description=(
                "Basketball analytics and AI assistant."
            ),

            sql_database=build_sql_database(),

            allowed_objects=None,
        )
    ]

# =====================================================
# CHATBOT
# =====================================================

chatbot = CustomerChatbot(
    build_datasets(),
    charts_dir="charts",
)

# =====================================================
# REQUEST MODEL
# =====================================================

class QueryRequest(BaseModel):

    message: str
    session_id: str

# =====================================================
# ROOT
# =====================================================

@app.get("/")
def root():

    return {
        "name": "MassHoops AI API",
        "status": "running",
        "version": "2.0.0",
    }

# =====================================================
# HEALTH
# =====================================================

@app.get("/health")
def health():

    return {
        "status": "healthy"
    }

# =====================================================
# NORMAL CHAT ENDPOINT
# =====================================================

@app.post("/basketballQuery")
def basketball_query(
    payload: QueryRequest,
    request: Request,
):

    try:

        response = chatbot.answer(
            session_id=payload.session_id,
            message=payload.message,
        )

        return response

    except Exception as e:

        print("\n[ERROR]")
        print(str(e))

        traceback.print_exc()

        return {
            "reply": (
                "MassHoops AI encountered an error."
            ),
            "vega_spec": None,
            "chart_url": None,
        }

# =====================================================
# STREAMING ENDPOINT
# =====================================================

@app.post("/basketballStream")
async def basketball_stream(
    payload: QueryRequest,
):

    async def generate():

        async for chunk in chatbot.stream_answer(
            session_id=payload.session_id,
            message=payload.message,
        ):

            yield chunk

    return StreamingResponse(
        generate(),
        media_type="text/plain",
    )

# =====================================================
# TEST
# =====================================================

@app.get("/test")
def test():

    return {
        "message": (
            "MassHoops AI backend is working."
        )
    }