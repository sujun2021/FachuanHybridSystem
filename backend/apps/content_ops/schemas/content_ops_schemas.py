from __future__ import annotations

from ninja import Schema


class TTSTestIn(Schema):
    """Request body for TTS test endpoint."""

    text: str  # Text to synthesize, 1-2000 chars
    voice: str = "冰糖"  # Voice name: 冰糖/茉莉/苏打/白桦
    audio_format: str = "mp3"  # Output format: mp3/wav/pcm/pcm16
