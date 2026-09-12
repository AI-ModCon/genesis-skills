"""Vector stores: one embedder over many named collections, searched by cosine similarity.

A store owns its embedder and its collections and is the one write path for
documents. Every reader goes through ``search``. Rank fusion across stores is
a module function because it is a pure algorithm two callers share. The parser
for each document type is imported at its single use site, so a server that
serves searches without ingesting pays nothing for the parsers at startup.

Class map: ``<branch>─<rel> Class``, ``<rel>`` is ◇ holds · ◆ owns · ▷ inherits::

    VectorStore «abstract»          add / search over named collections
    ├─◇ Embedder «abstract» 1        text to vectors; ``create`` picks the implementation
    │   ├─▷ LocalEmbedder            sentence-transformers, offline
    │   └─▷ ApiEmbedder              an OpenAI-compatible endpoint
    └─▷ ChromaVectorStore            local Chroma, one collection per name

    free fn: fuse_by_rank            reciprocal rank fusion, used by store and caller
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import numpy as np


@dataclass(frozen=True)
class Hit:
    doc_id: str
    score: float
    text: str


class Embedder(ABC):
    """Map text to vectors of one fixed dimension."""

    dimension: int

    @classmethod
    def create(cls, name: str, *, base_url: str | None = None, api_key: str | None = None) -> "Embedder":
        """Build the embedder for a model name: an API client when a base URL is given, else local."""
        if base_url:
            return ApiEmbedder(name, base_url=base_url, api_key=api_key)
        return LocalEmbedder(name)

    @abstractmethod
    def embed(self, texts: list[str]) -> "np.ndarray":
        """Embed each text; the result has one row per input."""


class LocalEmbedder(Embedder):
    def __init__(self, name: str):
        try:
            # Imported here: sentence-transformers loads torch, which a search-only server never needs.
            from sentence_transformers import SentenceTransformer
        except ImportError as err:
            raise ImportError("LocalEmbedder needs the 'local' extra: pip install 'mypkg[local]'") from err
        self._model = SentenceTransformer(name)
        self.dimension = self._model.get_sentence_embedding_dimension()

    def embed(self, texts: list[str]) -> "np.ndarray":
        return self._model.encode(texts, normalize_embeddings=True)


class ApiEmbedder(Embedder):
    def __init__(self, name: str, *, base_url: str, api_key: str | None):
        if not api_key:
            raise ValueError("ApiEmbedder needs an API key; set EMBEDDING_API_KEY")
        self._name = name
        self._base_url = base_url
        self._api_key = api_key
        self.dimension = 1536

    def embed(self, texts: list[str]) -> "np.ndarray":
        ...


class VectorStore(ABC):
    """Named collections of documents under one embedder."""

    def __init__(self, embedder: Embedder):
        self.embedder = embedder

    @abstractmethod
    def add_documents(self, collection: str, docs: list[tuple[str, str]]) -> int:
        """Embed and store ``(doc_id, text)`` pairs; return the count stored."""

    @abstractmethod
    def search(self, collection: str, query: str, k: int) -> list[Hit]:
        """The ``k`` nearest documents to the query, best first."""


class ChromaVectorStore(VectorStore):
    def __init__(self, embedder: Embedder, index_dir: Path):
        super().__init__(embedder)
        if not index_dir.is_dir():
            raise FileNotFoundError(f"index directory {index_dir} does not exist")
        self.index_dir = index_dir

    def add_documents(self, collection: str, docs: list[tuple[str, str]]) -> int:
        if not docs:
            raise ValueError(f"add_documents to {collection!r} was given no documents")
        ...

    def search(self, collection: str, query: str, k: int) -> list[Hit]:
        ...


def fuse_by_rank(rankings: list[list[Hit]], *, constant: int = 60) -> list[Hit]:
    """Reciprocal rank fusion. Scores from different embedding spaces combine by rank alone."""
    fused: dict[str, float] = {}
    text: dict[str, str] = {}
    for ranking in rankings:
        for rank, hit in enumerate(ranking, 1):
            fused[hit.doc_id] = fused.get(hit.doc_id, 0.0) + 1.0 / (constant + rank)
            text[hit.doc_id] = hit.text
    ordered = sorted(fused.items(), key=lambda item: item[1], reverse=True)
    return [Hit(doc_id, score, text[doc_id]) for doc_id, score in ordered]
