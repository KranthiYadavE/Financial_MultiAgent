import time
from typing import Any

from fastapi import HTTPException
from prometheus_client import Counter, Histogram
from pydantic import BaseModel, Field
from qdrant_client import QdrantClient
from sentence_transformers import SentenceTransformer

from shared.config import Settings
from shared.fastapi_app import create_service_app
from shared.llm_client import OllamaClient
from shared.logging_setup import setup_logging

settings = Settings()
logger = setup_logging("rag-agent", settings.log_level)
app = create_service_app("rag-agent", log_level=settings.log_level)

RAG_REQUESTS = Counter("rag_requests_total", "Total RAG requests")
RAG_LATENCY = Histogram("rag_latency_seconds", "RAG query latency")
VECTOR_LATENCY = Histogram("vector_search_latency_seconds", "Qdrant search latency")

_embedder: SentenceTransformer | None = None
_qdrant: QdrantClient | None = None


def get_embedder() -> SentenceTransformer:
    global _embedder
    if _embedder is None:
        _embedder = SentenceTransformer(settings.embedding_model)
    return _embedder


def get_qdrant() -> QdrantClient:
    global _qdrant
    if _qdrant is None:
        _qdrant = QdrantClient(host=settings.qdrant_host, port=settings.qdrant_port)
    return _qdrant


class RAGRequest(BaseModel):
    question: str = Field(..., min_length=3, max_length=500)
    top_k: int = Field(default=3, ge=1, le=10)


class SourceDoc(BaseModel):
    doc_id: str
    title: str
    category: str
    score: float
    snippet: str


class RAGResponse(BaseModel):
    answer: str
    sources: list[SourceDoc]
    latency_ms: float
    llm_used: bool


RAG_PROMPT = """Answer the user's question using ONLY the context below.
If the context does not contain the answer, say "I don't have that information in our policies."
Be concise and cite the policy topic when relevant.

Context:
{context}

Question: {question}

Answer:"""


@app.post("/ask", response_model=RAGResponse)
async def ask_policy(req: RAGRequest):
    start = time.perf_counter()
    RAG_REQUESTS.inc()

    try:
        embedder = get_embedder()
        qdrant = get_qdrant()

        vec_start = time.perf_counter()
        query_vector = embedder.encode(req.question).tolist()
        hits = qdrant.search(
            collection_name=settings.qdrant_collection,
            query_vector=query_vector,
            limit=req.top_k,
        )
        VECTOR_LATENCY.observe(time.perf_counter() - vec_start)

        if not hits:
            raise HTTPException(status_code=404, detail="No documents in vector DB. Run data-init first.")

        sources: list[SourceDoc] = []
        context_parts: list[str] = []
        for hit in hits:
            payload = hit.payload or {}
            snippet = (payload.get("content") or "")[:300]
            sources.append(
                SourceDoc(
                    doc_id=str(payload.get("doc_id", "")),
                    title=str(payload.get("title", "")),
                    category=str(payload.get("category", "")),
                    score=round(hit.score, 4),
                    snippet=snippet,
                )
            )
            context_parts.append(f"[{payload.get('title')}]: {payload.get('content')}")

        context = "\n\n".join(context_parts)
        llm_used = False
        answer = _extractive_fallback(sources)

        client = OllamaClient(settings)
        if await client.is_available():
            try:
                answer = await client.generate(
                    RAG_PROMPT.format(context=context, question=req.question),
                    system="You are a helpful bank policy assistant.",
                )
                llm_used = True
            except Exception as exc:
                logger.warning("Ollama RAG failed, using extractive fallback", extra={"error": str(exc)})

        latency = (time.perf_counter() - start) * 1000
        RAG_LATENCY.observe(latency / 1000)
        logger.info("RAG query complete", extra={"sources": len(sources), "llm_used": llm_used})

        return RAGResponse(
            answer=answer,
            sources=sources,
            latency_ms=round(latency, 2),
            llm_used=llm_used,
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("RAG failed", extra={"error": str(exc)})
        raise HTTPException(status_code=500, detail=str(exc)) from exc


def _extractive_fallback(sources: list[SourceDoc]) -> str:
    if not sources:
        return "No relevant policy documents found."
    top = sources[0]
    return f"Based on '{top.title}': {top.snippet}..."


@app.get("/collection-info")
async def collection_info() -> dict[str, Any]:
    qdrant = get_qdrant()
    if not qdrant.collection_exists(settings.qdrant_collection):
        return {"exists": False, "points_count": 0}
    info = qdrant.get_collection(settings.qdrant_collection)
    return {
        "exists": True,
        "points_count": info.points_count,
        "collection": settings.qdrant_collection,
    }
