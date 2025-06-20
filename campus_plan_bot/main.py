import uuid
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from campus_plan_bot.bot import RAG, SimpleTextBot

app = FastAPI(
    title="Campus Plan Bot API",
    description="A stateful API for conversing with the Campus Plan Bot.",
)


# Serve the frontend
@app.get("/")
async def read_index():
    return FileResponse("frontend/index.html")


app.mount("/frontend", StaticFiles(directory="frontend"), name="frontend")

database_path = Path("phase1") / "data" / "campusplan_evaluation.csv"

# We will create a new bot instance for each session
# but we can pre-load the RAG component to save time.
rag_component = RAG.from_file(database_path)

# In-memory storage for bot sessions
bot_sessions: dict[str, SimpleTextBot] = {}


class StartResponse(BaseModel):
    session_id: str = Field(..., description="The unique ID for the new session.")


class ChatRequest(BaseModel):
    session_id: str = Field(..., description="The session ID.")
    query: str = Field(..., description="The user's query.")


class ChatResponse(BaseModel):
    response: str = Field(..., description="The bot's response.")


@app.post("/start", response_model=StartResponse)
def start_session():
    """Starts a new chat session and returns a unique session ID."""
    session_id = str(uuid.uuid4())
    bot_sessions[session_id] = SimpleTextBot(rag=rag_component)
    return StartResponse(session_id=session_id)


@app.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest):
    """Chat with the bot using a session ID."""
    bot = bot_sessions.get(request.session_id)
    if not bot:
        raise HTTPException(status_code=404, detail="Session not found.")

    response = bot.query(request.query)
    return ChatResponse(response=response)


@app.post("/end")
def end_session(session_id: str):
    """Ends a chat session and cleans up resources."""
    if session_id in bot_sessions:
        del bot_sessions[session_id]
        return {"message": f"Session {session_id} ended."}
    else:
        raise HTTPException(status_code=404, detail="Session not found.")
