import os
from typing import Set


class Settings:
    def __init__(self) -> None:
        # Banco
        self.DATABASE_URL: str = os.getenv(
            "DATABASE_URL"
        )

        # OpenRouter
        self.OPENROUTER_API_KEY: str = os.getenv("OPENROUTER_API_KEY", "")
        self.OPENROUTER_SITE_URL: str = os.getenv("OPENROUTER_SITE_URL", "")
        self.OPENROUTER_APP_NAME: str = os.getenv(
            "OPENROUTER_APP_NAME",
            "rag-learning-web",
        )

        # Modelos de embedding
        self.EMBEDDING_MODEL_NAME: str = os.getenv(
            "EMBEDDING_MODEL_NAME",
            "openai/text-embedding-3-small",
        )
        self.EMBEDDING_DIM: int = int(os.getenv("EMBEDDING_DIM", "1536"))

        # Groq
        self.GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
        self.TRANSCRIPTION_MODEL_NAME: str = os.getenv(
            "TRANSCRIPTION_MODEL_NAME",
            "whisper-large-v3-turbo",
        )
        self.GROQ_TRANSCRIPTION_ENDPOINT: str = os.getenv(
            "GROQ_TRANSCRIPTION_ENDPOINT",
            "https://api.groq.com/openai/v1/audio/transcriptions",
        )

        self.VISION_MODEL_NAME: str = os.getenv(
            "VISION_MODEL_NAME",
            "meta-llama/llama-4-maverick-17b-128e-instruct",
        )
        self.GROQ_CHAT_COMPLETIONS_ENDPOINT: str = os.getenv(
            "GROQ_CHAT_COMPLETIONS_ENDPOINT",
            "https://api.groq.com/openai/v1/chat/completions",
        )

        self.GROQ_CHAT_MODEL: str = os.getenv(
            "GROQ_CHAT_MODEL",
            "openai/gpt-oss-120b",
        )

        self.LEARNING_CONTENT_MODEL: str = "llama-3.3-70b-versatile"


settings = Settings()

AUDIO_EXTS: Set[str] = {".wav", ".mp3"}
VIDEO_EXTS: Set[str] = {".mp4", ".mpeg", ".mov", ".webm"}
IMAGE_EXTS: Set[str] = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif", ".tiff"}


def build_openrouter_headers(app_name: str | None = None) -> dict:
    headers = {
        "Authorization": f"Bearer {settings.OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
    }

    if settings.OPENROUTER_SITE_URL:
        headers["HTTP-Referer"] = settings.OPENROUTER_SITE_URL

    title = app_name or settings.OPENROUTER_APP_NAME
    if title:
        headers["X-Title"] = title

    return headers


def build_groq_headers() -> dict:
    return {
        "Authorization": f"Bearer {settings.GROQ_API_KEY}",
    }
