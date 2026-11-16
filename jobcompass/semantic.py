"""Local MiniLM embeddings; exact cosine search with deterministic hybrid scores."""

import hashlib
import json
import math
import os
from functools import lru_cache
from pathlib import Path

from .ingest import _save
from .search import description_text, filter_jobs, rank_jobs, sort_ranked

MODEL = "sentence-transformers/all-MiniLM-L6-v2"
DIMENSIONS = 384


class SemanticUnavailable(RuntimeError):
    pass


def document(row):
    # Put identifying context first because this model truncates long text.
    return "\n".join([row["title"], row["title"], row["company"],
                      " ".join(row.get("categories") or []), row.get("excerpt") or "",
                      description_text(row)[:4000]])


def content_hash(row):
    return hashlib.sha256(document(row).encode()).hexdigest()


@lru_cache(maxsize=1)
def embedding_model():
    try:
        from fastembed import TextEmbedding
        cache = Path(os.environ.get("JOBCOMPASS_MODEL_CACHE", "data/models"))
        return TextEmbedding(model_name=MODEL, cache_dir=str(cache), threads=2)
    except Exception as error:
        raise SemanticUnavailable("Embedding model unavailable; install the semantic extra and run the embed command.") from error


def validate_vector(vector):
    values = [float(value) for value in vector]
    if len(values) != DIMENSIONS or not all(math.isfinite(value) for value in values) or not any(values):
        raise ValueError("Expected a finite, nonzero 384-dimensional vector")
    norm = math.hypot(*values)
    if not math.isfinite(norm) or norm == 0:
        raise ValueError("Invalid vector magnitude")
    return [value / norm for value in values]


def embed_texts(texts):
    if not texts:
        return []
    try:
        return [validate_vector(value) for value in embedding_model().embed(texts)]
    except SemanticUnavailable:
        raise
    except Exception as error:
        raise SemanticUnavailable("Embedding generation failed; deterministic recommendations remain available.") from error


def build_index(snapshot, data_dir):
    rows = snapshot["records"]
    vectors = embed_texts([document(row) for row in rows])
    if len(vectors) != len(rows):
        raise SemanticUnavailable("Embedding count did not match the source records")
    entries = [{"source": row["source"], "source_id": row["source_id"],
                "content_hash": content_hash(row), "vector": vector} for row, vector in zip(rows, vectors)]
    index = {"model": MODEL, "dimensions": DIMENSIONS, "rows": entries}
    _save(Path(data_dir) / "embeddings.json", index)
    if os.environ.get("DATABASE_URL"):
        from .database import save_vectors
        save_vectors(entries, MODEL)
    return {"model": MODEL, "dimensions": DIMENSIONS, "indexed": len(entries)}


def cosine(left, right):
    return sum(a*b for a, b in zip(left, right)) / math.sqrt(sum(a*a for a in left) * sum(b*b for b in right))


def semantic_scores(records, query):
    query_vector = embed_texts([query])[0]
    if os.environ.get("DATABASE_URL"):
        from .database import vector_scores
        try:
            scores = vector_scores(records, query_vector, MODEL)
        except Exception as error:
            raise SemanticUnavailable("PostgreSQL vector retrieval failed; check migrations and connection.") from error
    else:
        path = Path(os.environ.get("JOBCOMPASS_DATA_DIR", "data")) / "embeddings.json"
        try:
            index = json.loads(path.read_text())
            if index["model"] != MODEL or index["dimensions"] != DIMENSIONS:
                raise ValueError("Wrong model")
            entries = {(row["source"], row["source_id"]): row for row in index["rows"]}
            scores = {}
            for row in records:
                entry = entries.get((row["source"], row["source_id"]))
                if entry and entry["content_hash"] == content_hash(row):
                    scores[(row["source"], row["source_id"])] = cosine(query_vector, validate_vector(entry["vector"]))
        except (OSError, ValueError, KeyError, TypeError) as error:
            raise SemanticUnavailable("Semantic index missing or invalid; run python -m jobcompass.manage embed.") from error
    if len(scores) != len(records):
        raise SemanticUnavailable("Semantic index is incomplete or outdated; run python -m jobcompass.manage embed.")
    return scores


def hybrid_rank(records, query, similarities):
    ranked = rank_jobs(records, query)
    for row in ranked:
        similarity = max(-1.0, min(1.0, similarities[(row["source"], row["source_id"])]))
        lexical = row["score"]
        row["score_components"] = {"semantic": round(70 * max(0, similarity), 6), "lexical": round(0.3 * lexical, 6)}
        row["semantic_similarity"] = round(similarity, 6)
        row["score"] = round(sum(row["score_components"].values()), 6)
    return sort_ranked(ranked)


def recommend_semantic(records, params, now=None):
    if not params.q:
        raise ValueError("Semantic search requires q")
    candidates = filter_jobs(records, params, now, keyword_mode="none")
    if not candidates:
        return []
    return hybrid_rank(candidates, params.q, semantic_scores(candidates, params.q))
