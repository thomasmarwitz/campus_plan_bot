"""Core Protocol Interfaces for the KIT Campus Navigator.

This file defines the simplified protocol interfaces for the main
components following the KISS principle as outlined in the project
specification.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import (
    Any,
    Optional,
    Protocol,
    TypedDict,
)


# --- Common Types ---
class Role(StrEnum):
    """Enum for user roles in the conversation."""

    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
    CODE = "ipython"


class InputMethods(StrEnum):
    """Enum for input types."""

    ASR = "asr"
    LOCAL_ASR = "local_asr"
    TEXT = "text"


class MessageProtocol(Protocol):
    """Protocol for a message from the user."""

    id: str
    timestamp: datetime
    content: str
    role: Role


class ConversationProtocol(Protocol):
    """Protocol for the conversation history."""

    id: str
    messages: Sequence[MessageProtocol]


@dataclass
class RetrievedDocument:
    """Represents a document retrieved from the database."""

    id: str
    # content: str
    data: dict
    relevance_score: float

    def __str__(self) -> str:
        return f"Document ID: {self.id}, Relevance Score: {self.relevance_score}, Content: {str(self.data)}"


# --- Input Processing Protocols ---


class UserInputSource(Protocol):
    """Protocol for receiving textual input from the user."""

    def get_input(self) -> str:
        """Get user input from one of the supported modalities.

        Returns:
            User input converted to text
        """
        ...


class AutomaticSpeechRecognition(UserInputSource, Protocol):
    """Protocol for automatic speech recognition component."""

    file_path: Optional[str]

    def __init__(self, file=None):
        self.file_path = file

    # We'll probably need async / threads to handle the provided ASR API
    # but maybe the interface can still be synchronous
    def transcribe(self, audio_path: str) -> str:
        """Convert audio data to text.

        Args:
            audio_path: Path to audio file

        Returns:
            Transcribed text
        """
        ...


# --- RAG Component Protocols ---


class EmbeddingGenerator(Protocol):
    """Protocol for generating embeddings from text."""

    def embed(self, text: str) -> list[float]:
        """Generate embedding vector for text.

        Args:
            text: Input text

        Returns:
            Embedding vector
        """
        ...

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Generate embedding vectors for multiple texts.

        Args:
            texts: List of input texts

        Returns:
            List of embedding vectors
        """
        ...


class SimilarityCalculator(Protocol):
    """Protocol for calculating similarity between embeddings."""

    # The types need to be changed to numpy / torch tensors later
    def calculate(self, embedding_a: Any, embedding_b: Any) -> float:
        """Calculate similarity scores between two embeddings."""
        ...


class Database(Protocol):
    """Protocol for database operations."""

    # What do we need here?


class RAGComponent(Protocol):
    """Protocol for the RAG (Retrieval-Augmented Generation) component."""

    # ATM, don't require the rag component to have those attributes
    # similarity_measure: SimilarityCalculator
    # embedding_generator: EmbeddingGenerator
    # database: Database

    def retrieve_context(
        self, query: str, limit: int = 5, conversation_history: list[str] | None = None
    ) -> list[RetrievedDocument]:
        """Retrieve relevant context based on a query string."""
        ...


# --- Contextual Information Protocols ---


class ContextProvider(Protocol):
    """Protocol for providing contextual information."""

    def get_current_datetime(self) -> datetime:
        """Get current date and time.

        Returns:
            Current date and time
        """
        ...

    def get_contextual_data(self) -> dict[str, Any]:
        """Get all available contextual data.

        Returns:
            Dictionary of contextual data
        """
        ...


# --- Prompt Assembly Protocols ---


class PromptAssembler(Protocol):
    """Protocol for assembling prompts for the LLM."""

    def assemble_prompt(
        self,
        user_message: MessageProtocol,
        conversation: ConversationProtocol,
        retrieved_contexts: list[RetrievedDocument],
        system_prompt: str,
        contextual_info: dict[str, Any],
    ) -> str:
        """Assemble a prompt for the LLM.

        Args:
            user_message: Current user message
            conversation: Conversation history
            retrieved_contexts: Retrieved context documents
            system_prompt: System prompt
            contextual_info: Contextual information

        Returns:
            Assembled prompt
        """
        ...

    # Where should this be stored?
    def get_system_prompt(self) -> str:
        """Get the system prompt for the KIT Campus Navigator.

        Returns:
            System prompt
        """
        ...


# --- LLM Client Protocols ---


class LLMRequestConfig(TypedDict):
    """Represents a request to an LLM."""

    temperature: float
    max_new_tokens: int


class LLMClient(Protocol):
    """Protocol for interacting with language models."""

    def generate(self, prompt: str, config: LLMRequestConfig) -> str:
        """Generate a response from the LLM.

        Args:
            request: LLM request parameters

        Returns:
            LLM response
        """
        ...

    def query(self, prompt: str) -> str:
        """Query the LLM with default request config.

        Args:
            prompt: Prompt to query the LLM

        Returns:
                LLM response
        """
        ...


# --- Response Parsing Protocols ---


class Action(Protocol):
    """Protocol for a parsed action from the LLM response."""

    # Is there a generic attribute for all actions?

    def execute(self) -> Any: ...


class ResponseParser(Protocol):
    """Protocol for parsing responses from the LLM."""

    def parse(self, llm_response: str) -> tuple[str, list[Action]]:
        """Parse the LLM response to extract text and actions.

        Args:
            llm_response: Response from the LLM

        Returns:
            Tuple of (processed_text, extracted_actions)
        """
        ...


# --- Output Generation Protocols ---


class Translator(Protocol):
    """Protocol for translating text."""

    def translate(self, text: str, target_language: str) -> str:
        """Translate text to target language.

        Args:
            text: Input text
            target_language: Target language code

        Returns:
            Translated text
        """
        ...


class TextToSpeech(Protocol):
    """Protocol for text-to-speech conversion."""

    def synthesize(self, text: str, voice_id: str = "default") -> bytes:
        """Convert text to speech.

        Args:
            text: Input text
            voice_id: Voice identifier

        Returns:
            Audio data
        """
        ...


class OutputGenerator(Protocol):
    """Protocol for generating system output."""

    # What about text to speech?
    def generate(self, text: str, actions: list[Action]) -> MessageProtocol:
        """Generate system output.

        Args:
            text: Text content
            actions: List of actions

        Returns:
            System message
        """
        ...


class TextBot(Protocol):
    """Protocol for the main bot interface."""

    def query(self, query: str, docs: list[RetrievedDocument]) -> str:
        """Process a user query and return a response."""
        ...
