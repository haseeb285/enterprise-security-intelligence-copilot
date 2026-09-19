# Layered development evaluation

Phase 10 evaluates the local synthetic system in separate layers. It does not calculate a combined project accuracy score. The cases use only deterministic synthetic events and fictional policies, one local `qwen3.5:4b` model, and one Apple M3 development machine. These results do not estimate production SOC performance.

The versioned manifest is `evaluation/phase10_suite.json`. It references the existing Phase 3 retrieval, Phase 4 structured-generation, Phase 6 routing, and Phase 8 integrated datasets instead of copying them. Phase 10 adds six predeclared fact expectations and thirteen deterministic safety/failure contracts.

## Reproduce

With PostgreSQL, Qdrant, the ingested fictional policy collection, and the persisted Phase 7 model available, run the layers that do not require Ollama:

```bash
.venv/bin/python -m app.evaluation.run --offline
```

With native Ollama and configured `qwen3.5:4b` also healthy, run the local-model layers once:

```bash
.venv/bin/python -m app.evaluation.run --live
```

For a fresh complete run, use `--all`. Detailed responses and timings are written to ignored `work/phase10/latest.json`. The command deterministically emits the sanitized tracked summaries:

- `evaluation/results/phase10-summary.json`
- `evaluation/results/phase10-summary.md`

The exact measured Phase 10 table is in [the generated summary](../evaluation/results/phase10-summary.md). A manual rubric is bound to the reviewed integrated artifact by SHA-256; a later live run makes that review stale until it is repeated.

## Dataset composition

- **Retrieval:** 47 queries: 39 answerable and 8 unanswerable, including direct, paraphrased, and Arabic questions.
- **Structured generation:** 12 live prompts: instruction following, terminology, evidence synthesis, insufficiency, Arabic, and 4 schema-constrained cases.
- **Agent routing labels:** 18 existing cases with expected tool sets defined before execution.
- **Integrated live:** 20 cases covering policy, events, incidents, ML, all evidence combinations, unknown/insufficient input, dependency failure, prompt injection, invalid time, ambiguity, and the known ML limitation.
- **Safety/failure:** 13 deterministic contracts covering policy and event prompt injection, unknown identifiers, irrelevant policy, missing model, PostgreSQL/Qdrant/Ollama failures, invalid authentication, insufficient evidence, and a write request.
- **ML:** the existing 589-observation Phase 7 holdout and six separately stored scenarios. Phase 10 does not retrain or change the selected Isolation Forest.

## Metrics and methodology

### Retrieval

Raw top-five ranking is measured separately from the fixed `0.805` relevance gate. Metrics are Recall@1, Recall@3, Recall@5, MRR, answerable acceptance, unanswerable rejection, citation/source correctness, and query latency. The suite is executed twice and non-latency records must match. The fixed gate still rejects five answerable questions despite perfect top-five ranking; no threshold was tuned on these cases.

### Structured generation

The local model is measured with deterministic checks for schema validity, declared evidence sufficiency, empty evidence when insufficient, instruction following, and prohibited phrases. No paid or cloud model judges output, and no factual-correctness score is inferred from subjective judging.

### Agent and integrated investigations

Expected tool sets are versioned inputs. Metrics cover tool selection, unnecessary calls, procedural completion, structured-call validity, five-step/three-tool limits, source/provenance equality, event and incident identifiers, policy citations, exact anomaly score and flag, evidence-category separation, sufficiency behavior, and unsupported identifier or numeric score references.

Six facts were declared before the live run: the password minimum, backup retention, exact event `EV000001`, U105 countries, U105 score, and U105 flag. The application-owned response fields passed all six checks.

The explicit manual rubric reviews unsupported factual claims, contradiction, uncertainty, ML/observed-fact distinction, invented policy requirements, and whether the bounded request is answered directly. It does not inspect hidden reasoning. Nineteen of twenty responses answered directly; the password-policy response retrieved the correct sixteen-character evidence but its generated prose stayed generic.

### ML and latency

Phase 10 reads the existing selected-baseline Phase 7 result rather than training again. It reports scenario detection, false-positive rate, flagged precision, Top-5/Top-10 scenario capture, ranking, and the known missed scenario. A fresh service instance measures one cold and five warm U105 inferences. Retrieval, structured generation, integrated investigation, and ML latency remain separate.

### Safety and failures

The safety evaluator runs the real bounded LangGraph with deterministic providers and tool outcomes, plus the real authentication dependency. It confirms safe prompt masking, no leaked dependency details, partial evidence when one source fails, safe insufficiency for unknown identifiers, 401 for absent credentials, and that attempted remediation can invoke at most existing read-only evidence tools. It performs no destructive action.

## Measured weaknesses

- The retrieval ranking found every target section at rank 1, but the fixed gate accepted only 34/39 answerable queries.
- The selected Isolation Forest detects 5/6 scenarios but has 40 false positives among 583 normal holdout observations and only 11.11% flagged precision.
- Impossible travel ranks 325th and is not flagged. Success means representing the Germany/Japan evidence and negative model flag faithfully.
- Local integrated inference remains slow: 26.620 seconds mean and 29.563 seconds median in this run.
- One policy response did not directly state the retrieved password-length answer.
- The deterministic and manual checks cover a small development suite; they do not prove general factual correctness, broad prompt-injection resistance, production reliability, or security effectiveness.
