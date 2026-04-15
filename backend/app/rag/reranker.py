"""Reranker implementations for improving RAG retrieval quality.

This module provides reranking functionality to improve the relevance of
search results. It supports both API-based rerankers (Cohere) and local
models (Cross Encoder).
"""

import logging
import time
from abc import ABC, abstractmethod

from app.core.config import settings
from app.rag.config import RAGSettings
from app.rag.models import SearchResult

logger = logging.getLogger(__name__)


class BaseReranker(ABC):
    """Abstract base class for reranking implementations.

    Defines the interface that all reranker providers must implement.
    Rerankers take an initial set of search results and reorder them
    based on semantic relevance to the query.
    """

    @abstractmethod
    async def rerank(
        self,
        query: str,
        results: list[SearchResult],
        top_k: int,
    ) -> list[SearchResult]:
        """Rerank search results based on query relevance.

        Args:
            query: The original search query.
            results: Initial search results from vector search.
            top_k: Number of top results to return after reranking.

        Returns:
            Reranked list of SearchResult objects, sorted by relevance.
        """
        pass

    @abstractmethod
    def warmup(self) -> None:
        """Ensure the reranker model is loaded and ready for inference.

        For API-based rerankers, this may validate credentials.
        For local models, this triggers model download and loading.
        """
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        """Return the name of the reranker for logging purposes."""
        pass


from sentence_transformers import CrossEncoder


class CrossEncoderReranker(BaseReranker):
    """Cross Encoder reranker using local Sentence Transformers model.

    Uses a cross-encoder model to score query-document pairs for relevance.
    Runs entirely locally - no API calls required.

    Default model: cross-encoder/ms-marco-MiniLM-L6-v2 (lightweight, fast)
    """

    # Default cross-encoder model for reranking
    DEFAULT_MODEL = settings.CROSS_ENCODER_MODEL

    def __init__(self, model: str | None = None, cache_dir: str | None = None):
        """Initialize the Cross Encoder reranker.

        Args:
            model: Cross-encoder model name from Sentence Transformers.
                   Defaults to cross-encoder/ms-marco-MiniLM-L6-v2 if not specified.
            cache_dir: Directory to cache the model. Defaults to app models cache.
        """
        self.model_name = model or self.DEFAULT_MODEL
        self.cache_dir = cache_dir
        self._model = None

    @property
    def model(self) -> CrossEncoder:
        """Lazy load the cross-encoder model."""
        if self._model is None:
            from app.core.config import settings as app_settings

            cache_path = self.cache_dir or str(app_settings.MODELS_CACHE_DIR)
            # Ensure cache directory exists
            app_settings.MODELS_CACHE_DIR.mkdir(exist_ok=True, parents=True)

            logger.info(f"[RERANKER] Loading Cross Encoder model: {self.model_name}")
            self._model = CrossEncoder(
                self.model_name,
                cache_folder=cache_path,
                token=settings.HF_TOKEN,
            )
            logger.info("[RERANKER] Cross Encoder model loaded successfully")
        return self._model

    @property
    def name(self) -> str:
        return f"CrossEncoderReranker({self.model_name})"

    async def rerank(
        self,
        query: str,
        results: list[SearchResult],
        top_k: int,
    ) -> list[SearchResult]:
        """Rerank results using local Cross Encoder model.

        Args:
            query: The search query.
            results: Initial search results.
            top_k: Number of results to return.

        Returns:
            Reranked results sorted by relevance score.
        """
        if not results:
            return []

        print(
            f"[RERANKER] Cross Encoder reranking {len(results)} documents, "
            f"query: '{query[:50]}...', top_k: {top_k}"
        )

        start_time = time.time()

        try:
            # Prepare query-document pairs for scoring
            # CrossEncoder expects list of [query, document] pairs
            pairs = [[query, result.content] for result in results]

            # Get relevance scores (higher = more relevant)
            scores = self.model.predict(pairs)

            elapsed = time.time() - start_time
            logger.info(f"[RERANKER] Cross Encoder reranking completed in {elapsed:.3f}s")

            # Create new results with cross-encoder scores
            scored_results = []
            for i, (result, score) in enumerate(zip(results, scores)):
                logger.debug(
                    f"[RERANKER] CrossEncoder score for doc {i}: {score:.4f} "
                    f"(original: {result.score:.4f}) - '{result.content[:30]}...'"
                )
                scored_results.append(
                    SearchResult(
                        content=result.content,
                        score=float(score),  # Use cross-encoder score
                        metadata=result.metadata,
                        parent_doc_id=result.parent_doc_id,
                    )
                )

            # Sort by cross-encoder score (descending)
            scored_results.sort(key=lambda x: x.score, reverse=True)

            # Log top results
            for i, r in enumerate(scored_results[:3]):
                logger.debug(
                    f"[RERANKER] Rank #{i + 1}: score={r.score:.4f}, content='{r.content[:50]}...'"
                )

            return scored_results[:top_k]

        except Exception as e:
            logger.error(f"[RERANKER] Cross Encoder reranking failed: {e!s}")
            return results[:top_k]

    def warmup(self) -> None:
        """Trigger model download and loading."""
        logger.info(f"[RERANKER] Cross Encoder warmup: loading model {self.model_name}")
        _ = self.model
        logger.info(f"[RERANKER] Cross Encoder ready: {self.model_name}")


class RerankService:
    """Service for managing reranking operations.

    Orchestrates reranking using a configured reranker provider.
    Supports both Cohere API and local Cross Encoder models.
    """

    def __init__(self, settings: RAGSettings):
        """Initialize the rerank service.

        Args:
            settings: RAG configuration settings containing reranker config.
        """
        self.settings = settings
        config = settings.reranker_config  # type: ignore[attr-defined]
        self._reranker: BaseReranker | None = None
        if config.model == "cross_encoder":
            self._reranker = CrossEncoderReranker()
            logger.info("[RERANKER] Using Cross Encoder reranker")

        if self._reranker is None:
            logger.warning(
                f"[RERANKER] No reranker configured (model: {config.model}). "
                "Reranking will be skipped."
            )

    @property
    def reranker(self) -> BaseReranker | None:
        """Return the configured reranker, if any."""
        return self._reranker

    @property
    def is_enabled(self) -> bool:
        """Check if reranking is enabled."""
        return self._reranker is not None

    async def rerank(
        self,
        query: str,
        results: list[SearchResult],
        top_k: int,
    ) -> list[SearchResult]:
        """Rerank search results if a reranker is configured.

        Args:
            query: The search query.
            results: Initial search results to rerank.
            top_k: Number of results to return.

        Returns:
            Reranked results if reranker is configured, otherwise original results.
        """
        if not self._reranker:
            logger.debug("[RERANKER] No reranker configured, returning original results")
            return results[:top_k]

        print(
            f"[RERANKER] Starting reranking with {self._reranker.name}, "
            f"query: '{query[:50]}...', results: {len(results)}, top_k: {top_k}"
        )

        # Log pre-reranking scores
        for i, r in enumerate(results[:5]):
            logger.debug(
                f"[RERANKER] Pre-rerank #{i + 1}: score={r.score:.4f}, "
                f"content='{r.content[:50]}...'"
            )

        reranked = await self._reranker.rerank(query, results, top_k)

        # Log post-reranking scores
        for i, r in enumerate(reranked[:5]):
            logger.debug(
                f"[RERANKER] Post-rerank #{i + 1}: score={r.score:.4f}, "
                f"content='{r.content[:50]}...'"
            )

        return reranked

    def warmup(self) -> None:
        """Initialize the reranker model if configured."""
        if self._reranker:
            logger.info(f"[RERANKER] Warming up {self._reranker.name}")
            self._reranker.warmup()
            logger.info(f"[RERANKER] {self._reranker.name} warmup complete")
