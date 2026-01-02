import os
from dotenv import load_dotenv
from langchain_nomic import NomicEmbeddings

load_dotenv()

embedder=NomicEmbeddings(model="nomic-embed-text-v1.5",nomic_api_key=os.getenv("NOMIC_API_KEY"))

def generate_embeddings(chunks: list[str]):
    embeddings = embedder.embed_documents(texts=chunks)
    return embeddings

def search_embeddings(query: str) -> list[float]:
    embeddings = embedder.embed_query(text=query)
    return embeddings

def text_from_embeddings(embeddings: list[float]) -> str:
    text = embedder(text=embeddings)
    return text