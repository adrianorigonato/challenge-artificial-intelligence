import json
from typing import Any, Dict, List, Optional

import requests
from psycopg2.extensions import connection as PgConnection
from psycopg2.extras import Json

from config import settings, build_groq_headers
from chunking import search_similar, build_context_from_results


def generate_learning_script_with_groq(
    subtema: str,
    nivel: str,
    content_type: str,
    context: str,
    justificativa: str = "",
) -> Dict[str, str]:
    headers = build_groq_headers()
    headers["Content-Type"] = "application/json"

    # Mapeamento de tipo
    tipo_map = {
        "video": "roteiro de vídeo curto explicativo",
        "audio": "roteiro de áudio/podcast curto",
        "texto": "texto explicativo curto",
    }
    tipo_legivel = tipo_map.get(content_type.lower(), "texto explicativo curto")

    system_prompt = """
Você é um especialista em educação e criação de conteúdos didáticos personalizados.

Seu trabalho:
- Criar um conteúdo focado em sanar dificuldades do aluno em um subtema específico.
- Usar APENAS o contexto fornecido (trechos da base de documentos).
- NÃO inventar fatos fora desse contexto.
- Ser claro, objetivo e em português do Brasil.

Formato de saída:
- Retorne ESTRITAMENTE um JSON válido com:
  {
    "title": "título curto e claro",
    "script": "roteiro ou texto completo"
  }
""".strip()

    user_content = f"""
Subtema: {subtema}
Nível atual do aluno (segundo análise): {nivel}

Tipo de conteúdo desejado: {tipo_legivel}

Justificativa/resumo das dificuldades do aluno:
{justificativa or "(sem justificativa detalhada fornecida)"}

Contexto (trechos da base de conhecimento) – USE APENAS ESTA FONTE:
{context}

Tarefa:
- Gere um conteúdo no formato especificado, explicando o subtema de forma acessível ao nível do aluno.
- Ajude o aluno a avançar, mas sem ser superficial.
- Use exemplos simples quando fizer sentido.
- Adote um tom amigável e motivador.

IMPORTANTE:
- Saída ESTRITAMENTE em JSON com os campos "title" e "script".
- Não inclua comentários, markdown ou texto fora do JSON.
""".strip()

    payload = {
        "model": settings.LEARNING_CONTENT_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ],
        "temperature": 0.5,
    }

    resp = requests.post(
        settings.GROQ_CHAT_COMPLETIONS_ENDPOINT,
        headers=headers,
        json=payload,
        timeout=120,
    )
    resp.raise_for_status()
    data = resp.json()
    raw = data["choices"][0]["message"]["content"].strip()

    # Caso venha em bloco ```json ... ```
    if raw.startswith("```"):
        raw = raw.strip("`")
        if raw.lower().startswith("json"):
            raw = raw[4:].strip()

    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        # fallback: se não veio JSON, usa o texto bruto como script
        return {
            "title": f"Conteúdo sobre {subtema}",
            "script": raw,
        }

    title = parsed.get("title") or f"Conteúdo sobre {subtema}"
    script = parsed.get("script") or ""

    return {"title": title, "script": script}


def save_personalized_content(
    conn: PgConnection,
    conversation_id: int,
    analysis_id: int,
    subtema: str,
    nivel: str,
    content_type: str,
    title: str,
    script: str,
    extra_metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO personalized_learning_contents (
                conversation_id,
                analysis_id,
                subtema,
                nivel,
                content_type,
                title,
                script,
                extra_metadata
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id;
            """,
            (
                conversation_id,
                analysis_id,
                subtema,
                nivel,
                content_type,
                title,
                script,
                Json(extra_metadata or {}),
            ),
        )
        content_id = cur.fetchone()[0]

    return {
        "id": content_id,
        "conversation_id": conversation_id,
        "analysis_id": analysis_id,
        "subtema": subtema,
        "nivel": nivel,
        "content_type": content_type,
        "title": title,
        "script": script,
        "extra_metadata": extra_metadata or {},
    }


def generate_personalized_contents(
    conn: PgConnection,
    conversation_id: int,
    analysis_id: int,
    analysis: List[Dict[str, Any]],
    top_k_docs: int = 8,
    preferred_format: Optional[str] = None,
) -> List[Dict[str, Any]]:
    nivel_rank_map = {
        "básico": 1,
        "basico": 1,
        "intermediário": 2,
        "intermediario": 2,
        "avançado": 3,
        "avancado": 3,
        "domina": 4,
    }

    ranks: List[int] = []
    for item in analysis:
        nivel_raw = (item.get("nivel") or "").strip().lower()
        rank = nivel_rank_map.get(nivel_raw)
        if rank is not None:
            ranks.append(rank)

    if not ranks:
        return []

    min_rank = min(ranks)

    generated: List[Dict[str, Any]] = []

    for item in analysis:
        subtema = (item.get("subtema") or "").strip()
        nivel_raw = (item.get("nivel") or "").strip()
        nivel_key = nivel_raw.lower()
        justificativa = (item.get("justificativa") or "").strip()

        if not subtema or not nivel_raw:
            continue
        
        # só níveis de maior dificuldade
        rank = nivel_rank_map.get(nivel_key)
        if rank is None or rank != min_rank:
            continue 

        # Busca vetorial pelos docs mais relevantes do subtema
        results = search_similar(conn, query=subtema, k=top_k_docs)
        if not results:
            continue

        context = build_context_from_results(results)
        source_doc_ids = [r["id"] for r in results]

        if preferred_format in {"video", "audio", "texto"}:
            content_types = [preferred_format]
        else:
            content_types = ["video", "audio", "texto"]

        for content_type in content_types:
            gen = generate_learning_script_with_groq(
                subtema=subtema,
                nivel=nivel_raw,
                content_type=content_type,
                context=context,
                justificativa=justificativa,
            )

            extra_metadata = {
                "justificativa": justificativa,
                "source_doc_ids": source_doc_ids,
                "num_trechos_contexto": len(results),
                "nivel_rank_usado": rank,
                "criterio_geracao": "apenas níveis de maior dificuldade na análise",
            }

            saved = save_personalized_content(
                conn=conn,
                conversation_id=conversation_id,
                analysis_id=analysis_id,
                subtema=subtema,
                nivel=nivel_raw,
                content_type=content_type,
                title=gen["title"],
                script=gen["script"],
                extra_metadata=extra_metadata,
            )
            generated.append(saved)

    return generated
