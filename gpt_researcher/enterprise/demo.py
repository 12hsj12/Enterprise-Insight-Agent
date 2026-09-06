"""Run a synthetic, credential-free demo through the real evidence/workflow layers."""

import argparse
import asyncio
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

from gpt_researcher.prompts import PromptFamily
from gpt_researcher.skills.context_manager import ContextManager
from .trace import RunTrace
from .workflow import IntelligenceRequest, IntelligenceWorkflow


class FixtureResearcher:
    """Researcher fixture using the real compression/evidence pipeline."""

    def __init__(self, **kwargs):
        self.query = kwargs["query"]
        self.verbose = False
        self.cfg = SimpleNamespace(source_reliability_weight=0.0, similarity_threshold=0.42)
        self.memory = SimpleNamespace(get_embeddings=lambda: None)
        self.prompt_family = PromptFamily
        self.kwargs = {}
        self.evidences, self.assessments = [], []

    def add_evidences(self, values):
        self.evidences.extend(values)

    def add_evidence_assessments(self, values):
        self.assessments.extend(values)

    def get_evidences(self):
        return self.evidences

    def get_evidence_assessments(self):
        return self.assessments

    def add_costs(self, value):
        raise AssertionError("Synthetic fast-path demo must not incur provider costs")

    def get_costs(self):
        return 0.0

    async def conduct_research(self):
        await ContextManager(self).get_similar_content_by_query(self.query, [
            {"title": "Synthetic company brief", "url": "https://example.com/company",
             "raw_content": "SYNTHETIC: FixtureCo offers a workflow product for small businesses."},
            {"title": "Synthetic market brief", "url": "https://example.org/market",
             "raw_content": "SYNTHETIC: Alternatives include spreadsheets and specialist workflow products. Market share is unknown."},
        ])

    async def write_report(self, **kwargs):
        return """# FixtureCo competitive intelligence — synthetic demonstration

## Company overview and products
FixtureCo offers a workflow product for small businesses ([synthetic brief](https://example.com/company)).

## Competitive landscape
Alternatives include spreadsheets and specialist products ([synthetic brief](https://example.org/market)).

## Recent developments
The fixture provides no dated development evidence.

## Risks and uncertainties
Market share is unknown. These example-domain sources and company facts are synthetic;
this demo demonstrates software behavior and does not measure research quality.
"""


async def demo():
    run_id = str(uuid4())
    return await IntelligenceWorkflow(FixtureResearcher).run(
        IntelligenceRequest(target="FixtureCo"), run_id=run_id, trace=RunTrace(run_id))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("outputs/enterprise-demo.json"))
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError("Choose a new output filename")
    result = asyncio.run(demo())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(result.model_dump_json(indent=2) + "\n", encoding="utf-8")
    print(f"Synthetic demo saved to {args.output}; evidence={len(result.evidences)}, provider_calls=0")
