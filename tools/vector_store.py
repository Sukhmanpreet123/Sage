"""
tools/vector_store.py
---------------------
2026 Agentic RAG Cache Layer — ChromaDB + sentence-transformers

Purpose:
  - Before running live web search, check if the topic has already been
    researched and stored in the local ChromaDB collection.
  - If a similar topic exists (cosine similarity > 0.85), load cached sources.
  - After a new research run, store results so future runs can reuse them.

This turns the system from "always online" to a smart hybrid:
  Fast repeated queries → ChromaDB (instant)
  New topics           → Full agent pipeline (then cached)
"""

import os
import hashlib
import json
from typing import List, Optional

# ChromaDB persistent client
import chromadb
from chromadb.config import Settings

# Sentence-transformers for embedding generation
from sentence_transformers import SentenceTransformer

# ── Config ────────────────────────────────────────────────────────────────────

CHROMA_PATH       = os.getenv("CHROMA_DB_PATH", "output/chromadb")
COLLECTION_NAME   = "research_cache"
SIMILARITY_THRESH = float(os.getenv("CACHE_SIMILARITY_THRESHOLD", "0.85"))
EMBED_MODEL_NAME  = "all-MiniLM-L6-v2"   # 80MB, runs on CPU, very fast


# ── Lazy singletons (avoid reloading on every call) ──────────────────────────

_client: Optional[chromadb.PersistentClient] = None
_collection = None
_embed_model: Optional[SentenceTransformer] = None


def _get_client():
    """Returns (creates if needed) the ChromaDB persistent client."""
    global _client, _collection
    if _client is None:
        os.makedirs(CHROMA_PATH, exist_ok=True)
        _client = chromadb.PersistentClient(
            path=CHROMA_PATH,
            settings=Settings(anonymized_telemetry=False)
        )
        _collection = _client.get_or_create_collection(
            name=COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"}
        )
    return _client, _collection


def _get_embed_model() -> SentenceTransformer:
    """Returns (loads if needed) the sentence-transformer model."""
    global _embed_model
    if _embed_model is None:
        print(f"[Vector Store] Loading embedding model '{EMBED_MODEL_NAME}'...")
        _embed_model = SentenceTransformer(EMBED_MODEL_NAME)
        print("[Vector Store] Embedding model loaded.")
    return _embed_model


def _topic_to_id(topic: str) -> str:
    """Creates a stable cache ID from a topic string."""
    return hashlib.sha256(topic.strip().lower().encode()).hexdigest()[:16]


# ── Public API ────────────────────────────────────────────────────────────────

def check_cache(topic: str) -> Optional[List[dict]]:
    """
    Query ChromaDB for previously cached sources similar to the given topic.

    Returns:
        List of source dicts if cache hit (similarity >= threshold), else None.
    """
    try:
        _, collection = _get_client()
        model = _get_embed_model()

        # Embed the query topic
        query_embedding = model.encode(topic).tolist()

        # Search for similar topics in the collection
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=1,
            include=["documents", "metadatas", "distances"]
        )

        if not results["ids"] or not results["ids"][0]:
            return None

        # Distance in cosine space: 0 = identical, 1 = orthogonal
        distance = results["distances"][0][0]
        similarity = 1.0 - distance

        if similarity >= SIMILARITY_THRESH:
            # Deserialize stored sources
            stored_json = results["documents"][0][0]
            sources = json.loads(stored_json)
            cached_topic = results["metadatas"][0][0].get("topic", "unknown")
            print(f"[Vector Store] Cache hit! Similarity={similarity:.2f} — cached topic: '{cached_topic}'")
            return sources
        else:
            print(f"[Vector Store] Cache miss. Best similarity={similarity:.2f} (threshold={SIMILARITY_THRESH})")
            return None

    except Exception as e:
        print(f"[Vector Store] ChromaDB check_cache error: {e}")
        return None


def store_results(topic: str, sources: List[dict]) -> bool:
    """
    Stores research sources in ChromaDB keyed to the topic embedding.

    Args:
        topic:   The researched topic string.
        sources: List of SourceItem dicts to cache.

    Returns:
        True on success, False on failure.
    """
    try:
        _, collection = _get_client()
        model = _get_embed_model()

        topic_embedding = model.encode(topic).tolist()
        topic_id = _topic_to_id(topic)

        # Serialize sources to JSON for storage
        sources_json = json.dumps(sources, ensure_ascii=False)

        # Upsert so re-running the same topic updates the cache
        collection.upsert(
            ids=[topic_id],
            embeddings=[topic_embedding],
            documents=[sources_json],
            metadatas=[{"topic": topic, "num_sources": len(sources)}]
        )

        print(f"[Vector Store] Cached {len(sources)} sources for topic: '{topic}'")
        return True

    except Exception as e:
        print(f"[Vector Store] ChromaDB store_results error: {e}")
        return False


def clear_cache() -> bool:
    """Clears the entire research cache (use with caution)."""
    try:
        _, collection = _get_client()
        all_ids = collection.get()["ids"]
        if all_ids:
            collection.delete(ids=all_ids)
        print(f"[Vector Store] Cache cleared ({len(all_ids)} entries removed).")
        return True
    except Exception as e:
        print(f"[Vector Store] Cache clear error: {e}")
        return False
