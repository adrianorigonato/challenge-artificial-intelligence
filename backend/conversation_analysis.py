import json
from typing import Any, Dict, List, Optional

import requests
from psycopg2.extensions import connection as PgConnection
from psycopg2.extras import Json

from config import settings, build_groq_headers
from conversation import ConversationHistory


def analyze_conversation_with_groq(
    conversation_history: ConversationHistory,
    temperature: float = 0.1,
) -> List[Dict[str, Any]]:
    headers = build_groq_headers()
    headers["Content-Type"] = "application/json"

    system_prompt = '''
Você é um avaliador pedagógico.

Receberá o histórico de uma conversa entre um assistente e um aluno.
Seu objetivo é identificar os SUBTEMAS discutidos e avaliar o NÍVEL DE CONHECIMENTO do aluno em cada subtema.

Avalie o nível de domínio do aluno exclusivamente pelas respostas que ele dá às perguntas — considerando precisão, clareza e coerência. 
Ignore qualquer autodeclaração do aluno sobre ser bom ou ruim em um assunto.
Baseie-se apenas no desempenho real dele nas respostas.

Níveis possíveis (APENAS estes):
- "básico"
- "intermediário"
- "avançado"
- "domina"

Definição resumida:
- básico: contato superficial, muitos erros conceituais.
- intermediário: entende conceitos principais, mas com lacunas.
- avançado: domina bem, poucas lacunas.
- domina: domínio profundo, quase como especialista.

Retorne ESTRITAMENTE um JSON válido.
'''.strip()

    conversation_json = json.dumps(
        conversation_history,
        ensure_ascii=False,
        indent=2,
    )

    user_content = f"""
A seguir está o histórico da conversa em formato JSON com campos "pergunta" e "resposta":

{conversation_json}

Agora, produza um JSON no formato:

[
  {{
    "subtema": "nome do subtema",
    "nivel": "básico|intermediário|avançado|domina",
    "justificativa": "texto curto explicando por que você atribuiu esse nível"
  }}
]

Retorne APENAS o JSON.
""".strip()

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
    raw = data["choices"][0]["message"]["content"].strip()

    if raw.startswith("```"):
        raw = raw.strip("`")
        if raw.lower().startswith("json"):
            raw = raw[4:].strip()

    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        parsed = [
            {
                "subtema": "ANÁLISE_FALHOU",
                "nivel": "básico",
                "justificativa": (
                    "Não foi possível interpretar o JSON retornado pelo modelo. "
                    f"Conteúdo bruto: {raw[:500]}"
                ),
            }
        ]

    if isinstance(parsed, dict):
        parsed = [parsed]

    return parsed


def save_profile_information(
    conn: PgConnection,
    conversation_id: int,
    conversation_history: ConversationHistory,
    analysis: List[Dict[str, Any]],
    preferred_format: Optional[str] = None,
) -> int:
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO profile_information (
                conversation_id,
                prefered_format,
                raw_conversation,
                analysis
            )
            VALUES (%s, %s, %s, %s)
            RETURNING id;
            """,
            (
                conversation_id,
                preferred_format,
                Json(conversation_history),
                Json(analysis),
            ),
        )
        profile_id = cur.fetchone()[0]

    return profile_id
