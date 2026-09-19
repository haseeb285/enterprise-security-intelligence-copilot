# Phase 10 generated evaluation summary

Suite version: `1.0.0`

> SYNTHETIC DEMONSTRATION DATA. This is a small local development evaluation, not production SOC performance.

## Offline layers

| Metric | Result |
| --- | ---: |
| Retrieval Recall@1 / @3 / @5 | 1.000 / 1.000 / 1.000 |
| Retrieval MRR | 1.000 |
| Answerable gate acceptance | 34/39 (87.18%) |
| Unanswerable gate rejection | 8/8 (100.00%) |
| Citation/source correctness | 39/39 |
| Retrieval mean / median | 22.898 / 20.960 ms |
| ML scenario detection | 5/6 (83.33%) |
| ML false-positive rate | 40/583 (6.86%) |
| ML flagged precision | 11.11% |
| ML Top-5 / Top-10 capture | 2/6 / 4/6 |
| ML cold / warm median inference | 52.808 / 14.169 ms |
| Deterministic safety contracts | 13/13 |

## Live local-model layers

| Metric | Result |
| --- | ---: |
| Structured-generation checks | 12/12 |
| Schema validity | 4/4 |
| Malformed structured outputs | 0 |
| Integrated expected tool sets | 20/20 |
| Integrated procedural completion | 20/20 |
| Source/provenance fidelity | 20/20 |
| Policy citation fidelity | 20/20 |
| Exact anomaly score / flag fidelity | 20/20 / 20/20 |
| Unsupported identifier / score references | 0 / 0 |
| Deterministic fact checks | 6/6 |
| Integrated mean / median latency | 26.620 / 29.563 s |
| Manual direct-answer review | 19/20 |

The impossible-travel regression passed by preserving Germany and Japan events fifteen minutes apart together with score `-0.21107408822812324` and `flagged=false`.

No combined project accuracy score is calculated.
