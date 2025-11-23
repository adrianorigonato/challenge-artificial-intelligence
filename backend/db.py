from typing import Optional

import psycopg2
from psycopg2.extensions import connection as PgConnection

from config import settings

# conexao postgres
def get_connection() -> PgConnection:
    conn = psycopg2.connect(settings.DATABASE_URL)
    conn.autocommit = True
    return conn

# config banco
def init_db(conn: Optional[PgConnection] = None) -> None:
    close_after = False
    if conn is None:
        conn = get_connection()
        close_after = True

    try:
        with conn.cursor() as cur:
            # Extensão para vetores
            cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")

            # Tabela de documentos embeddados
            cur.execute(
                f"""
                CREATE TABLE IF NOT EXISTS documents (
                    id BIGSERIAL PRIMARY KEY,
                    content TEXT,
                    metadata JSONB,
                    embedding VECTOR({settings.EMBEDDING_DIM})
                );
                """
            )

            # Índice vetorial (opcional, mas recomendado)
            cur.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_documents_embedding
                ON documents
                USING ivfflat (embedding vector_l2_ops)
                WITH (lists = 100);
                """
            )

            # Histórico de conversa
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS conversation (
                    id BIGSERIAL PRIMARY KEY,
                    history JSONB NOT NULL DEFAULT '[]'::jsonb,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                );
                """
            )

            # Análise de perfil / lacunas (uma linha por conversa analisada)
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS profile_information (
                    id BIGSERIAL PRIMARY KEY,
                    conversation_id BIGINT REFERENCES conversation(id) ON DELETE CASCADE,
                    prefered_format TEXT,
                    raw_conversation JSONB,
                    analysis JSONB,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                );
                """
            )

            # Conteúdos personalizados gerados
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS personalized_learning_contents (
                    id BIGSERIAL PRIMARY KEY,
                    conversation_id BIGINT REFERENCES conversation(id) ON DELETE CASCADE,
                    analysis_id BIGINT REFERENCES profile_information(id) ON DELETE CASCADE,
                    subtema TEXT,
                    nivel TEXT,
                    content_type TEXT,
                    title TEXT,
                    script TEXT,
                    extra_metadata JSONB,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                );
                """
            )

    finally:
        if close_after:
            conn.close()
