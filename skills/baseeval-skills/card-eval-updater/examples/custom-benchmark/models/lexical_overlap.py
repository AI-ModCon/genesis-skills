"""A custom lm-evaluation-harness model: a lexical-overlap baseline.

Registered as `lexical-overlap`, this is a real (if deliberately simple) model.
It scores each candidate answer by how much vocabulary it shares with the
question, after removing stopwords, and prefers the choice with the highest
overlap. Ties break toward the shorter answer.

Why a baseline rather than a downloaded LLM: it is deterministic, needs no
weights, no GPU, and no network, so the example is exactly reproducible and its
accuracy is a genuine measurement rather than a placeholder. It is also a
meaningful control — any real model evaluated on this benchmark should beat it,
and a model that does not has learned nothing beyond surface word matching.

Usage:
    lm_eval --model lexical-overlap --include_path tasks --tasks beamline_qa
"""

from __future__ import annotations

import math
import re

from lm_eval.api.instance import Instance
from lm_eval.api.model import LM
from lm_eval.api.registry import register_model

# Function words carry no topical signal; leaving them in would let long answers
# win on padding alone.
STOPWORDS = frozenset(
    """a an the of to in on at by for from with without and or but is are was were
    be been being it its this that these those which what who whom whose when where
    why how does do did done can could should would may might must will shall as
    into onto than then there here all any each every no not only own same so such
    too very s t just about above below over under again further once""".split()
)

TOKEN_RE = re.compile(r"[a-z0-9]+")


def _content_words(text: str) -> set[str]:
    return {w for w in TOKEN_RE.findall(text.lower()) if w not in STOPWORDS and len(w) > 2}


@register_model("lexical-overlap")
class LexicalOverlapLM(LM):
    """Scores a continuation by its content-word overlap with the context."""

    def __init__(self, length_penalty: float = 0.05, **kwargs) -> None:
        super().__init__()
        self.length_penalty = float(length_penalty)

    @classmethod
    def create_from_arg_string(cls, arg_string, additional_config=None):
        args = {}
        for pair in (arg_string or "").split(","):
            if "=" in pair:
                key, value = pair.split("=", 1)
                args[key.strip()] = value.strip()
        return cls(**args)

    def _score(self, context: str, continuation: str) -> float:
        question = _content_words(context)
        answer = _content_words(continuation)
        if not answer:
            return -math.inf
        overlap = len(question & answer)
        # Normalise by answer length so a long answer cannot win on breadth
        # alone, then penalise length slightly to break ties toward brevity.
        return overlap / len(answer) - self.length_penalty * len(answer)

    def loglikelihood(self, requests: list[Instance]) -> list[tuple[float, bool]]:
        # lm-eval ranks multiple-choice options by these scores. They are
        # comparable within a question, which is all the accuracy metric needs;
        # they are not calibrated log-probabilities and must not be read as such.
        return [(self._score(*req.args), False) for req in requests]

    def loglikelihood_rolling(self, requests: list[Instance]) -> list[float]:
        raise NotImplementedError(
            "lexical-overlap is a ranking baseline and cannot score free text; "
            "it supports multiple_choice tasks only."
        )

    def generate_until(self, requests: list[Instance]) -> list[str]:
        raise NotImplementedError(
            "lexical-overlap cannot generate text; it supports multiple_choice tasks only."
        )
