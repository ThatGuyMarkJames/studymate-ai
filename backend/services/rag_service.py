import os
import json
import pickle
import hashlib
import numpy as np
from pathlib import Path
from typing import List, Tuple, Optional
import PyPDF2
import faiss
from sentence_transformers import SentenceTransformer
from dotenv import load_dotenv

load_dotenv()

UPLOAD_DIR   = Path(os.getenv("UPLOAD_DIR", "uploads"))
VECTOR_DIR   = UPLOAD_DIR / "vectors"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
VECTOR_DIR.mkdir(parents=True, exist_ok=True)

CHUNK_SIZE    = 600    # characters per chunk
CHUNK_OVERLAP = 100   # character overlap between chunks
TOP_K         = 4     # number of chunks to retrieve

# Load model once at module level (CPU-friendly)
print("Loading embedding model (one-time)...")
_embedder = SentenceTransformer("all-MiniLM-L6-v2")
print("Embedding model ready.")



def extract_text(file_path: str, file_type: str) -> str:
    """Extract plain text from PDF or TXT file."""
    if file_type == "pdf":
        text = []
        with open(file_path, "rb") as f:
            reader = PyPDF2.PdfReader(f)
            for page in reader.pages:
                t = page.extract_text()
                if t:
                    text.append(t.strip())
        return "\n".join(text)
    else:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            return f.read()



def chunk_text(text: str) -> List[str]:
    """Split text into overlapping chunks."""
    chunks = []
    start  = 0
    while start < len(text):
        end = start + CHUNK_SIZE
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        start += CHUNK_SIZE - CHUNK_OVERLAP
    return chunks



def _index_path(index_id: str) -> Tuple[Path, Path]:
    return VECTOR_DIR / f"{index_id}.faiss", VECTOR_DIR / f"{index_id}.meta"


def build_index(chunks: List[str], index_id: str) -> int:
    """Embed chunks and persist FAISS index + metadata."""
    embeddings = _embedder.encode(chunks, show_progress_bar=False)
    embeddings = np.array(embeddings, dtype="float32")
    faiss.normalize_L2(embeddings)

    dim   = embeddings.shape[1]
    index = faiss.IndexFlatIP(dim)   # Inner-product (cosine after normalization)
    index.add(embeddings)

    idx_path, meta_path = _index_path(index_id)
    faiss.write_index(index, str(idx_path))
    with open(meta_path, "wb") as f:
        pickle.dump(chunks, f)

    return len(chunks)


def retrieve_context(query: str, index_ids: List[str], top_k: int = TOP_K) -> List[str]:
    """Retrieve top-k relevant chunks across multiple document indexes."""
    if not index_ids:
        return []

    q_emb = _embedder.encode([query], show_progress_bar=False)
    q_emb = np.array(q_emb, dtype="float32")
    faiss.normalize_L2(q_emb)

    all_results = []   # (score, chunk_text)

    for idx_id in index_ids:
        idx_path, meta_path = _index_path(idx_id)
        if not idx_path.exists() or not meta_path.exists():
            continue
        index = faiss.read_index(str(idx_path))
        with open(meta_path, "rb") as f:
            chunks = pickle.load(f)

        k = min(top_k, index.ntotal)
        scores, indices = index.search(q_emb, k)
        for score, i in zip(scores[0], indices[0]):
            if i < len(chunks):
                all_results.append((float(score), chunks[i]))

    # Sort by score descending, return top_k unique chunks
    all_results.sort(key=lambda x: x[0], reverse=True)
    seen   = set()
    result = []
    for _, chunk in all_results:
        key = chunk[:80]
        if key not in seen:
            seen.add(key)
            result.append(chunk)
        if len(result) >= top_k:
            break

    return result


def delete_index(index_id: str):
    """Remove vector files for a deleted document."""
    idx_path, meta_path = _index_path(index_id)
    for p in [idx_path, meta_path]:
        if p.exists():
            p.unlink()



def save_upload(file_bytes: bytes, original_name: str, user_id: int) -> Tuple[str, str]:
    """Save uploaded file and return (saved_filename, file_type)."""
    ext  = original_name.rsplit(".", 1)[-1].lower() if "." in original_name else "txt"
    hash_ = hashlib.md5(file_bytes).hexdigest()[:8]
    filename = f"u{user_id}_{hash_}_{original_name}"
    path = UPLOAD_DIR / filename
    with open(path, "wb") as f:
        f.write(file_bytes)
    return filename, ext


def process_document(filename: str, file_type: str) -> Tuple[List[str], str]:
    """Full pipeline: extract → chunk → return (chunks, index_id)."""
    path     = UPLOAD_DIR / filename
    text     = extract_text(str(path), file_type)
    chunks   = chunk_text(text)
    index_id = hashlib.md5(filename.encode()).hexdigest()[:16]
    build_index(chunks, index_id)
    return chunks, index_id
