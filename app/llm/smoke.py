"""Local-only smoke evaluation; outputs are ignored runtime artifacts, not test fixtures."""

import argparse
import json
import re
import statistics
from pathlib import Path

from app.core.settings import get_settings
from app.llm.ollama import OllamaProvider
from app.llm.schemas import AnalysisResponse


def _pass(case: dict, text: str, value: AnalysisResponse | None) -> bool:
    if any(phrase.lower() in text.lower() for phrase in case.get("forbidden_contains", [])):
        return False
    check = case["check"]
    if check == "structured":
        return (
            value is not None
            and value.sufficient_evidence is case["sufficient_evidence"]
            and (case["sufficient_evidence"] or not value.evidence)
        )
    if check == "exact":
        return text.strip() == case["expected"]
    if check == "numbered_three":
        return len(re.findall(r"(?m)^\s*[123][.)]", text)) == 3
    if check == "contains":
        return case["expected"].lower() in text.lower()
    if check == "insufficient":
        return any(
            phrase in text.lower()
            for phrase in ("cannot determine", "can't determine", "insufficient", "not enough")
        )
    if check == "arabic":
        return bool(re.search(r"[\u0600-\u06ff]", text))
    raise ValueError(f"Unknown check: {check}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=Path("work/llm-smoke-results.json"))
    args = parser.parse_args()
    cases = json.loads(Path("evaluation/llm_smoke.json").read_text())
    provider = OllamaProvider(get_settings())
    health = provider.health()
    if not health.reachable or not health.model_available:
        raise SystemExit(health.detail)
    results = []
    for case in cases:
        try:
            value = None
            if case["check"] == "structured":
                response = provider.generate_structured(case["prompt"], AnalysisResponse)
                value = response.value
                generation = response.generation
            else:
                generation = provider.generate(case["prompt"])
            passed = _pass(case, generation.text, value)
            results.append(
                {
                    "id": case["id"],
                    "category": case["category"],
                    "passed": passed,
                    "structured_valid": value is not None,
                    "duration_seconds": generation.duration_seconds,
                    "load_seconds": generation.load_seconds,
                    "output_tokens": generation.output_tokens,
                    "response": generation.text,
                }
            )
            print(
                f"{case['id']}: {'PASS' if passed else 'FAIL'} {generation.duration_seconds:.2f}s",
                flush=True,
            )
        except Exception as exc:
            results.append(
                {
                    "id": case["id"],
                    "category": case["category"],
                    "passed": False,
                    "structured_valid": False,
                    "error": f"{type(exc).__name__}: {exc}",
                }
            )
            print(f"{case['id']}: ERROR {type(exc).__name__}", flush=True)
    durations = [item["duration_seconds"] for item in results if "duration_seconds" in item]
    summary = {
        "model": provider.model,
        "ollama_version": health.version,
        "prompts": len(cases),
        "successful": sum(item["passed"] for item in results),
        "structured_valid": sum(item["structured_valid"] for item in results),
        "structured_total": sum(case["check"] == "structured" for case in cases),
        "mean_seconds": statistics.mean(durations) if durations else None,
        "median_seconds": statistics.median(durations) if durations else None,
        "results": results,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps({key: value for key, value in summary.items() if key != "results"}, indent=2))


if __name__ == "__main__":
    main()
