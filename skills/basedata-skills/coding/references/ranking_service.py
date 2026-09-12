"""Per-project feed ranking: one similarity to the project centroid, boosted and banded.

The centroid of a project's saved papers is the ranker. Serving is one vector
inner product per candidate; Python applies the bounded multiplicative boosts
and assigns a confidence band from the un-boosted score, so a boost reorders
within a band and never moves a paper across the band line. The ranker learns
only from what the team saves.

Module map, train then serve::

    train_ranker            build the centroid and save it; the one write to ProjectRanker
    │  profile_vector         the centroid from the saved papers
    └─ save_ranker            the write itself

    rank_feed               the served order: candidates, factors, band, page
    │  ranker_relevance       the inner product per candidate
    └─ decorate_factors       the single place the boost factors are computed
         recency_factor · keyphrase_factor

    band                    score to accept / borderline
"""

from __future__ import annotations

import datetime
import math

import numpy as np
from sqlalchemy.orm import Session

from mypkg.models import Article, Project, ProjectRanker


def profile_vector(session: Session, project: Project) -> np.ndarray:
    """The mean embedding of the project's saved papers. Raises when the library is empty."""
    vectors = [a.embedding for a in project.library_articles(session) if a.embedding is not None]
    if not vectors:
        raise ValueError(f"project {project.id} has no embedded library papers to train from")
    centroid = np.mean(np.asarray(vectors), axis=0)
    return centroid / np.linalg.norm(centroid)


def save_ranker(session: Session, project: Project, weight: np.ndarray) -> ProjectRanker:
    """Store the served weight for the project, replacing any previous one."""
    ranker = session.get(ProjectRanker, project.id) or ProjectRanker(project_id=project.id)
    ranker.weight = weight.tolist()
    ranker.trained_at = datetime.datetime.now(datetime.timezone.utc)
    session.add(ranker)
    session.flush()
    return ranker


def train_ranker(session: Session, project: Project) -> ProjectRanker:
    """Rebuild the project's centroid and save it."""
    return save_ranker(session, project, profile_vector(session, project))


def recency_factor(age_seconds: float, half_life_days: float) -> float:
    """A boost in (1, 2] that halves every ``half_life_days``."""
    if half_life_days <= 0:
        raise ValueError(f"half_life_days must be positive, got {half_life_days}")
    return 1.0 + math.exp(-age_seconds / (half_life_days * 86400.0))


def keyphrase_factor(n_matches: int) -> float:
    """A boost in [1, 1.5] that saturates at three matching keyphrases."""
    return 1.0 + 0.5 * min(n_matches, 3) / 3


def decorate_factors(
    articles: list[Article],
    *,
    relevance: dict[int, float],
    match_counts: dict[int, int],
    half_life_days: float,
    now: float,
) -> dict[int, dict[str, float]]:
    """Compute each article's ranking factors.

    A factor whose ingredient is missing is absent from the article's dict,
    never ``1.0``, because absence is the client's signal to grey that control.
    """
    out: dict[int, dict[str, float]] = {}
    for article in articles:
        factors: dict[str, float] = {}
        if article.id in relevance:
            factors["relevance"] = round(relevance[article.id], 4)
        if article.published_at is not None:
            age = now - article.published_at.timestamp()
            factors["recency"] = round(recency_factor(age, half_life_days), 4)
        if article.id in match_counts:
            factors["keyphrase"] = round(keyphrase_factor(match_counts[article.id]), 4)
        out[article.id] = factors
    return out


def band(probability: float) -> str:
    """Accept above 0.5, borderline from 0.3, else reject."""
    if probability >= 0.5:
        return "accept"
    if probability >= 0.3:
        return "borderline"
    return "reject"
