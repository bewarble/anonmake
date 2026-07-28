from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from aiogram.types import Message

SUPPORTED_MEDIA_TYPES = {
    "photo",
    "video",
    "document",
    "animation",
    "audio",
    "voice",
    "video_note",
    "sticker",
}


@dataclass(frozen=True, slots=True)
class TelegramContent:
    content_type: str
    text: str
    file_id: str | None
    caption: str | None

    @property
    def duplicate_key(self) -> str:
        return "|".join(
            (
                self.content_type,
                self.file_id or "",
                self.text,
                self.caption or "",
            )
        )


def extract_content(message: Message) -> TelegramContent | None:
    text = (message.text or "").strip()
    if text:
        return TelegramContent("text", text, None, None)

    caption = (message.caption or "").strip() or None

    if message.photo:
        return TelegramContent(
            "photo",
            caption or "Фото",
            message.photo[-1].file_id,
            caption,
        )
    if message.video:
        return TelegramContent(
            "video",
            caption or "Видео",
            message.video.file_id,
            caption,
        )
    if message.document:
        fallback = message.document.file_name or "Документ"
        return TelegramContent(
            "document",
            caption or fallback,
            message.document.file_id,
            caption,
        )
    if message.animation:
        return TelegramContent(
            "animation",
            caption or "Анимация",
            message.animation.file_id,
            caption,
        )
    if message.audio:
        fallback = message.audio.title or message.audio.file_name or "Аудио"
        return TelegramContent(
            "audio",
            caption or fallback,
            message.audio.file_id,
            caption,
        )
    if message.voice:
        return TelegramContent(
            "voice",
            caption or "Голосовое сообщение",
            message.voice.file_id,
            caption,
        )
    if message.video_note:
        return TelegramContent(
            "video_note",
            "Видеосообщение",
            message.video_note.file_id,
            None,
        )
    if message.sticker:
        return TelegramContent(
            "sticker",
            message.sticker.emoji or "Стикер",
            message.sticker.file_id,
            None,
        )

    return None


def delivery_payload(content: TelegramContent) -> dict[str, Any] | None:
    if content.content_type == "text":
        return None
    return {
        "content_type": content.content_type,
        "file_id": content.file_id,
        "caption": content.caption,
    }
