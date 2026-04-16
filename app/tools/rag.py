"""
rag.py — RAG con ChromaDB usando embeddings via OpenAI o Anthropic API
Sin torch ni sentence-transformers → imagen Docker ~1GB más ligera
Controlar con EMBEDDING_PROVIDER en .env: openai (defecto) | anthropic_voyage
"""

import os
import glob
from pathlib import Path
import chromadb
from chromadb import Documents, EmbeddingFunction, Embeddings
from dotenv import load_dotenv

load_dotenv()

DOCS_DIR   = Path(__file__).parent.parent.parent / "knowledge" / "docs"
CHROMA_DIR = Path(__file__).parent.parent.parent / "knowledge" / "chroma_db"
COLLECTION = "nomadas_knowledge"

EMBEDDING_PROVIDER = os.getenv("EMBEDDING_PROVIDER", "openai").lower()


# ---------------------------------------------------------------------------
# Embedding functions sin torch
# ---------------------------------------------------------------------------

class OpenAIEmbeddingFunction(EmbeddingFunction):
    def __init__(self):
        from openai import OpenAI
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.model  = "text-embedding-3-small"  # barato y rápido

    def __call__(self, input: Documents) -> Embeddings:
        response = self.client.embeddings.create(model=self.model, input=input)
        return [item.embedding for item in response.data]


class VoyageEmbeddingFunction(EmbeddingFunction):
    """Voyage AI es el proveedor de embeddings recomendado por Anthropic."""
    def __init__(self):
        import voyageai
        self.client = voyageai.Client(api_key=os.getenv("VOYAGE_API_KEY"))
        self.model  = "voyage-3-lite"

    def __call__(self, input: Documents) -> Embeddings:
        result = self.client.embed(input, model=self.model)
        return result.embeddings


def _get_embedding_function():
    if EMBEDDING_PROVIDER == "voyage":
        return VoyageEmbeddingFunction()
    return OpenAIEmbeddingFunction()  # defecto


# ---------------------------------------------------------------------------
# Colección ChromaDB
# ---------------------------------------------------------------------------

_collection = None

def get_collection():
    global _collection
    if _collection is None:
        client = chromadb.PersistentClient(path=str(CHROMA_DIR))
        _collection = client.get_or_create_collection(
            name=COLLECTION,
            embedding_function=_get_embedding_function(),
            metadata={"hnsw:space": "cosine"},
        )
    return _collection


# ---------------------------------------------------------------------------
# Indexación
# ---------------------------------------------------------------------------

def index_documents():
    col   = get_collection()
    files = glob.glob(str(DOCS_DIR / "**/*"), recursive=True)
    docs, ids, metas = [], [], []

    for fpath in files:
        path = Path(fpath)
        if path.suffix not in (".txt", ".md", ".pdf"):
            continue

        if path.suffix == ".pdf":
            try:
                import pypdf
                reader = pypdf.PdfReader(str(path))
                text   = "\n".join(p.extract_text() or "" for p in reader.pages)
            except ImportError:
                print(f"  pypdf no instalado, saltando {path.name}")
                continue
        else:
            text = path.read_text(encoding="utf-8", errors="ignore")

        words      = text.split()
        chunk_size = 500
        for i, start in enumerate(range(0, len(words), chunk_size)):
            chunk = " ".join(words[start:start + chunk_size])
            if len(chunk.strip()) < 50:
                continue
            docs.append(chunk)
            ids.append(f"{path.stem}_chunk{i}")
            metas.append({"source": path.name, "chunk": i})

    if docs:
        col.upsert(documents=docs, ids=ids, metadatas=metas)
        print(f"✓ Indexados {len(docs)} chunks de {len(files)} archivos")
    else:
        print("No se encontraron documentos en knowledge/docs/")


def search(query: str, n_results: int = 3) -> list[dict]:
    col = get_collection()
    if col.count() == 0:
        return []
    results = col.query(
        query_texts=[query],
        n_results=min(n_results, col.count()),
    )
    return [
        {"texto": doc, "fuente": meta.get("source", "?"), "distancia": round(dist, 3)}
        for doc, meta, dist in zip(
            results["documents"][0],
            results["metadatas"][0],
            results["distances"][0],
        )
    ]


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "index":
        index_documents()
    else:
        print("Uso: python -m app.tools.rag index")