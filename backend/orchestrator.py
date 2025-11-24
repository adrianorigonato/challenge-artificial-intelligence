import os
import json
from typing import Any, Dict, List, Optional

from psycopg2.extensions import connection as PgConnection

from .db import init_db
from .extract import (
    AUDIO_EXTS,
    VIDEO_EXTS,
    IMAGE_EXTS,
    extract_text_from_pdf,
    transcribe_audio_file,
    transcribe_video_file,
    describe_image_with_groq,
)
from .chunking import (
    split_text_into_chunks,
    embed_texts,
    insert_documents,
    is_already_ingested,
)
from .conversation import (
    chat_step,
    create_conversation,
    get_conversation_history,
)
from .conversation_analysis import (
    analyze_conversation_with_groq,
    save_profile_information,
)
from .content_generation import generate_personalized_contents


# ==========================
# INGESTÃO DE ARQUIVOS
# ==========================
def ingest_file(
    conn: PgConnection,
    file_path: str,
    title: Optional[str] = None,
) -> Dict[str, Any]:

    init_db(conn)

    ext = os.path.splitext(file_path)[1].lower()
    base_name = os.path.basename(file_path)

    media_metadata: Dict[str, Any]
    doc_type: str

    # ==========================
    # PDF
    # ==========================
    if ext == ".pdf":
        doc_type = "pdf"
        media_metadata = {
            "source": base_name,
            "title": title,
            "type": "pdf",
            "original_format": "pdf",
        }

        if is_already_ingested(conn, base_name, doc_type):
            return {
                "skipped": True,
                "reason": "already_ingested",
                "inserted_chunks": 0,
                "metadata": media_metadata,
            }

        full_text = extract_text_from_pdf(file_path)

    # ==========================
    # TXT
    # ==========================
    elif ext == ".txt":
        doc_type = "text"
        media_metadata = {
            "source": base_name,
            "title": title,
            "type": "text",
            "original_format": "txt",
        }

        if is_already_ingested(conn, base_name, doc_type):
            return {
                "skipped": True,
                "reason": "already_ingested",
                "inserted_chunks": 0,
                "metadata": media_metadata,
            }

        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            full_text = f.read()

    # ==========================
    # JSON
    # ==========================
    elif ext == ".json":
        doc_type = "json"
        media_metadata = {
            "source": base_name,
            "title": title,
            "type": "json",
            "original_format": "json",
        }

        if is_already_ingested(conn, base_name, doc_type):
            return {
                "skipped": True,
                "reason": "already_ingested",
                "inserted_chunks": 0,
                "metadata": media_metadata,
            }

        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            try:
                data = json.load(f)
                # Deixa o JSON “bonitinho” como texto para ser embeddado
                full_text = json.dumps(data, ensure_ascii=False, indent=2)
            except json.JSONDecodeError:
                # Se não for um JSON válido, trata como texto puro
                f.seek(0)
                full_text = f.read()

    # ==========================
    # ÁUDIO
    # ==========================
    elif ext in AUDIO_EXTS:
        doc_type = "audio"
        media_metadata = {
            "source": base_name,
            "title": title,
            "type": "audio",
            "original_format": ext.lstrip("."),
        }

        if is_already_ingested(conn, base_name, doc_type):
            return {
                "skipped": True,
                "reason": "already_ingested",
                "inserted_chunks": 0,
                "metadata": media_metadata,
            }

        full_text = transcribe_audio_file(file_path)

    # ==========================
    # VÍDEO
    # ==========================
    elif ext in VIDEO_EXTS:
        doc_type = "video"
        media_metadata = {
            "source": base_name,
            "title": title,
            "type": "video",
            "original_format": ext.lstrip("."),
        }

        if is_already_ingested(conn, base_name, doc_type):
            return {
                "skipped": True,
                "reason": "already_ingested",
                "inserted_chunks": 0,
                "metadata": media_metadata,
            }

        full_text = transcribe_video_file(file_path)

    # ==========================
    # IMAGEM
    # ==========================
    elif ext in IMAGE_EXTS:
        doc_type = "image"
        file_size_bytes = os.path.getsize(file_path)

        media_metadata = {
            "source": base_name,
            "title": title,
            "type": "image",
            "original_format": ext.lstrip("."),
            "file_size_bytes": file_size_bytes,
        }

        if is_already_ingested(conn, base_name, doc_type):
            return {
                "skipped": True,
                "reason": "already_ingested",
                "inserted_chunks": 0,
                "metadata": media_metadata,
            }

        full_text = describe_image_with_groq(file_path, language="pt")

    else:
        raise ValueError(f"Extensão de arquivo não suportada para ingestão: {ext}")

    # ==========================
    # CHUNKING
    # ==========================
    full_text = (full_text or "").strip()
    if not full_text:
        return {
            "skipped": True,
            "reason": "no_text_extracted",
            "inserted_chunks": 0,
            "metadata": media_metadata,
        }

    chunks = split_text_into_chunks(full_text)
    if not chunks:
        return {
            "skipped": True,
            "reason": "no_chunks_generated",
            "inserted_chunks": 0,
            "metadata": media_metadata,
        }

    # ==========================
    # EMBEDDINGS + INSERT
    # ==========================
    embeddings = embed_texts(chunks)
    inserted = insert_documents(
        conn,
        chunks,
        embeddings,
        base_metadata=media_metadata,
    )

    return {
        "skipped": False,
        "reason": None,
        "inserted_chunks": inserted,
        "metadata": media_metadata,
    }


# ==========================
# CONVERSATION
# ==========================
def start_conversation(conn: PgConnection) -> int:
    
    init_db(conn)
    conversation_id = create_conversation(conn)
    return conversation_id


def handle_chat_message(
    conn: PgConnection,
    conversation_id: Optional[int],
    message: str,
    top_k: int = 5,
) -> Dict[str, Any]:
    
    init_db(conn)

    result = chat_step(
        conn=conn,
        conversation_id=conversation_id,
        question=message,
        top_k=top_k,
    )
    return result


# ==========================
# ANÁLISE E CRIAÇÃO DE CONTEÚDOS
# ==========================
def analyze_and_generate(
    conn: PgConnection,
    conversation_id: int,
    preferred_format: Optional[str] = None,
) -> Dict[str, Any]:
    
    init_db(conn)

    history = get_conversation_history(conn, conversation_id)
    if not history:
        raise ValueError("Nenhum histórico encontrado para esta conversa.")

    # 2) Análise pedagógica (Groq)
    analysis = analyze_conversation_with_groq(history)

    # 3) Salvar análise em profile_information
    analysis_id = save_profile_information(
        conn=conn,
        conversation_id=conversation_id,
        conversation_history=history,
        analysis=analysis,
        preferred_format=preferred_format,
    )

    # 4) Geração de conteúdos personalizados
    contents = generate_personalized_contents(
        conn=conn,
        conversation_id=conversation_id,
        analysis_id=analysis_id,
        analysis=analysis,
        preferred_format=preferred_format,
    )

    return {
        "analysis": analysis,
        "contents": contents,
    }
