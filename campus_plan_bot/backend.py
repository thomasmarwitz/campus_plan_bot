from pathlib import Path
from typing import Dict
import uuid
import tempfile
import shutil
import os
import asyncio
from enum import Enum
import subprocess
from loguru import logger

from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from campus_plan_bot.rag import RAG
from campus_plan_bot.pipeline import Pipeline
from campus_plan_bot.input.local_asr import LocalASR
from campus_plan_bot.input.remote_asr import RemoteASR

app = FastAPI(
    title="Campus Plan Bot API",
    description="A stateful API for conversing with the Campus Plan Bot.",
)


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

# Serve the frontend
@app.get("/")
async def read_index():
    return FileResponse('frontend/index.html')

app.mount("/frontend", StaticFiles(directory="frontend"), name="frontend")

database_path = Path("data") / "campusplan_evaluation.csv"
embeddings_path = Path("data") / "embeddings"
# We will create a new bot instance for each session
# but we can pre-load the RAG component to save time.
rag_component = RAG.from_file(database_path, persist_dir=embeddings_path)

# In-memory storage for bot sessions
pipeline_sessions: Dict[str, Pipeline] = {}


class StartResponse(BaseModel):
    session_id: str = Field(..., description="The unique ID for the new session.")


class ChatRequest(BaseModel):
    session_id: str = Field(..., description="The session ID.")
    query: str = Field(..., description="The user's query.")


class ChatResponse(BaseModel):
    response: str = Field(..., description="The bot's response.")
    link: str | None = Field(None, description="A link relevant to the response, if any.")


@app.post("/start", response_model=StartResponse)
def start_session():
    """
    Starts a new chat session and returns a unique session ID.
    """
    session_id = str(uuid.uuid4())
    pipeline_sessions[session_id] = Pipeline.from_system_prompt(rag=rag_component)
    return StartResponse(session_id=session_id)


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Chat with the bot using a session ID.
    """
    pipeline = pipeline_sessions.get(request.session_id)
    if not pipeline:
        raise HTTPException(status_code=404, detail="Session not found.")

    response = await pipeline.run(request.query)
    return ChatResponse(response=response.answer, link=response.link)


@app.post("/chat_audio", response_model=ChatResponse)
async def chat_audio(
    session_id: str = Form(...),
    asr_method: ASRMethod = Form(ASRMethod.LOCAL),
    file: UploadFile = File(...),
):
    """
    Chat with the bot using an audio recording.
    """
    pipeline = pipeline_sessions.get(session_id)
    if not pipeline:
        raise HTTPException(status_code=404, detail="Session not found.")

    fd_in, tmp_in_path = tempfile.mkstemp()
    os.close(fd_in)

    fd_out, tmp_out_path = tempfile.mkstemp(suffix=".wav")
    os.close(fd_out)

    try:
        with open(tmp_in_path, "wb") as f:
            shutil.copyfileobj(file.file, f)

        _convert_to_wav(tmp_in_path, tmp_out_path)

        if asr_method == ASRMethod.LOCAL:
            asr = LocalASR(None)
        else:
            asr = RemoteASR(None)

        loop = asyncio.get_event_loop()
        transcript = await loop.run_in_executor(None, asr.transcribe, tmp_out_path)

        response = await pipeline.run(transcript, fix_asr=True)
        return ChatResponse(response=response.answer, link=response.link)
    finally:
        os.remove(tmp_in_path)
        os.remove(tmp_out_path)
        await file.close()


@app.post("/end")
def end_session(session_id: str):
    """
    Ends a chat session and cleans up resources.
    """
    if session_id in pipeline_sessions:
        del pipeline_sessions[session_id]
        return {"message": f"Session {session_id} ended."}
    else:
        raise HTTPException(status_code=404, detail="Session not found.") 