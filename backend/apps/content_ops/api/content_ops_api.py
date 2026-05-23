from __future__ import annotations

import logging
import tempfile
from pathlib import Path

from django.http import FileResponse
from ninja import Router

from apps.content_ops.schemas.content_ops_schemas import TTSTestIn
from apps.content_ops.services.tts_service import TTS_VOICES, TTSService
from apps.core.security.auth import JWTOrSessionAuth

logger = logging.getLogger("apps.content_ops.api")

router = Router(tags=["内容运营"], auth=JWTOrSessionAuth())


@router.post("/tts/test")
def tts_test(request, payload: TTSTestIn):
    """Test TTS synthesis. Returns an MP3/WAV audio file for preview."""
    if not payload.text.strip():
        return {"error": "text 不能为空"}
    if len(payload.text) > 2000:
        return {"error": "text 不能超过 2000 字"}
    if payload.voice not in TTS_VOICES:
        return {"error": f"不支持的音色: {payload.voice}，可选: {', '.join(TTS_VOICES.keys())}"}

    try:
        service = TTSService()
        audio_bytes = service.synthesize(
            text=payload.text,
            voice=payload.voice,
            audio_format=payload.audio_format,
        )
    except Exception as e:
        logger.error("TTS test failed: %s", e)
        return {"error": str(e)}

    # Write to temp file and return as FileResponse
    suffix = f".{payload.audio_format}"
    tmp = tempfile.NamedTemporaryFile(suffix=suffix, delete=False)
    tmp.write(audio_bytes)
    tmp.flush()
    tmp.close()

    content_type = {
        "mp3": "audio/mpeg",
        "wav": "audio/wav",
        "pcm": "audio/pcm",
        "pcm16": "audio/pcm",
    }.get(payload.audio_format, "audio/mpeg")

    return FileResponse(
        Path(tmp.name).open("rb"),
        content_type=content_type,
        filename=f"tts_test{suffix}",
    )
