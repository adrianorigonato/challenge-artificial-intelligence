import json
import re
from typing import Any, Dict, List, Optional

import requests
from psycopg2.extensions import connection as PgConnection

from config import settings, build_openrouter_headers

#Divide um texto em chunks, com overlap de parágrafos.
def split_text_into_chunks(
    text: str,
    min_words: int = 200,
    max_words: int = 400,
    overlap_paragraphs: int = 1,
) -> List[str]:

    if not text:
        return []

    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = text.strip()
    if not text:
        return []

    def count_words(s: str) -> int:
        return len(s.split())

    raw_paragraphs = text.split("\n\n")
    paragraphs = [p.strip() for p in raw_paragraphs if p.strip()]

    if len(paragraphs) > 1:
        units = paragraphs
        joiner = "\n\n"
    else:
        raw_sentences = re.split(r"(?<=[.!?])\s+", text)
        units = [s.strip() for s in raw_sentences if s.strip()]
        joiner = " "
        if not units:
            return []

    chunks: List[str] = []
    current_units: List[str] = []
    current_words = 0

    def finalize_chunk() -> None:
        nonlocal current_units, current_words
        if not current_units:
            return
        chunk_text = joiner.join(current_units)
        chunks.append(chunk_text)

        if overlap_paragraphs > 0:
            overlap = current_units[-overlap_paragraphs:]
            current_units = overlap.copy()
            current_words = count_words(joiner.join(current_units))
        else:
            current_units = []
            current_words = 0

    for unit in units:
        unit_words = count_words(unit)

        if not current_units:
            current_units.append(unit)
            current_words = unit_words
            continue

        if current_words + unit_words <= max_words:
            current_units.append(unit)
            current_words += unit_words
            continue

        if current_words < min_words:
            current_units.append(unit)
            current_words += unit_words
            finalize_chunk()
            continue

        finalize_chunk()
        current_units.append(unit)
        current_words = unit_words

    if current_units:
        finalize_chunk()

    return chunks

#embedding openrouter
def _openrouter_embed_request(inputs: List[str]) -> List[List[float]]:
    headers = build_openrouter_headers("rag-learning-web-embeddings")
    payload = {
        "model": settings.EMBEDDING_MODEL_NAME,
        "input": inputs,
    }

    resp = requests.post(
        "https://openrouter.ai/api/v1/embeddings",
        headers=headers,
        json=payload,
        timeout=60,
    )
    resp.raise_for_status()
    data = resp.json()
    return [item["embedding"] for item in data["data"]]


def embed_texts(texts: List[str]) -> List[List[float]]:
    return _openrouter_embed_request(texts)


def embedding_to_pgvector_str(embedding: List[float]) -> str:
    return "[" + ",".join(f"{x:.6f}" for x in embedding) + "]"

#insert chunks
def insert_documents(
    conn: PgConnection,
    chunks: List[str],
    embeddings: List[List[float]],
    base_metadata: Optional[dict] = None,
) -> int:
    if len(chunks) != len(embeddings):
        raise ValueError("chunks e embeddings precisam ter o mesmo tamanho.")

    inserted = 0
    with conn.cursor() as cur:
        for content, emb in zip(chunks, embeddings):
            vector_str = embedding_to_pgvector_str(emb)
            metadata_json = json.dumps(base_metadata) if base_metadata else None
            cur.execute(
                """
                INSERT INTO documents (content, metadata, embedding)
                VALUES (%s, %s, %s::vector);
                """,
                (content, metadata_json, vector_str),
            )
            inserted += 1

    return inserted

# validação para não inserir dados duplicados
def is_already_ingested(conn: PgConnection, source: str, doc_type: str) -> bool:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT 1
            FROM documents
            WHERE metadata->>'source' = %s
              AND metadata->>'type' = %s
            LIMIT 1;
            """,
            (source, doc_type),
        )
        return cur.fetchone() is not None

#busca vetorial
def search_similar(
    conn: PgConnection, query: str, k: int = 5
) -> List[Dict[str, Any]]:
    query_emb = embed_texts([query])[0]
    vector_str = embedding_to_pgvector_str(query_emb)

    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT id, content, metadata, (embedding <-> %s::vector) AS distance
            FROM documents
            ORDER BY embedding <-> %s::vector
            LIMIT %s;
            """,
            (vector_str, vector_str, k),
        )
        rows = cur.fetchall()

    results: List[Dict[str, Any]] = []
    for row in rows:
        doc_id, content, metadata, distance = row
        results.append(
            {
                "id": doc_id,
                "content": content,
                "metadata": metadata,
                "distance": float(distance),
            }
        )
    return results

# contexto rag
def build_context_from_results(results: List[Dict[str, Any]]) -> str:

    if not results:
        return "Nenhum trecho relevante foi encontrado na base de conhecimento."

    partes: List[str] = []
    for i, r in enumerate(results, start=1):
        metadata = r.get("metadata") or {}
        if isinstance(metadata, str):
            try:
                metadata = json.loads(metadata)
            except json.JSONDecodeError:
                metadata = {}

        source = metadata.get("source", "")
        title = metadata.get("title", "")
        doc_type = metadata.get("type", "")

        header_parts = [f"Trecho {i}"]
        if title:
            header_parts.append(f"título: {title}")
        if source:
            header_parts.append(f"fonte: {source}")
        if doc_type:
            header_parts.append(f"tipo: {doc_type}")

        header = " | ".join(header_parts)
        partes.append(f"{header}\n{r['content']}")

    return "\n\n" + ("\n" + "-" * 80 + "\n\n").join(partes)
