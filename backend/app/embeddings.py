"""Deterministic project-chunk embeddings with local and optional pgvector search.

The local JSON cache is the zero-config default. When ``DATABASE_URL`` is set
and ``psycopg`` is installed, the same public functions also sync and query the
Supabase/PostgreSQL ``project_chunks`` table. Callers never need to change.
"""

from __future__ import annotations

import json
import logging
import math
import os
import tempfile
from pathlib import Path
from typing import Any, Protocol
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import httpx
from dotenv import load_dotenv

from app.projects import get_project, iter_project_chunks

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

CACHE_FILE = Path(__file__).parent / "embeddings_cache.json"
PG_SCHEMA_FILE = Path(__file__).resolve().parent.parent / "sql" / "init_pgvector.sql"
EMBEDDING_MODEL = os.getenv("GEMINI_EMBEDDING_MODEL", "gemini-embedding-001").strip() or "gemini-embedding-001"
FALLBACK_EMBEDDING_MODEL = "gemini-embedding-2"
EMBEDDING_DIMENSIONS = 768
GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta"
DEFAULT_TIMEOUT_SECONDS = 30.0

logger = logging.getLogger(__name__)

_active_model: str | None = None


class EmbeddingError(RuntimeError):
    """A safe, user-facing failure from the embedding layer."""


class EmbeddingStore(Protocol):
    def load(self) -> dict[str, dict[str, Any]]: ...

    def save(self, records: dict[str, dict[str, Any]]) -> None: ...


class JsonEmbeddingStore:
    def __init__(self, path: Path = CACHE_FILE) -> None:
        self.path = path

    def load(self) -> dict[str, dict[str, Any]]:
        if not self.path.exists():
            return {}
        with open(self.path, "r", encoding="utf-8") as handle:
            data = json.load(handle)
        return data if isinstance(data, dict) else {}

    def save(self, records: dict[str, dict[str, Any]]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        descriptor, temp_path = tempfile.mkstemp(
            dir=self.path.parent, prefix=f".{self.path.name}.", suffix=".tmp"
        )
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
                json.dump(records, handle, ensure_ascii=False, indent=2)
            os.replace(temp_path, self.path)
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)


def _store() -> EmbeddingStore:
    return JsonEmbeddingStore(CACHE_FILE)


def _api_key() -> str:
    key = os.getenv("GEMINI_API_KEY", "").strip()
    if not key:
        raise EmbeddingError("GEMINI_API_KEY is not configured.")
    return key


def _timeout_seconds() -> float:
    try:
        return max(1.0, float(os.getenv("EMBEDDING_TIMEOUT_SECONDS", "30")))
    except ValueError:
        return DEFAULT_TIMEOUT_SECONDS


def _request_embedding(model: str, text: str) -> list[float]:
    body: dict[str, Any] = {"content": {"parts": [{"text": text}]}}
    if model != "text-embedding-004":
        body["outputDimensionality"] = EMBEDDING_DIMENSIONS

    response = httpx.post(
        f"{GEMINI_BASE_URL}/models/{model}:embedContent",
        params={"key": _api_key()},
        json=body,
        timeout=_timeout_seconds(),
    )
    response.raise_for_status()
    return response.json()["embedding"]["values"]


def embed_text(text: str) -> list[float]:
    global _active_model

    cleaned = (text or "").strip()
    if not cleaned:
        raise EmbeddingError("Cannot embed empty text.")

    if _active_model:
        models = [_active_model]
    else:
        models = list(dict.fromkeys((EMBEDDING_MODEL, FALLBACK_EMBEDDING_MODEL)))

    values: Any = None
    last_error: EmbeddingError | None = None

    for index, model in enumerate(models):
        try:
            values = _request_embedding(model, cleaned)
            _active_model = model
            break
        except httpx.HTTPStatusError as exc:
            status = exc.response.status_code if exc.response is not None else None
            last_error = EmbeddingError(
                f"Gemini embedding request failed with HTTP {status}."
            )
            if index < len(models) - 1 and status in (400, 404):
                logger.warning(
                    "Embedding model %s is unavailable (HTTP %s); trying %s.",
                    model,
                    status,
                    models[index + 1],
                )
                continue
            raise last_error from exc
        except (httpx.HTTPError, KeyError, TypeError, ValueError) as exc:
            raise EmbeddingError("Gemini returned an invalid embedding response.") from exc

    if values is None:
        raise last_error or EmbeddingError("Gemini returned no embedding.")

    if not isinstance(values, list) or len(values) != EMBEDDING_DIMENSIONS:
        raise EmbeddingError("Gemini returned an embedding with an unexpected size.")

    return [float(value) for value in values]


def _project_title(project_id: str) -> str:
    project = get_project(project_id)
    return project.title if project else project_id


def _make_record(chunk: dict[str, Any], vector: list[float]) -> dict[str, Any]:
    return {
        "sha256": chunk["hash"],
        "project_slug": chunk["project_id"],
        "project_title": _project_title(chunk["project_id"]),
        "section": chunk["chunk_type"],
        "text": chunk["content"],
        "vector": vector,
    }


def _is_complete_record(record: Any) -> bool:
    if not isinstance(record, dict):
        return False
    required = ("sha256", "project_slug", "project_title", "section", "text", "vector")
    if any(field not in record for field in required):
        return False
    vector = record["vector"]
    return isinstance(vector, list) and len(vector) == EMBEDDING_DIMENSIONS


def sync_embeddings() -> dict[str, int | bool]:
    store = _store()
    cache = store.load()
    chunks = list(iter_project_chunks())
    current_hashes = {chunk["hash"] for chunk in chunks}

    pruned = sum(1 for digest in cache if digest not in current_hashes)
    if pruned:
        cache = {digest: record for digest, record in cache.items() if digest in current_hashes}

    embedded = 0
    cached = 0
    for chunk in chunks:
        digest = chunk["hash"]
        if _is_complete_record(cache.get(digest)):
            cached += 1
            continue
        cache[digest] = _make_record(chunk, embed_text(chunk["content"]))
        embedded += 1

    if embedded or pruned:
        store.save(cache)

    postgres = _sync_postgres(cache)
    return {
        "embedded": embedded,
        "cached": cached,
        "pruned": pruned,
        "total": len(chunks),
        "postgres": postgres,
    }


def cosine_similarity(vec1: list[float], vec2: list[float]) -> float:
    if len(vec1) != len(vec2):
        raise ValueError("Vectors must have the same length.")
    dot_product = sum(a * b for a, b in zip(vec1, vec2))
    norm_a = math.sqrt(sum(a * a for a in vec1))
    norm_b = math.sqrt(sum(b * b for b in vec2))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return dot_product / (norm_a * norm_b)


def _clamp_score(score: float) -> float:
    return max(0.0, min(1.0, score))


def _result(record: dict[str, Any], score: float) -> dict[str, Any]:
    return {
        "sha256": record["sha256"],
        "project_slug": record["project_slug"],
        "project_title": record["project_title"],
        "section": record["section"],
        "text": record["text"],
        "score": _clamp_score(score),
    }


def _search_local(query_vector: list[float], top_k: int) -> list[dict[str, Any]]:
    records = [
        record
        for record in _store().load().values()
        if _is_complete_record(record)
    ]
    if not records:
        raise EmbeddingError(
            "No cached embeddings found. Run sync_embeddings() before searching."
        )

    results = [
        _result(record, cosine_similarity(query_vector, record["vector"]))
        for record in records
    ]
    results.sort(key=lambda item: item["score"], reverse=True)
    return results[:top_k]


def search_similar_chunks(query: str, top_k: int = 4) -> list[dict[str, Any]]:
    top_k = max(1, int(top_k))
    query_vector = embed_text(query)

    postgres_results = _search_postgres(query_vector, top_k)
    if postgres_results is not None:
        return postgres_results

    return _search_local(query_vector, top_k)


def _vector_literal(vector: list[float]) -> str:
    return "[" + ",".join(repr(float(value)) for value in vector) + "]"


def _database_url() -> str | None:
    """Return a psycopg-safe Postgres URL, preferring DIRECT_URL.

    Supabase's Prisma snippets can include ``?pgbouncer=true`` and port 6543.
    psycopg rejects that unknown URI parameter, so it is removed here.
    """
    for name in ("DIRECT_URL", "DATABASE_URL"):
        candidate = os.getenv(name, "").strip()
        if not candidate:
            continue
        parsed = urlsplit(candidate)
        if parsed.scheme not in ("postgres", "postgresql"):
            logger.warning(
                "%s is not a PostgreSQL connection string; ignoring it.", name
            )
            continue
        query = [
            (key, value)
            for key, value in parse_qsl(parsed.query, keep_blank_values=True)
            if key.lower() != "pgbouncer"
        ]
        return urlunsplit(
            (parsed.scheme, parsed.netloc, parsed.path, urlencode(query), parsed.fragment)
        )
    return None


def _uses_transaction_pooler(url: str) -> bool:
    return urlsplit(url).port == 6543


def _connect_postgres() -> Any | None:
    url = _database_url()
    if not url:
        return None
    try:
        import psycopg
    except ImportError:
        logger.warning(
            "DATABASE_URL is set but psycopg is not installed; using the local cache."
        )
        return None
    connect_kwargs: dict[str, Any] = {"connect_timeout": 5}
    if _uses_transaction_pooler(url):
        # PgBouncer transaction pooling cannot reuse prepared statements.
        connect_kwargs["prepare_threshold"] = None
    try:
        connection = psycopg.connect(url, **connect_kwargs)
        connection.autocommit = True
        return connection
    except Exception as exc:
        logger.warning("PostgreSQL is unreachable (%s); using the local cache.", exc)
        return None


def _pg_schema_statements() -> list[str]:
    if not PG_SCHEMA_FILE.exists():
        raise EmbeddingError(f"Missing pgvector schema file: {PG_SCHEMA_FILE}")
    sql = PG_SCHEMA_FILE.read_text(encoding="utf-8")
    return [statement.strip() for statement in sql.split(";") if statement.strip()]


def _ensure_pg_schema(connection: Any) -> None:
    with connection.cursor() as cursor:
        for statement in _pg_schema_statements():
            cursor.execute(statement)


def _sync_postgres(cache: dict[str, dict[str, Any]]) -> bool:
    connection = _connect_postgres()
    if connection is None:
        return False

    upsert_sql = (
        "INSERT INTO project_chunks "
        "(chunk_hash, project_id, chunk_type, content, embedding) "
        "VALUES (%s, %s, %s, %s, %s::vector) "
        "ON CONFLICT (chunk_hash) DO UPDATE SET "
        "project_id = EXCLUDED.project_id, "
        "chunk_type = EXCLUDED.chunk_type, "
        "content = EXCLUDED.content, "
        "embedding = EXCLUDED.embedding"
    )

    try:
        _ensure_pg_schema(connection)
        records = list(cache.values())
        with connection.cursor() as cursor:
            for record in records:
                cursor.execute(
                    upsert_sql,
                    (
                        record["sha256"],
                        record["project_slug"],
                        record["section"],
                        record["text"],
                        _vector_literal(record["vector"]),
                    ),
                )
            if records:
                cursor.execute(
                    "DELETE FROM project_chunks WHERE NOT (chunk_hash = ANY(%s))",
                    ([record["sha256"] for record in records],),
                )
            else:
                cursor.execute("DELETE FROM project_chunks")
        return True
    except Exception as exc:
        logger.warning("PostgreSQL sync failed (%s); the local cache was kept.", exc)
        return False
    finally:
        connection.close()


def _search_postgres(
    query_vector: list[float], top_k: int
) -> list[dict[str, Any]] | None:
    connection = _connect_postgres()
    if connection is None:
        return None

    vector = _vector_literal(query_vector)
    query_sql = (
        "SELECT chunk_hash, project_id, chunk_type, content, "
        "1 - (embedding <=> %s::vector) AS score "
        "FROM project_chunks "
        "ORDER BY embedding <=> %s::vector "
        "LIMIT %s"
    )

    try:
        _ensure_pg_schema(connection)
        with connection.cursor() as cursor:
            cursor.execute(query_sql, (vector, vector, top_k))
            rows = cursor.fetchall()
    except Exception as exc:
        logger.warning(
            "PostgreSQL search failed (%s); falling back to the local cache.", exc
        )
        return None
    finally:
        connection.close()

    if not rows:
        logger.warning("PostgreSQL has no project chunks; falling back to the local cache.")
        return None

    return [
        {
            "sha256": chunk_hash,
            "project_slug": project_id,
            "project_title": _project_title(project_id),
            "section": chunk_type,
            "text": content,
            "score": _clamp_score(float(score)),
        }
        for chunk_hash, project_id, chunk_type, content, score in rows
    ]
