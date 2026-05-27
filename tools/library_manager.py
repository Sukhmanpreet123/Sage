"""
tools/library_manager.py
------------------------
Phase 2 Feature: Personal Research Library

Allows users to upload their own PDF documents (papers, notes, past reports).
These are indexed into a dedicated ChromaDB collection ("user_library"), separate
from the main research cache.

When a topic is researched, the top relevant chunks from the user's library are
retrieved and injected into the pipeline as "user_library_context", enabling
the Contradiction Detector and Writer to cross-reference against personal knowledge.

Key capabilities:
  - index_user_pdf()        : Chunk and embed a user-uploaded PDF
  - query_user_library()    : Semantic search against personal library
  - list_library_documents(): List all indexed document names
  - delete_from_library()   : Remove a document by filename
  - clear_library()         : Wipe the entire personal library
"""

import os
import io
import hashlib

# Try pdfplumber for PDF text extraction (better than PyPDF2 for complex layouts)
try:
    import pdfplumber
    PDFPLUMBER_AVAILABLE = True
except ImportError:
    PDFPLUMBER_AVAILABLE = False

# Try PyPDF2 as fallback
try:
    import PyPDF2
    PYPDF2_AVAILABLE = True
except ImportError:
    PYPDF2_AVAILABLE = False

# ChromaDB for vector storage
try:
    import chromadb
    from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction
    CHROMA_AVAILABLE = True
except ImportError:
    CHROMA_AVAILABLE = False

LIBRARY_COLLECTION_NAME = "user_library"
CHUNK_SIZE = 600          # Characters per chunk
CHUNK_OVERLAP = 100       # Overlap between chunks for context continuity
MAX_QUERY_RESULTS = 5     # Top chunks to return per query

_chroma_client = None
_library_collection = None


def _get_library_collection():
    """Get or initialize the ChromaDB user_library collection."""
    global _chroma_client, _library_collection

    if not CHROMA_AVAILABLE:
        raise ImportError("chromadb not installed. Run: pip install chromadb sentence-transformers")

    if _library_collection is None:
        db_path = os.getenv("CHROMA_DB_PATH", "output/chromadb")
        os.makedirs(db_path, exist_ok=True)

        _chroma_client = chromadb.PersistentClient(path=db_path)
        embed_fn = SentenceTransformerEmbeddingFunction(model_name="all-MiniLM-L6-v2")

        _library_collection = _chroma_client.get_or_create_collection(
            name=LIBRARY_COLLECTION_NAME,
            embedding_function=embed_fn,
            metadata={"hnsw:space": "cosine"}
        )

    return _library_collection


def _extract_text_from_pdf(file_bytes: bytes) -> str:
    """
    Extract plain text from PDF bytes.
    Tries pdfplumber first (better quality), then PyPDF2 as fallback.
    """
    if PDFPLUMBER_AVAILABLE:
        try:
            with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
                pages = []
                for page in pdf.pages[:50]:  # Cap at 50 pages
                    text = page.extract_text()
                    if text:
                        pages.append(text.strip())
            return "\n\n".join(pages)
        except Exception as e:
            print(f"[Library] pdfplumber extraction failed: {e}")

    if PYPDF2_AVAILABLE:
        try:
            reader = PyPDF2.PdfReader(io.BytesIO(file_bytes))
            pages = []
            for page in reader.pages[:50]:
                text = page.extract_text()
                if text:
                    pages.append(text.strip())
            return "\n\n".join(pages)
        except Exception as e:
            print(f"[Library] PyPDF2 extraction failed: {e}")

    raise ImportError(
        "No PDF extraction library available. Install pdfplumber: pip install pdfplumber"
    )


def _chunk_text(text: str, filename: str) -> list[dict]:
    """
    Split text into overlapping chunks for vector indexing.
    Returns list of dicts: {id, text, filename, chunk_index}
    """
    chunks = []
    start = 0
    chunk_index = 0
    file_hash = hashlib.md5(filename.encode()).hexdigest()[:8]

    while start < len(text):
        end = min(start + CHUNK_SIZE, len(text))
        chunk_text = text[start:end].strip()

        if len(chunk_text) > 50:  # Skip tiny chunks
            chunks.append({
                "id":          f"{file_hash}_chunk_{chunk_index}",
                "text":        chunk_text,
                "filename":    filename,
                "chunk_index": chunk_index,
            })
            chunk_index += 1

        start += CHUNK_SIZE - CHUNK_OVERLAP

    return chunks


def index_user_pdf(file_bytes: bytes, filename: str) -> dict:
    """
    Index a user-uploaded PDF into the personal research library.

    Args:
        file_bytes: Raw bytes of the PDF file
        filename:   Original filename for metadata tracking

    Returns:
        dict with keys: success, chunks_indexed, filename, message
    """
    result = {"success": False, "chunks_indexed": 0, "filename": filename, "message": ""}

    try:
        print(f"[Library] Extracting text from '{filename}'...")
        text = _extract_text_from_pdf(file_bytes)

        if not text or len(text) < 100:
            result["message"] = "PDF appears to be empty or image-only (no extractable text)."
            return result

        chunks = _chunk_text(text, filename)
        print(f"[Library] Created {len(chunks)} chunks from '{filename}'")

        collection = _get_library_collection()

        # Delete existing chunks for this file to allow re-indexing
        try:
            existing = collection.get(where={"filename": filename})
            if existing["ids"]:
                collection.delete(ids=existing["ids"])
                print(f"[Library] Removed {len(existing['ids'])} old chunks for '{filename}'")
        except Exception:
            pass

        # Batch upsert chunks
        collection.upsert(
            ids=[c["id"] for c in chunks],
            documents=[c["text"] for c in chunks],
            metadatas=[{"filename": c["filename"], "chunk_index": c["chunk_index"]} for c in chunks],
        )

        result["success"] = True
        result["chunks_indexed"] = len(chunks)
        result["message"] = f"Successfully indexed {len(chunks)} chunks from '{filename}'."
        print(f"[Library] ✅ Indexed '{filename}' ({len(chunks)} chunks)")

    except ImportError as e:
        result["message"] = str(e)
    except Exception as e:
        result["message"] = f"Indexing failed: {str(e)}"
        print(f"[Library] ❌ Error indexing '{filename}': {e}")

    return result


def query_user_library(topic: str, k: int = MAX_QUERY_RESULTS) -> str:
    """
    Query the personal library for chunks relevant to a topic.

    Args:
        topic: Research topic to search for
        k:     Number of top chunks to retrieve

    Returns:
        Merged text string of relevant library chunks, or empty string if none.
    """
    try:
        collection = _get_library_collection()

        if collection.count() == 0:
            return ""

        results = collection.query(
            query_texts=[topic],
            n_results=min(k, collection.count()),
        )

        if not results or not results.get("documents"):
            return ""

        docs = results["documents"][0]
        metas = results.get("metadatas", [[]])[0]

        chunks = []
        for doc, meta in zip(docs, metas):
            filename = meta.get("filename", "Unknown document")
            chunks.append(f"[From your library: {filename}]\n{doc}")

        merged = "\n\n---\n\n".join(chunks)
        print(f"[Library] Retrieved {len(chunks)} relevant chunks for topic '{topic}'")
        return merged

    except Exception as e:
        print(f"[Library] Query failed: {e}")
        return ""


def list_library_documents() -> list[str]:
    """
    Returns a sorted list of unique document filenames in the library.
    """
    try:
        collection = _get_library_collection()
        if collection.count() == 0:
            return []

        results = collection.get(include=["metadatas"])
        filenames = sorted(set(
            m.get("filename", "Unknown")
            for m in results.get("metadatas", [])
        ))
        return filenames

    except Exception as e:
        print(f"[Library] list_documents failed: {e}")
        return []


def get_library_count() -> int:
    """Returns the number of chunks stored in the personal library."""
    try:
        return _get_library_collection().count()
    except Exception:
        return 0


def delete_from_library(filename: str) -> bool:
    """
    Remove all chunks for a specific document from the library.

    Args:
        filename: The filename to delete

    Returns:
        True if deletion succeeded, False otherwise.
    """
    try:
        collection = _get_library_collection()
        existing = collection.get(where={"filename": filename})
        if existing["ids"]:
            collection.delete(ids=existing["ids"])
            print(f"[Library] Deleted '{filename}' ({len(existing['ids'])} chunks)")
            return True
        return False
    except Exception as e:
        print(f"[Library] delete failed: {e}")
        return False


def clear_library() -> bool:
    """Wipes the entire personal research library."""
    global _library_collection
    try:
        if _chroma_client:
            _chroma_client.delete_collection(LIBRARY_COLLECTION_NAME)
            _library_collection = None
            print("[Library] Library cleared.")
        return True
    except Exception as e:
        print(f"[Library] clear failed: {e}")
        return False
