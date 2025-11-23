import base64
import os
from typing import Dict, Optional, Tuple

import pdfplumber
import requests

from config import (
    AUDIO_EXTS,
    IMAGE_EXTS,
    VIDEO_EXTS,
    settings,
    build_groq_headers,
)


def extract_text_from_pdf(pdf_path: str) -> str:
    all_text: list[str] = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            text = page.extract_text() or ""
            all_text.append(text)
    return "\n\n".join(all_text)


def _guess_image_mime_type(ext: str) -> str:
    ext = ext.lower()
    if ext in {".jpg", ".jpeg"}:
        return "image/jpeg"
    if ext == ".png":
        return "image/png"
    if ext == ".webp":
        return "image/webp"
    if ext == ".gif":
        return "image/gif"
    if ext in {".bmp"}:
        return "image/bmp"
    if ext in {".tif", ".tiff"}:
        return "image/tiff"
    return "image/jpeg"

#transcrição de audio e video
def _transcribe_with_groq(file_path: str, language: str = "pt") -> str:
    headers = build_groq_headers()

    with open(file_path, "rb") as f:
        files = {
            "file": (os.path.basename(file_path), f),
        }
        data = {
            "model": settings.TRANSCRIPTION_MODEL_NAME,
            "temperature": 0,
            "response_format": "json",
            "language": language,
        }
        resp = requests.post(
            settings.GROQ_TRANSCRIPTION_ENDPOINT,
            headers=headers,
            files=files,
            data=data,
            timeout=600,
        )

    resp.raise_for_status()
    out = resp.json()
    text = out.get("text", "") or ""
    return text.strip()


def transcribe_audio_file(file_path: str) -> str:
    return _transcribe_with_groq(file_path, language="pt")


def transcribe_video_file(file_path: str) -> str:
    return _transcribe_with_groq(file_path, language="pt")


def describe_image_with_groq(file_path: str, language: str = "pt") -> str:
    ext = os.path.splitext(file_path)[1].lower()
    mime_type = _guess_image_mime_type(ext)

    with open(file_path, "rb") as f:
        img_bytes = f.read()

    img_b64 = base64.b64encode(img_bytes).decode("utf-8")
    data_url = f"data:{mime_type};base64,{img_b64}"

    headers = build_groq_headers()
    headers["Content-Type"] = "application/json"

    system_prompt = (
        "Você é um assistente que analisa imagens.\n"
        "Responda SEMPRE em português do Brasil.\n"
        "1) Descreva em detalhes o que aparece na imagem.\n"
        "2) Se houver texto legível, transcreva-o.\n"
        "3) Se for documento, faça um resumo estrutural."
    )

    user_prompt = (
        "Analise cuidadosamente a imagem enviada. "
        "Descreva o conteúdo visual e transcreva qualquer texto legível."
    )

    payload = {
        "model": settings.VISION_MODEL_NAME,
        "messages": [
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": user_prompt},
                    {
                        "type": "image_url",
                        "image_url": {"url": data_url, "detail": "high"},
                    },
                ],
            },
        ],
        "temperature": 0.2,
        "max_tokens": 2048,
    }

    resp = requests.post(
        settings.GROQ_CHAT_COMPLETIONS_ENDPOINT,
        headers=headers,
        json=payload,
        timeout=600,
    )
    resp.raise_for_status()
    data = resp.json()
    return data["choices"][0]["message"]["content"].strip()


def guess_doc_type(file_path: str) -> str:
    ext = os.path.splitext(file_path)[1].lower()
    if ext == ".pdf":
        return "pdf"
    if ext in AUDIO_EXTS:
        return "audio"
    if ext in VIDEO_EXTS:
        return "video"
    if ext in IMAGE_EXTS:
        return "image"
    raise ValueError(f"Extensão não suportada: {ext}")


def extract_text_and_metadata(
    file_path: str,
    title: Optional[str] = None,
) -> Tuple[str, Dict]:
    ext = os.path.splitext(file_path)[1].lower()
    base_name = os.path.basename(file_path)
    doc_type = guess_doc_type(file_path)

    if doc_type == "pdf":
        metadata = {
            "source": base_name,
            "title": title,
            "type": "pdf",
            "original_format": "pdf",
        }
        full_text = extract_text_from_pdf(file_path)

    elif doc_type == "audio":
        metadata = {
            "source": base_name,
            "title": title,
            "type": "audio",
            "original_format": ext.lstrip("."),
            "transcription_model": settings.TRANSCRIPTION_MODEL_NAME,
            "transcription_provider": "groq",
        }
        full_text = transcribe_audio_file(file_path)

    elif doc_type == "video":
        metadata = {
            "source": base_name,
            "title": title,
            "type": "video",
            "original_format": ext.lstrip("."),
            "transcription_model": settings.TRANSCRIPTION_MODEL_NAME,
            "transcription_provider": "groq",
        }
        full_text = transcribe_video_file(file_path)

    else:  # image
        file_size_bytes = os.path.getsize(file_path)
        metadata = {
            "source": base_name,
            "title": title,
            "type": "image",
            "original_format": ext.lstrip("."),
            "vision_model": settings.VISION_MODEL_NAME,
            "vision_provider": "groq",
            "file_size_bytes": file_size_bytes,
        }
        full_text = describe_image_with_groq(file_path, language="pt")

    return full_text, metadata
