import json
from typing import Any, Dict, List, Optional

import requests
from psycopg2.extensions import connection as PgConnection
from psycopg2.extras import Json

from config import settings, build_groq_headers
from chunking import search_similar, build_context_from_results

ConversationTurn = Dict[str, str]
ConversationHistory = List[ConversationTurn]


def create_conversation(conn: PgConnection) -> int:
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO conversation (history)
            VALUES (%s)
            RETURNING id;
            """,
            (Json([]),),
        )
        conversation_id = cur.fetchone()[0]
    return conversation_id


def get_conversation_history(
    conn: PgConnection, conversation_id: int
) -> ConversationHistory:
    with conn.cursor() as cur:
        cur.execute(
            "SELECT history FROM conversation WHERE id = %s;",
            (conversation_id,),
        )
        row = cur.fetchone()
    if not row:
        raise ValueError(f"Conversa {conversation_id} não encontrada.")
    history = row[0] or []
    return history


def save_conversation_history(
    conn: PgConnection, conversation_id: int, history: ConversationHistory
) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            UPDATE conversation
            SET history = %s
            WHERE id = %s;
            """,
            (Json(history), conversation_id),
        )


def answer_with_groq(
    question: str,
    context: str,
    conversation_history: Optional[ConversationHistory] = None,
    temperature: float = 0.2,
) -> str:
    headers = build_groq_headers()
    headers["Content-Type"] = "application/json"

    system_prompt = """
Você é um assistente conversacional especializado em interagir APENAS com base no contexto fornecido.
Se a resposta não estiver claramente contida nesse contexto, diga que não sabe com base nesse material.
Use o conteúdo para conduzir uma conversa fluida com o objetivo de identificar lacunas de conhecimento
do usuário sobre os temas do contexto.

Comece com perguntas mais fáceis e vá aumentando a complexidade quando perceber que o usuário domina o tema.
Não revele que está usando esse contexto como base de conhecimento.
Não dê aulas completas; seu foco é identificar lacunas, não ensinar tudo.
Responda em português do Brasil.
""".strip()

    if conversation_history:
        partes = []
        for i, turno in enumerate(conversation_history, start=1):
            partes.append(
                f"Turno {i}:\nUsuário: {turno['pergunta']}\nAssistente: {turno['resposta']}"
            )
        history_text = "\n\n".join(partes)
    else:
        history_text = "Nenhum histórico anterior. Esta é a primeira interação."

    user_content = (
        f"Histórico da conversa até agora:\n{history_text}\n\n"
        f"Contexto (única fonte de informação nesta rodada):\n{context}\n\n"
        f"Pergunta atual do usuário:\n{question}"
    )

    payload = {
        "model": settings.GROQ_CHAT_MODEL,
        "temperature": temperature,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ],
    }

    resp = requests.post(
        settings.GROQ_CHAT_COMPLETIONS_ENDPOINT,
        headers=headers,
        json=payload,
        timeout=120,
    )
    resp.raise_for_status()
    data = resp.json()
    return data["choices"][0]["message"]["content"].strip()

# cria conversa se não existir
# busca contexto RAG
# chama LLM
# atualiza histórico no banco
def chat_step(
    conn: PgConnection,
    conversation_id: Optional[int],
    question: str,
    top_k: int = 5,
) -> Dict[str, Any]:
    if conversation_id is None:
        conversation_id = create_conversation(conn)
        history: ConversationHistory = []
    else:
        history = get_conversation_history(conn, conversation_id)

    results = search_similar(conn, question, k=top_k)

    if not results:
        answer = (
            "Não encontrei nada relevante na base de conhecimento para responder à sua pergunta."
        )
    else:
        context = build_context_from_results(results)
        answer = answer_with_groq(
            question=question,
            context=context,
            conversation_history=history,
        )

    history.append({"pergunta": question, "resposta": answer})
    save_conversation_history(conn, conversation_id, history)

    return {
        "conversation_id": conversation_id,
        "answer": answer,
        "history": history,
    }
