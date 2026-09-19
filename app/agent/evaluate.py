"""Opt-in local development evaluation of the real graph and services."""

import json
from pathlib import Path
from statistics import mean, median
from time import perf_counter

from qdrant_client import QdrantClient
from sqlalchemy.orm import Session

from app.agent.graph import InvestigationAgent
from app.agent.tools import AgentTools
from app.api.services import ApiService, build_rag_service
from app.core.settings import Settings
from app.db.session import create_db_engine
from app.llm.ollama import OllamaProvider
from app.llm.provider import LLMMalformedOutput

ROOT = Path(__file__).resolve().parents[2]


class TrackingProvider:
    def __init__(self, wrapped):
        self.wrapped = wrapped
        self.calls = 0
        self.valid = 0
        self.malformed = 0

    def generate_structured(self, prompt, schema, system=None):
        self.calls += 1
        try:
            result = self.wrapped.generate_structured(prompt, schema, system=system)
        except LLMMalformedOutput:
            self.malformed += 1
            raise
        self.valid += 1
        return result


def main() -> None:
    cases = json.loads((ROOT / "evaluation/agent_cases.json").read_text())["cases"]
    settings = Settings()
    engine = create_db_engine(settings)
    qdrant = QdrantClient(url=str(settings.qdrant_url), timeout=15)
    llm = OllamaProvider(settings)
    records = []
    out = ROOT / "work/phase6-agent-evaluation.json"
    try:
        with Session(engine) as session:
            service = ApiService(session)
            provider = TrackingProvider(llm)
            agent = InvestigationAgent(
                provider, AgentTools(service, lambda: build_rag_service(settings, qdrant))
            )
            for case in cases:
                before = (provider.calls, provider.valid, provider.malformed)
                start = perf_counter()
                result = agent.run(case["request"], "admin")
                seconds = round(perf_counter() - start, 3)
                expected = set(case["expected_tools"])
                actual = {item.value for item in result.selected_tools}
                complete = (
                    result.outcome == "complete"
                    and bool(result.observed_evidence)
                    and actual == expected
                    if case["expect_evidence"]
                    else result.outcome == "insufficient_evidence"
                    and not result.observed_evidence
                    and actual == expected
                )
                record = {
                    "id": case["id"],
                    "category": case["category"],
                    "request": case["request"],
                    "expected_tools": case["expected_tools"],
                    "selected_tools": [item.value for item in result.selected_tools],
                    "tool_results": result.tool_results,
                    "tool_calls": result.tool_calls,
                    "selection_correct": actual == expected,
                    "unnecessary_tool_calls": sum(
                        name not in expected
                        and result.tool_results.get(name) in {"success", "empty", "failure"}
                        for name in actual
                    ),
                    "task_complete": complete,
                    "outcome": result.outcome,
                    "evidence_count": len(result.observed_evidence),
                    "sources": result.sources,
                    "errors": result.errors,
                    "structured_calls": provider.calls - before[0],
                    "structured_valid": provider.valid - before[1],
                    "structured_malformed": provider.malformed - before[2],
                    "latency_seconds": seconds,
                    "response": result.model_dump(mode="json"),
                }
                records.append(record)
                out.write_text(json.dumps({"incomplete": True, "cases": records}, indent=2))
                print(
                    json.dumps(
                        {
                            key: record[key]
                            for key in (
                                "id",
                                "selected_tools",
                                "selection_correct",
                                "task_complete",
                                "outcome",
                                "latency_seconds",
                            )
                        }
                    ),
                    flush=True,
                )
    finally:
        qdrant.close()
        llm.client.close()
        engine.dispose()
    latencies = [r["latency_seconds"] for r in records]
    summary = {
        "request_count": len(records),
        "selection_correct": sum(r["selection_correct"] for r in records),
        "task_complete": sum(r["task_complete"] for r in records),
        "unnecessary_tool_calls": sum(r["unnecessary_tool_calls"] for r in records),
        "structured_calls": sum(r["structured_calls"] for r in records),
        "structured_valid": sum(r["structured_valid"] for r in records),
        "structured_malformed": sum(r["structured_malformed"] for r in records),
        "failures": sum(not r["task_complete"] for r in records),
        "mean_latency_seconds": round(mean(latencies), 3),
        "median_latency_seconds": round(median(latencies), 3),
    }
    out.write_text(json.dumps({"summary": summary, "cases": records}, indent=2))
    print(json.dumps(summary, indent=2), flush=True)
    print(f"Detailed synthetic evaluation saved to ignored {out.relative_to(ROOT)}", flush=True)


if __name__ == "__main__":
    main()
