"""Embed FAQ/policy docs and upsert into Qdrant."""

import json
import uuid
from pathlib import Path

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams
from sentence_transformers import SentenceTransformer

from shared.config import Settings


def ingest_docs() -> None:
    settings = Settings()
    docs_path = Path(__file__).resolve().parents[1] / "data" / "docs" / "faq_policies.json"
    docs = json.loads(docs_path.read_text(encoding="utf-8"))

    model = SentenceTransformer(settings.embedding_model)
    client = QdrantClient(host=settings.qdrant_host, port=settings.qdrant_port)

    collection = settings.qdrant_collection
    dim = model.get_sentence_embedding_dimension()

    if not client.collection_exists(collection):
        client.create_collection(
            collection_name=collection,
            vectors_config=VectorParams(size=dim, distance=Distance.COSINE),
        )
    else:
        client.delete_collection(collection)
        client.create_collection(
            collection_name=collection,
            vectors_config=VectorParams(size=dim, distance=Distance.COSINE),
        )

    points = []
    for doc in docs:
        text = f"{doc['title']}\n{doc['content']}"
        vector = model.encode(text).tolist()
        points.append(
            PointStruct(
                id=str(uuid.uuid5(uuid.NAMESPACE_DNS, doc["id"])),
                vector=vector,
                payload={
                    "doc_id": doc["id"],
                    "title": doc["title"],
                    "category": doc["category"],
                    "content": doc["content"],
                },
            )
        )

    client.upsert(collection_name=collection, points=points)
    print(f"Ingested {len(points)} documents into Qdrant collection '{collection}'")


if __name__ == "__main__":
    ingest_docs()
