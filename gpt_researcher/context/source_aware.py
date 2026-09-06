from dataclasses import dataclass
from collections.abc import Sequence

from langchain_core.documents import Document

from gpt_researcher.evidence.reliability import EvidenceReliabilityEvaluator


@dataclass(frozen=True)
class SourceAwareScore:
    similarity_score: float
    authority_score: float
    final_score: float


class SourceAwareScorer:
    """Combine semantic similarity with a source-level reliability prior."""

    def __init__(self, reliability_weight: float = 0.2):
        if not 0.0 <= reliability_weight <= 1.0:
            raise ValueError("reliability_weight must be between 0 and 1")

        self.reliability_weight = reliability_weight
        self.reliability_evaluator = EvidenceReliabilityEvaluator()

    def score(self, similarity_score: float, url: str) -> SourceAwareScore:
        source_type = self.reliability_evaluator.classify_source_type(url)
        authority_score = self.reliability_evaluator.get_authority_score(
            source_type
        )

        final_score = (
            (1.0 - self.reliability_weight) * similarity_score
            + self.reliability_weight * authority_score
        )

        return SourceAwareScore(
            similarity_score=similarity_score,
            authority_score=authority_score,
            final_score=final_score,
        )

    def rank_documents(
        self,
        documents: Sequence[Document],
    ) -> list[Document]:
        """Rank documents using semantic similarity and source reliability."""

        scored_documents = []

        for doc in documents:
            state = getattr(doc, "state", {})
            similarity_score = state.get("query_similarity_score")

            if similarity_score is None:
                raise ValueError(
                    "Document is missing query_similarity_score"
                )

            url = doc.metadata.get("source", "") or ""

            score = self.score(
                similarity_score=float(similarity_score),
                url=url,
            )

            scored_documents.append((score.final_score, doc))

        scored_documents.sort(
            key=lambda item: item[0],
            reverse=True,
        )

        return [doc for _, doc in scored_documents]