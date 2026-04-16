"""
main.py — FastAPI app principal
Endpoints:
  POST /chat          → conversación con el chatbot
  GET  /health        → healthcheck para Docker
"""

import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

from app.tools.bookly import close_pool
from app.chat import chat

load_dotenv()

# ---------------------------------------------------------------------------
# Lifespan
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    await close_pool()  # Cierra pool MySQL al apagar


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Nomadas Surf Park — Chatbot API",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("ALLOWED_ORIGINS", "https://nomadassurfpark.com").split(","),
    allow_credentials=True,
    allow_methods=["POST", "GET"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Modelos
# ---------------------------------------------------------------------------

class Message(BaseModel):
    role: str    # "user" | "assistant"
    content: str

class ChatRequest(BaseModel):
    messages: list[Message]  # Historial completo de la conversación

class ChatResponse(BaseModel):
    reply: str

# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    if not request.messages:
        raise HTTPException(status_code=400, detail="messages no puede estar vacío")

    # Validar roles
    for msg in request.messages:
        if msg.role not in ("user", "assistant"):
            raise HTTPException(status_code=400, detail=f"Rol inválido: {msg.role}")

    # El último mensaje debe ser del usuario
    if request.messages[-1].role != "user":
        raise HTTPException(status_code=400, detail="El último mensaje debe ser del usuario")

    try:
        messages_dict = [{"role": m.role, "content": m.content} for m in request.messages]
        reply = await chat(messages_dict)
        return ChatResponse(reply=reply)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
