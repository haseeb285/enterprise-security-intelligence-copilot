"""Evaluate raw retrieval rank and calibrated threshold against labeled policy sections."""

import argparse
import json
import statistics
import time
from pathlib import Path

from app.core.settings import get_settings
from app.rag.embeddings import get_embedder
from app.rag.service import RagService
from app.rag.store import VectorStore


def evaluate(service: RagService, cases: list[dict], threshold: float) -> dict:
    hits = {1: 0, 3: 0, 5: 0}
    reciprocal = []
    reject = 0
    accepted = 0
    arabic = [0, 0]
    latencies = []
    records = []
    citation_correct = 0
    for index, case in enumerate(cases):
        start = time.perf_counter()
        result = service.retrieve(case["query"], top_k=5)
        latencies.append((time.perf_counter() - start) * 1000)
        raw = result.evidence  # service threshold=0 during evaluation
        eligible = [item for item in raw if item.score >= threshold]
        if case["document"] is None:
            reject += not bool(eligible)
            records.append(
                {
                    "id": case.get("id", f"retrieval-{index}"),
                    "answerable": False,
                    "accepted": bool(eligible),
                    "target_rank": None,
                    "citation_correct": not bool(eligible),
                }
            )
            continue
        accepted += bool(eligible)
        ranks = [
            rank
            for rank, item in enumerate(raw, 1)
            if item.citation.document == case["document"]
            and item.citation.section == case["section"]
        ]
        rank = min(ranks) if ranks else None
        correct = bool(
            rank
            and raw[rank - 1].citation.source
            and raw[rank - 1].citation.document == case["document"]
            and raw[rank - 1].citation.section == case["section"]
        )
        citation_correct += correct
        records.append(
            {
                "id": case.get("id", f"retrieval-{index}"),
                "answerable": True,
                "accepted": bool(eligible),
                "target_rank": rank,
                "citation_correct": correct,
            }
        )
        reciprocal.append(1 / rank if rank else 0)
        for k in hits:
            hits[k] += bool(rank and rank <= k)
        if case.get("language") == "ar":
            arabic[1] += 1
            arabic[0] += bool(rank == 1)
    positives = len(reciprocal)
    negatives = len(cases) - positives
    return {
        "queries": len(cases),
        "positives": positives,
        "negatives": negatives,
        "threshold": threshold,
        "recall_at_1": hits[1] / positives,
        "recall_at_3": hits[3] / positives,
        "recall_at_5": hits[5] / positives,
        "mrr": statistics.mean(reciprocal),
        "negative_rejected": reject,
        "negative_total": negatives,
        "unanswerable_rejection_rate": reject / negatives if negatives else 0.0,
        "positive_accepted": accepted,
        "answerable_acceptance_rate": accepted / positives if positives else 0.0,
        "citation_source_correct": citation_correct,
        "citation_source_total": positives,
        "arabic_recall_at_1": arabic[0] / arabic[1] if arabic[1] else None,
        "arabic_positive_total": arabic[1],
        "latency_mean_ms": statistics.mean(latencies),
        "latency_median_ms": statistics.median(latencies),
        "records": records,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--threshold", type=float, default=None)
    args = parser.parse_args()
    settings = get_settings()
    embedder = get_embedder(settings.embedding_model)
    store = VectorStore(str(settings.qdrant_url), settings.rag_collection, embedder.dimension)
    store.ready()
    service = RagService(
        store,
        embedder,
        settings.rag_chunk_target_chars,
        settings.rag_chunk_overlap_chars,
        threshold=0,
    )
    cases = json.loads(Path("evaluation/rag_cases.json").read_text())
    print(
        json.dumps(
            evaluate(
                service,
                cases,
                args.threshold if args.threshold is not None else settings.rag_min_score,
            ),
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
