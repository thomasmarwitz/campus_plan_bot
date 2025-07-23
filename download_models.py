
from sentence_transformers import CrossEncoder, SentenceTransformer
from transformers import WhisperForConditionalGeneration, WhisperProcessor

# Embedding and Reranker models
print("Downloading embedding and reranker models...")
SentenceTransformer("nomic-ai/nomic-embed-text-v1", trust_remote_code=True)
CrossEncoder("ml6team/cross-encoder-mmarco-german-distilbert-base")
print("Embedding and reranker models downloaded.")

# ASR model (unused in favor for the institute model)
# print("Downloading ASR model...")
# WhisperProcessor.from_pretrained("openai/whisper-base")
# WhisperForConditionalGeneration.from_pretrained("openai/whisper-base")
# print("ASR model downloaded.") 