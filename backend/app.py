import os
import shutil
import tempfile
from pathlib import Path
from typing import Any, Dict, Optional

from fastapi import Depends, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel

from db import get_connection, init_db
from orchestrator import (
    analyze_and_generate,
    handle_chat_message,
    ingest_file,
    start_conversation,
)

app = FastAPI(title="RAG Learning Web")


# ==========================
# CONEXÃO COM O BANCO
# ==========================

def get_db():
    conn = get_connection()
    try:
        yield conn
    finally:
        conn.close()


@app.on_event("startup")
def on_startup() -> None:
    """
    Inicializa o schema do banco ao subir a API.
    """
    conn = get_connection()
    try:
        init_db(conn)
    finally:
        conn.close()


# ==========================
# MODELOS Pydantic
# ==========================

class ChatRequest(BaseModel):
    message: str
    top_k: int = 5
    conversation_id: Optional[int] = None


class ChatResponse(BaseModel):
    conversation_id: int
    answer: str
    history: list[dict]


class AnalyzeRequest(BaseModel):
    preferred_format: Optional[str] = None  # "video" | "audio" | "texto" | None


# ==========================
# ROTAS API
# ==========================

@app.post("/api/ingest")
async def api_ingest(
    file: UploadFile = File(...),
    title: Optional[str] = Form(None),
    conn=Depends(get_db),
):
    """
    Recebe um arquivo (PDF, áudio, vídeo ou imagem), faz ingestão
    e salva os chunks + embeddings na tabela 'documents'.
    """
    suffix = os.path.splitext(file.filename)[1]
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        shutil.copyfileobj(file.file, tmp)
        tmp_path = tmp.name

    try:
        result = ingest_file(conn, tmp_path, title or file.filename)
        return result
    finally:
        try:
            os.remove(tmp_path)
        except FileNotFoundError:
            pass


@app.post("/api/conversation/start")
def api_start_conversation(conn=Depends(get_db)) -> Dict[str, int]:
    """
    Cria uma nova conversa vazia e devolve o id.
    (No front, isso é chamado de forma transparente na 1ª mensagem.)
    """
    conversation_id = start_conversation(conn)
    return {"conversation_id": conversation_id}


@app.post("/api/conversation/chat", response_model=ChatResponse)
def api_chat(
    body: ChatRequest,
    conn=Depends(get_db),
):
    """
    Envia uma mensagem do usuário para o bot RAG.
    Se conversation_id for None, o orchestrator cria uma conversa nova.
    """
    result = handle_chat_message(
        conn=conn,
        conversation_id=body.conversation_id,
        message=body.message,
        top_k=body.top_k,
    )
    return ChatResponse(**result)


@app.post("/api/conversation/{conversation_id}/analyze-and-generate")
def api_analyze(
    conversation_id: int,
    body: AnalyzeRequest,
    conn=Depends(get_db),
):
    """
    Dispara análise da conversa + geração de conteúdos personalizados
    (usando modelo da Groq).
    """
    try:
        result = analyze_and_generate(
            conn=conn,
            conversation_id=conversation_id,
            preferred_format=body.preferred_format,
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ==========================
# SERVIR FRONTEND (pasta /frontend)
# ==========================

BASE_DIR = Path(__file__).resolve().parent.parent
FRONTEND_DIR = BASE_DIR / "frontend"
INDEX_FILE = FRONTEND_DIR / "index.html"
MAIN_JS_FILE = FRONTEND_DIR / "main.js"


@app.get("/", response_class=FileResponse)
def index() -> FileResponse:
    """
    Retorna o arquivo frontend/index.html.
    """
    if not INDEX_FILE.exists():
        raise HTTPException(
            status_code=500,
            detail="Arquivo frontend/index.html não encontrado.",
        )
    return FileResponse(str(INDEX_FILE))


@app.get("/main.js", response_class=FileResponse)
def main_js() -> FileResponse:
    """
    Retorna o arquivo frontend/main.js.
    """
    if not MAIN_JS_FILE.exists():
        raise HTTPException(
            status_code=500,
            detail="Arquivo frontend/main.js não encontrado.",
        )
    return FileResponse(str(MAIN_JS_FILE))
