import asyncio
import os
import tempfile
import uuid
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from loguru import logger
from pydantic import BaseModel, Field

from backend.utils import ASRMethod, audio_chat_generator
from campus_plan_bot.interfaces.interfaces import LLMClient, LLMRequestConfig
from campus_plan_bot.llm_client import InstituteClient
from campus_plan_bot.pipeline import Pipeline
from campus_plan_bot.rag import RAG
from campus_plan_bot.translator import Translator


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Start background janitor task
    asyncio.create_task(launch_session_janitor())
    yield


app = FastAPI(
    title="Campus Plan Bot API",
    description="A stateful API for conversing with the Campus Plan Bot.",
    lifespan=lifespan,
)


# Serve the frontend
@app.get("/")
async def read_index():
    return FileResponse("frontend/index.html")


app.mount("/frontend", StaticFiles(directory="frontend"), name="frontend")

database_path = Path("data") / "campusplan_evaluation.csv"
embeddings_path = Path("data") / "embeddings"
# We will create a new bot instance for each session
# but we can pre-load the RAG component to save time.
rag_component = RAG.from_file(database_path, persist_dir=embeddings_path)

# In-memory storage for bot sessions


@dataclass
class SessionData:
    pipeline: Pipeline
    last_used: datetime = field(default_factory=datetime.utcnow)


# Maximum idle time before a session is cleaned up
SESSION_TTL = timedelta(hours=1)
# How often the janitor checks for stale sessions (in seconds)
SWEEP_PERIOD_SECONDS = 10 * 60

pipeline_sessions: dict[str, SessionData] = {}


def _touch(session_id: str) -> None:
    """Refresh last-use timestamp for the given session, if it exists."""
    session = pipeline_sessions.get(session_id)
    if session:
        session.last_used = datetime.utcnow()


async def launch_session_janitor() -> None:
    """Background task that removes stale sessions periodically."""

    async def janitor() -> None:
        while True:
            await asyncio.sleep(SWEEP_PERIOD_SECONDS)
            now = datetime.utcnow()
            expired = [
                sid
                for sid, sess in list(pipeline_sessions.items())
                if now - sess.last_used > SESSION_TTL
            ]
            for sid in expired:
                logger.info(f"Session {sid} expired (idle > {SESSION_TTL}). Removing.")
                del pipeline_sessions[sid]

    asyncio.create_task(janitor())


GLOBAL_ALLOW_COMPLEX_MODE = bool(os.getenv("OPENAI_API_KEY"))
if not GLOBAL_ALLOW_COMPLEX_MODE:
    logger.info("OPENAI_API_KEY not found, complex queries are disabled.")


class StartRequest(BaseModel):
    model_name: str = "Llama3.1-8B"
    temperature: float = 0.05
    max_new_tokens: int = 1024
    user_coords_str: str | None = None
    allow_complex_mode: bool = GLOBAL_ALLOW_COMPLEX_MODE


class StartResponse(BaseModel):
    session_id: str = Field(..., description="The unique ID for the new session.")


class ChatRequest(BaseModel):
    session_id: str = Field(..., description="The session ID.")
    query: str = Field(..., description="The user's query.")


class ChatResponse(BaseModel):
    response: str = Field(..., description="The bot's response.")
    link: str | None = Field(
        None, description="A link relevant to the response, if any."
    )


class TranslationRequest(BaseModel):
    text: str
    target_language: str


class TranslationResponse(BaseModel):
    translated_text: str


# Instantiate the translator once to be reused across requests
translator = Translator()


@app.post("/start", response_model=StartResponse)
def start_session(request: StartRequest):
    """Starts a new chat session and returns a unique session ID."""
    session_id = str(uuid.uuid4())

    llm_config = LLMRequestConfig(
        temperature=request.temperature,
        max_new_tokens=request.max_new_tokens,
    )

    llm_client: LLMClient
    if request.model_name == "Llama3.1-8B":
        llm_client = InstituteClient(default_request_config=llm_config)
    # elif request.model_name == "Qwen3-32B":
    #    llm_client = ChuteModel(default_request_config=llm_config, no_think=True, strip_think=True)  # type: ignore[assignment]
    else:
        raise HTTPException(status_code=400, detail="Invalid model name.")

    pipeline_sessions[session_id] = SessionData(
        pipeline=Pipeline.from_system_prompt(
            rag=rag_component,
            llm_client=llm_client,
            user_coords_str=request.user_coords_str,
            allow_complex_mode=(
                request.allow_complex_mode if GLOBAL_ALLOW_COMPLEX_MODE else False
            ),
        )
    )
    return StartResponse(session_id=session_id)


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Chat with the bot using a session ID."""
    session = pipeline_sessions.get(request.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found.")
    _touch(request.session_id)

    response = await session.pipeline.run(request.query)
    return ChatResponse(response=response.answer, link=response.link)


@app.post("/translate", response_model=TranslationResponse)
async def translate_text(request: TranslationRequest):
    """Translates text to a specified language."""
    try:
        translated_text = await translator.translate(
            text=request.text, target_language=request.target_language
        )
        return TranslationResponse(translated_text=translated_text)
    except Exception as e:
        logger.error(f"Translation failed: {e}")
        raise HTTPException(status_code=500, detail="Translation service failed.")


@app.post("/chat_audio")
async def chat_audio(
    request: Request,
    session_id: str = Form(...),
    file: UploadFile = File(...),
):
    """Chat with the bot using an audio recording, streaming transcript and
    final response."""
    session = pipeline_sessions.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found.")
    _touch(session_id)

    # The UploadFile must be read here, before the function returns
    # and the file handle is closed by FastAPI.
    fd_in, tmp_in_path = tempfile.mkstemp()
    os.close(fd_in)
    try:
        with open(tmp_in_path, "wb") as f:
            content = await file.read()
            f.write(content)
    finally:
        await file.close()

    async def sse_generator():
        # The generator must clean up the temporary file when it's done.
        try:
            async for data in audio_chat_generator(
                session.pipeline, ASRMethod.REMOTE, tmp_in_path
            ):
                if await request.is_disconnected():
                    logger.warning("Client disconnected.")
                    break
                yield f"data: {data}\n\n"
        finally:
            os.remove(tmp_in_path)

    return StreamingResponse(sse_generator(), media_type="text/event-stream")


@app.post("/end")
def end_session(session_id: str):
    """Ends a chat session and cleans up resources."""
    if session_id in pipeline_sessions:
        del pipeline_sessions[session_id]
        return {"message": f"Session {session_id} ended."}
    else:
        raise HTTPException(status_code=404, detail="Session not found.")
