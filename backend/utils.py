import asyncio
import json
import os
import subprocess
import tempfile
from enum import Enum
from typing import AsyncGenerator

from loguru import logger

from campus_plan_bot.input.local_asr import LocalASR
from campus_plan_bot.input.remote_asr import RemoteASR
from campus_plan_bot.pipeline import Pipeline


def _convert_to_wav(input_path: str, output_path: str):
    """Converts an audio file to WAV format using ffmpeg."""
    command = [
        "ffmpeg",
        "-i",
        input_path,
        "-acodec",
        "pcm_s16le",
        "-ar",
        "16000",
        "-ac",
        "1",
        "-y",  # Overwrite output file if it exists
        output_path,
    ]
    try:
        subprocess.run(
            command,
            check=True,
            capture_output=True,
            text=True,
        )
    except FileNotFoundError:
        logger.error("ffmpeg not found. Make sure it is installed and in your PATH.")
        raise
    except subprocess.CalledProcessError as e:
        logger.error(f"Error converting audio file with ffmpeg: {e.stderr}")
        raise


class ASRMethod(str, Enum):
    LOCAL = "local"
    REMOTE = "remote"


async def audio_chat_generator(
    pipeline: Pipeline, asr_method: ASRMethod, input_path: str
) -> AsyncGenerator[str, None]:
    """Generator that handles audio processing and yields SSE events."""
    fd_out, tmp_out_path = tempfile.mkstemp(suffix=".wav")
    os.close(fd_out)

    try:
        _convert_to_wav(input_path, tmp_out_path)

        if asr_method == ASRMethod.LOCAL:
            asr = LocalASR(None)
        else:
            asr = RemoteASR(None)

        loop = asyncio.get_event_loop()
        transcript = await loop.run_in_executor(None, asr.transcribe, tmp_out_path)

        yield json.dumps({"type": "transcript", "data": transcript})

        response = await pipeline.run(transcript, fix_asr=True)

        yield json.dumps(
            {
                "type": "final_response",
                "data": {"response": response.answer, "link": response.link},
            }
        )

    finally:
        os.remove(tmp_out_path) 