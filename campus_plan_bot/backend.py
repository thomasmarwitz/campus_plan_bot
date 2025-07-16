from pathlib import Path
from typing import Dict
import uuid

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from campus_plan_bot.rag import RAG
from campus_plan_bot.pipeline import Pipeline

app = FastAPI(
    title="Campus Plan Bot API",
    description="A stateful API for conversing with the Campus Plan Bot.",
)

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