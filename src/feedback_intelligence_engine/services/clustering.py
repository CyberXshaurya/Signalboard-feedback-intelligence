from __future__ import annotations

import math
import re
from dataclasses import dataclass

import httpx
import numpy as np
from sklearn.cluster import AgglomerativeClustering, KMeans
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from ..config import Settings
from ..models import FeedbackItem

REDACTION_NOISE_RE = re.compile(
    r"\b(?:x{2,}|xx/xx/xxxx|section|consumer|company|customer|complaint|account)\b",
    re.IGNORECASE,
)


@dataclass
class CandidateCluster:
    cluster_key: str
    item_ids: list[str]
    representative_ids: list[str]
    coherence: float
    pattern_type: str
    unique_feedback_count: int
    dominant_product_area: str


@dataclass
class ClusteringResult:
    clusters: list[CandidateCluster]
    diagnostics: dict


def _clean_document(item: FeedbackItem, metadata_weight: int) -> str:
    clean_text = REDACTION_NOISE_RE.sub(" ", item.feedback_text_masked)
    area_context = (item.product_area + " ") * metadata_weight
    return f"{area_context}{clean_text}"


def _openai_embeddings(items: list[FeedbackItem], settings: Settings) -> np.ndarray:
    try:
        from openai import OpenAI
    except ImportError as exc:
        raise RuntimeError("The openai package is required for OpenAI embeddings") from exc
    client = OpenAI(api_key=settings.openai_api_key)
    inputs = [
        f"Product area: {item.product_area}\nCustomer feedback: "
        f"{item.feedback_text_masked[: settings.max_ai_text_chars]}"
        for item in items
    ]
    vectors: list[list[float]] = []
    for start in range(0, len(inputs), settings.embedding_batch_size):
        batch = inputs[start : start + settings.embedding_batch_size]
        response = client.embeddings.create(model=settings.openai_embedding_model, input=batch)
        vectors.extend(row.embedding for row in response.data)
    if len(vectors) != len(items):
        raise ValueError("Embedding provider returned an unexpected number of vectors")
    return np.asarray(vectors, dtype=np.float32)




def _ollama_embeddings(items: list[FeedbackItem], settings: Settings) -> np.ndarray:
    url = settings.ollama_base_url.rstrip("/") + "/api/embed"
    inputs = [
        f"Product area: {item.product_area}\nCustomer feedback: "
        f"{item.feedback_text_masked[: settings.max_ai_text_chars]}"
        for item in items
    ]
    vectors: list[list[float]] = []
    with httpx.Client(timeout=settings.ai_request_timeout_seconds) as client:
        for start in range(0, len(inputs), settings.embedding_batch_size):
            batch = inputs[start : start + settings.embedding_batch_size]
            response = client.post(
                url,
                json={"model": settings.ollama_embedding_model, "input": batch, "truncate": True},
            )
            response.raise_for_status()
            vectors.extend(response.json().get("embeddings", []))
    if len(vectors) != len(items):
        raise ValueError("Ollama returned an unexpected number of embedding vectors")
    return np.asarray(vectors, dtype=np.float32)


def _tfidf_embeddings(items: list[FeedbackItem], settings: Settings) -> tuple[np.ndarray, int]:
    documents = [_clean_document(item, settings.metadata_weight) for item in items]
    vectorizer = TfidfVectorizer(
        stop_words="english",
        ngram_range=(1, 2),
        max_features=12_000,
        sublinear_tf=True,
        strip_accents="unicode",
    )
    matrix = vectorizer.fit_transform(documents)
    return matrix.toarray(), len(vectorizer.get_feature_names_out())


def _split_oversized_groups(
    groups: list[list[int]], matrix: np.ndarray, max_cluster_size: int
) -> list[list[int]]:
    refined: list[list[int]] = []
    pending = list(groups)
    while pending:
        indices = pending.pop(0)
        if len(indices) <= max_cluster_size:
            refined.append(indices)
            continue
        n_clusters = max(2, math.ceil(len(indices) / max_cluster_size) + 1)
        local = matrix[indices]
        labels = KMeans(n_clusters=n_clusters, random_state=42, n_init="auto").fit_predict(local)
        children = [
            [indices[pos] for pos, value in enumerate(labels) if int(value) == label]
            for label in sorted(set(int(value) for value in labels))
        ]
        if len(children) == 1:
            refined.extend(
                indices[start : start + max_cluster_size]
                for start in range(0, len(indices), max_cluster_size)
            )
        else:
            pending.extend(children)
    return refined


def _select_representatives(
    items: list[FeedbackItem], matrix: np.ndarray, max_items: int
) -> list[str]:
    if len(items) <= max_items:
        return [item.id for item in items]
    centroid = matrix.mean(axis=0, keepdims=True)
    centrality = cosine_similarity(matrix, centroid).ravel()
    ranked = list(np.argsort(-centrality))

    selected: list[int] = []
    seen_sources: set[str] = set()
    seen_user_types: set[str] = set()
    seen_dates: set[str] = set()
    for idx in ranked:
        item = items[idx]
        month = item.feedback_date.strftime("%Y-%m")
        if (
            item.source not in seen_sources
            or item.user_type not in seen_user_types
            or month not in seen_dates
        ):
            selected.append(idx)
            seen_sources.add(item.source)
            seen_user_types.add(item.user_type)
            seen_dates.add(month)
        if len(selected) >= max_items:
            break
    for idx in ranked:
        if idx not in selected:
            selected.append(idx)
        if len(selected) >= max_items:
            break
    return [items[idx].id for idx in selected]


def cluster_feedback(items: list[FeedbackItem], settings: Settings) -> ClusteringResult:
    if not items:
        return ClusteringResult(clusters=[], diagnostics={"item_count": 0})
    if len(items) == 1:
        item = items[0]
        return ClusteringResult(
            clusters=[
                CandidateCluster(
                    cluster_key="cluster-0",
                    item_ids=[item.id],
                    representative_ids=[item.id],
                    coherence=1.0,
                    pattern_type="isolated",
                    unique_feedback_count=1,
                    dominant_product_area=item.product_area,
                )
            ],
            diagnostics={"item_count": 1, "cluster_count": 1, "provider": "single_item"},
        )

    requested_provider = settings.embedding_provider
    if requested_provider == "openai" and not settings.openai_api_key:
        raise RuntimeError("OPENAI_API_KEY is required when EMBEDDING_PROVIDER=openai")
    if requested_provider == "ollama" and not settings.ollama_enabled:
        raise RuntimeError("OLLAMA_ENABLED=true is required when EMBEDDING_PROVIDER=ollama")

    provider = "tfidf"
    fallback_reason: str | None = None
    feature_count: int | None = None
    try:
        if requested_provider == "openai" or (requested_provider == "auto" and settings.openai_api_key):
            dense_matrix = _openai_embeddings(items, settings)
            provider = "openai"
            distance_threshold = settings.embedding_cluster_distance_threshold
        elif requested_provider == "ollama" or (requested_provider == "auto" and settings.ollama_enabled):
            dense_matrix = _ollama_embeddings(items, settings)
            provider = "ollama"
            distance_threshold = settings.embedding_cluster_distance_threshold
        else:
            dense_matrix, feature_count = _tfidf_embeddings(items, settings)
            distance_threshold = settings.cluster_distance_threshold
    except Exception as exc:
        if requested_provider in {"openai", "ollama"}:
            raise
        fallback_reason = f"{type(exc).__name__}: {exc}"
        dense_matrix, feature_count = _tfidf_embeddings(items, settings)
        distance_threshold = settings.cluster_distance_threshold

    model = AgglomerativeClustering(
        n_clusters=None,
        distance_threshold=distance_threshold,
        metric="cosine",
        linkage="average",
    )
    labels = model.fit_predict(dense_matrix)

    raw_groups: dict[int, list[int]] = {}
    for index, label in enumerate(labels):
        raw_groups.setdefault(int(label), []).append(index)
    groups = _split_oversized_groups(
        sorted(raw_groups.values(), key=lambda group: min(group)),
        dense_matrix,
        settings.max_cluster_size,
    )

    clusters: list[CandidateCluster] = []
    coherences: list[float] = []
    for ordinal, indices in enumerate(groups):
        cluster_items = [items[index] for index in indices]
        cluster_matrix = dense_matrix[indices]
        if len(indices) == 1:
            coherence = 1.0
        else:
            similarity = cosine_similarity(cluster_matrix)
            upper = similarity[np.triu_indices(len(indices), k=1)]
            coherence = float(np.mean(upper)) if upper.size else 1.0
        coherences.append(coherence)
        unique_count = len({item.content_hash for item in cluster_items})
        duplicate_ratio = 1 - (unique_count / len(cluster_items))
        area_counts: dict[str, int] = {}
        for item in cluster_items:
            area_counts[item.product_area] = area_counts.get(item.product_area, 0) + 1
        dominant_area = max(area_counts, key=area_counts.get)
        area_purity = area_counts[dominant_area] / len(cluster_items)
        if unique_count == 1:
            pattern = "isolated" if len(cluster_items) == 1 else "uncertain"
        elif duplicate_ratio > 0.6 or area_purity < 0.6 or coherence < settings.low_coherence_threshold:
            pattern = "mixed"
        else:
            pattern = "repeated"
        clusters.append(
            CandidateCluster(
                cluster_key=f"cluster-{ordinal}",
                item_ids=[item.id for item in cluster_items],
                representative_ids=_select_representatives(
                    cluster_items, cluster_matrix, settings.max_representative_items
                ),
                coherence=round(coherence, 4),
                pattern_type=pattern,
                unique_feedback_count=unique_count,
                dominant_product_area=dominant_area,
            )
        )

    diagnostics = {
        "item_count": len(items),
        "cluster_count": len(clusters),
        "average_cluster_size": round(len(items) / len(clusters), 2),
        "average_coherence": round(float(np.mean(coherences)), 4),
        "distance_threshold": distance_threshold,
        "embedding_provider": provider,
        "largest_cluster": max(len(cluster.item_ids) for cluster in clusters),
        "singleton_clusters": sum(1 for cluster in clusters if len(cluster.item_ids) == 1),
        "estimated_pairwise_scale": int(math.pow(len(items), 2)),
    }
    if feature_count is not None:
        diagnostics["vectorizer_features"] = feature_count
    if fallback_reason:
        diagnostics["embedding_fallback_reason"] = fallback_reason
    return ClusteringResult(clusters=clusters, diagnostics=diagnostics)
