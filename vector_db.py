from qdrant_client import QdrantClient
from qdrant_client.models import (
    VectorParams,
    SparseVectorParams,
    SparseIndexParams,
    Distance,
    PointStruct,
    SparseVector,
    Filter,
    FieldCondition,
    MatchValue,
    Prefetch,
    FusionQuery,
    Fusion,
)

from data_loader import EMBED_DIM


def build_access_filter(user_id: str) -> Filter:
    """Return a Qdrant filter that allows public docs OR docs owned by user_id."""
    return Filter(
        should=[
            FieldCondition(key="visibility", match=MatchValue(value="public")),
            FieldCondition(key="user_id", match=MatchValue(value=user_id)),
        ]
    )


class QdrantStorage:
    def __init__(self, url: str = "http://localhost:6333", collection: str = "docs"):
        self.client = QdrantClient(url=url, timeout=30)
        self.collection = collection
        if not self.client.collection_exists(self.collection):
            self.client.create_collection(
                collection_name=self.collection,
                vectors_config={"dense": VectorParams(size=EMBED_DIM, distance=Distance.COSINE)},
                sparse_vectors_config={
                    "sparse": SparseVectorParams(index=SparseIndexParams(on_disk=False))
                },
            )

    def upsert(self, ids: list, dense_vecs: list, sparse_vecs: list, payloads: list) -> None:
        points = [
            PointStruct(
                id=ids[i],
                vector={
                    "dense": dense_vecs[i],
                    "sparse": SparseVector(
                        indices=sparse_vecs[i]["indices"],
                        values=sparse_vecs[i]["values"],
                    ),
                },
                payload=payloads[i],
            )
            for i in range(len(ids))
        ]
        self.client.upsert(self.collection, points=points)

    def delete_by_source(self, source_id: str) -> None:
        """Remove all vectors for a given source before re-ingesting."""
        self.client.delete(
            collection_name=self.collection,
            points_selector=Filter(
                must=[FieldCondition(key="source", match=MatchValue(value=source_id))]
            ),
        )

    def search(
        self,
        dense_vec: list[float],
        sparse_vec: dict,
        top_k: int = 5,
        access_filter: Filter | None = None,
    ) -> dict:
        """Hybrid search combining dense cosine similarity and BM25 with RRF fusion."""
        prefetch = [
            Prefetch(query=dense_vec, using="dense", limit=top_k * 2),
            Prefetch(
                query=SparseVector(
                    indices=sparse_vec["indices"], values=sparse_vec["values"]
                ),
                using="sparse",
                limit=top_k * 2,
            ),
        ]
        response = self.client.query_points(
            collection_name=self.collection,
            prefetch=prefetch,
            query=FusionQuery(fusion=Fusion.RRF),
            query_filter=access_filter,
            with_payload=True,
            with_vectors=False,
            limit=top_k,
        )

        contexts, sources, scores = [], set(), []
        for point in response.points:
            payload = getattr(point, "payload", None) or {}
            text = payload.get("text", "")
            source = payload.get("source", "")
            score = getattr(point, "score", 0.0)
            if text:
                contexts.append(text)
                sources.add(source)
                scores.append(round(score, 4))

        return {"contexts": contexts, "sources": list(sources), "scores": scores}
