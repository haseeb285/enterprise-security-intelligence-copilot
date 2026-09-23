# Local Demo and Validation Guide

This guide exercises the real Streamlit → FastAPI path against the seeded synthetic dataset. Generated wording can vary, while typed evidence, tool choices, citations, scores, and flags remain application-owned.

## Prepare the local environment

1. Complete the [Docker Compose bootstrap](deployment-local.md) and keep native Ollama running with `qwen3.5:4b`.
2. Open <http://127.0.0.1:8501> and enter a configured demo token. The admin token permits access to the audit and process-metrics views; investigations also work with a reader token.
3. Open **System Health** and confirm that FastAPI, PostgreSQL, Qdrant, and Ollama are ready.
4. Allow additional time for the first local model request. Integrated requests measured about 30 seconds median in the tracked development evaluation.
5. Use the [tracked evaluation summary](../evaluation/results/phase10-summary.md) to compare the live behavior with the recorded results.

## Run a multi-source investigation

Open **Investigation Copilot** and submit the evaluated U104 request:

> Investigate suspicious activity for U104 on 2026-08-31 and determine whether relevant password policy controls apply.

For this versioned case, LangGraph is expected to select policy retrieval, event search, and anomaly analysis from the six-tool read-only allowlist. Application code derives and validates identifiers, dates, filters, and result limits. The graph is bounded to three tool calls and five steps.

## Inspect the response

Review the response sections in this order:

1. **Observed evidence:** PostgreSQL security events with application-owned event IDs and attributes.
2. **ML analysis:** the exact Isolation Forest score, flag, feature values, model version, and provenance.
3. **Policy context:** fictional policy chunks with document, section, source, and chunk citations from Qdrant.
4. **AI interpretation:** Qwen's bounded synthesis, kept visibly separate from observed and retrieved evidence.
5. **Execution details:** selected tools, outcomes, source IDs, graph steps, and evidence sufficiency.

The LLM does not create citation or source fields. The committed U104 captures preserve the policy context exactly as returned by the evaluated local run:

- [structured security-event evidence](images/investigation-u104-events.png)
- [typed Isolation Forest analysis](images/investigation-u104-ml.png)
- [retrieved policy evidence and citations](images/investigation-u104-policy.png)

## Reproduce the U105 limitation

Submit:

> Is U105 behaving unusually on 2026-08-31?

The observed evidence includes successful logins from Germany at 10:00 UTC and Japan at 10:15 UTC. The typed ML result is:

```text
score   = -0.21107408822812324
flagged = false
```

Daily aggregate features do not explicitly calculate geographic travel velocity, so the Isolation Forest misses this sequence. The application preserves the event evidence and negative model result side by side rather than changing the flag. The committed captures show the [observed U105 events](images/investigation-u105-evidence.png) and [typed ML result](images/investigation-u105-ml.png).

## Verify system health

Open **System Health** with an admin token and verify:

- FastAPI, PostgreSQL, Qdrant, and Ollama report ready;
- process metrics expose only bounded counters and latency summaries;
- no sensitive configuration or request content is displayed.

The **Audit / About** view shows safe metadata for authenticated reads without storing prompts, evidence, or tokens. A reference [System Health capture](images/system-health.png) is included with the project.

Compare the running system with the [Phase 10 evaluation table](../evaluation/results/phase10-summary.md): top-five retrieval recall was 100%, relevance-gate acceptance was 34/39 (87.18%), the ML evaluation detected 5/6 scenarios with a 6.86% false-positive rate, integrated provenance fidelity was 20/20, and median local integrated latency was 29.563 seconds. These are synthetic development results.

## Additional example requests

These requests are part of the versioned integrated evaluation set:

- Policy only: `How long are daily backups retained under the backup policy?`
- Event only: `Show failed logins for U104 on 2026-08-31.`
- Exact event: `Investigate synthetic event EV000001.`
- Policy plus events: `What does the MFA policy require, and what failed login events were recorded for U104 on 2026-08-31?`
- ML only: `What is the anomaly score for U104 on 2026-08-31?`
- Insufficient evidence: `What is the policy for quantum key escrow?`
- Unknown entity: `What is the anomaly score for U999 on 2026-08-31?`

The final two requests intentionally exercise insufficient-evidence behavior.

## Expected behavior and limitations

- Streamlit communicates only with FastAPI; it does not directly access PostgreSQL, Qdrant, Ollama, LangGraph, or the ML service.
- Results separate observed records, ML analysis, retrieved policy context, generated interpretation, and recommendations.
- Policy retrieval uses a fixed `0.805` relevance threshold and can reject relevant material or return context that differs from an intuitive expectation.
- Generated prose may vary, but application-owned identifiers, citations, anomaly scores, flags, tool outcomes, and provenance must remain faithful to the returned evidence.
- Unknown identifiers, weak retrieval, missing dependencies, and ambiguous requests produce explicit partial or insufficient-evidence outcomes.
- All events and policies are synthetic or fictional. The measured results do not estimate production SOC performance.
