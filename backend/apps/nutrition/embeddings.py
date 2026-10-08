"""Food-name embeddings for search. They are not nutrition values."""

from pgvector.django import CosineDistance

from .models import FoodEmbedding

EMBEDDING_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
EMBEDDING_DIMENSIONS = 384


def passage_text(food_name: str) -> str:
    return food_name


def query_text(query: str) -> str:
    return query


def embed_texts(texts: list[str]) -> list[list[float]]:
    from fastembed import TextEmbedding

    model = TextEmbedding(model_name=EMBEDDING_MODEL)
    return [vector.tolist() for vector in model.embed(texts)]


def similar_foods(query: str, version, limit: int = 8, embed=None):
    if not FoodEmbedding.objects.filter(dataset_version=version, model_name=EMBEDDING_MODEL).exists():
        return []
    embed_fn = embed or (lambda values: embed_texts([query_text(values[0])]))
    vector = embed_fn([query])[0]
    rows = (
        FoodEmbedding.objects.filter(dataset_version=version, model_name=EMBEDDING_MODEL)
        .select_related("food")
        .annotate(distance=CosineDistance("embedding", vector))
        .order_by("distance")[:limit]
    )
    return [row.food for row in rows if row.distance is not None and row.distance <= 0.45]
