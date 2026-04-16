"""
rag.py — Sistema RAG con ChromaDB para documentos propios
Coloca tus PDFs, TXTs, MDs en knowledge/docs/ y ejecuta: python -m app.tools.rag index
"""

import os
import glob
from pathlib import Path
import chromadb
from chromadb.utils import embedding_functions
from dotenv import load_dotenv

load_dotenv()

DOCS_DIR    = Path(__file__).parent.parent.parent / "knowledge" / "docs"
CHROMA_DIR  = Path(__file__).parent.parent.parent / "knowledge" / "chroma_db"
COLLECTION  = "nomadas_knowledge"

# Usa OpenAI-compatible embeddings via Anthropic o embeddings locales
# Por simplicidad usamos el modelo de sentence-transformers local (sin coste)
_ef = embedding_functions.SentenceTransformerEmbeddingFunction(
    model_name="paraphrase-multilingual-MiniLM-L12-v2"  # soporta español
)

_client: chromadb.ClientAPI = None
_collection = None


def get_collection():
    global _client, _collection
    if _collection is None:
        _client = chromadb.PersistentClient(path=str(CHROMA_DIR))
        _collection = _client.get_or_create_collection(
            name=COLLECTION,
            embedding_function=_ef,
            metadata={"hnsw:space": "cosine"},
        )
    return _collection


def index_documents():
    """Indexa todos los archivos de knowledge/docs/"""
    col = get_collection()
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
                text = "\n".join(p.extract_text() or "" for p in reader.pages)
            except ImportError:
                print(f"  pypdf no instalado, saltando {path.name}")
                continue
        else:
            text = path.read_text(encoding="utf-8", errors="ignore")

        # Dividir en chunks de ~500 palabras
        words = text.split()
        chunk_size = 500
        for i, start in enumerate(range(0, len(words), chunk_size)):
            chunk = " ".join(words[start:start + chunk_size])
            if len(chunk.strip()) < 50:
                continue
            doc_id = f"{path.stem}_chunk{i}"
            docs.append(chunk)
            ids.append(doc_id)
            metas.append({"source": path.name, "chunk": i})

    if docs:
        # Upsert para no duplicar en re-indexaciones
        col.upsert(documents=docs, ids=ids, metadatas=metas)
        print(f"✓ Indexados {len(docs)} chunks de {len(files)} archivos")
    else:
        print("No se encontraron documentos en knowledge/docs/")


def search(query: str, n_results: int = 3) -> list[dict]:
    """Busca los fragmentos más relevantes para una query."""
    col = get_collection()
    if col.count() == 0:
        return []

    results = col.query(
        query_texts=[query],
        n_results=min(n_results, col.count()),
    )

    output = []
    for doc, meta, distance in zip(
        results["documents"][0],
        results["metadatas"][0],
        results["distances"][0],
    ):
        output.append({
            "texto":    doc,
            "fuente":   meta.get("source", "?"),
            "distancia": round(distance, 3),
        })
    return output


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "index":
        index_documents()
    else:
        print("Uso: python -m app.tools.rag index")
