# 3–5 minute portfolio demo

This walkthrough uses the real Streamlit → FastAPI path and the seeded synthetic dataset. Do not paste a prepared response or hard-code output: generated wording can vary, while typed evidence, tool choices, citations, scores, and flags remain application-owned.

## Prepare before presenting

1. Complete the [Docker Compose bootstrap](deployment-local.md) and keep native Ollama running with `qwen3.5:4b`.
2. Open <http://127.0.0.1:8501> and enter the admin demo token. The admin token allows the final audit view; the investigation itself also works with a reader token.
3. Confirm **System Health** reports FastAPI, PostgreSQL, Qdrant, and Ollama ready.
4. Run each investigation once before the presentation so the local model is warm. Clear or replace the visible result by submitting the question again during the demo.
5. Keep the [tracked evaluation summary](../evaluation/results/phase10-summary.md) open in a separate browser tab.

Local integrated requests measured about 30 seconds median, so narrate the architecture while the model runs.

## Demo story

### 1. Establish the dataset — Dashboard (20–30 seconds)

Open **Dashboard**. Point out that the UI is showing 12,065 deterministic synthetic events and six incidents through FastAPI. Explain that Streamlit has no direct PostgreSQL, Qdrant, Ollama, LangGraph, or ML access.

### 2. Start one multi-source investigation — Copilot (45–75 seconds)

Open **Investigation Copilot** and submit this evaluated question:

> Investigate suspicious activity for U104 on 2026-08-31 and determine whether relevant password policy controls apply.

While it runs, explain that LangGraph can select at most three names from a six-tool read-only allowlist. For this versioned case, the expected tools are policy retrieval, event search, and anomaly analysis. Identifiers, dates, filters, and result limits are derived and validated by application code rather than accepted from model-generated arguments.

### 3. Read the evidence in order (60–90 seconds)

When the result appears, show these sections without promising exact generated prose:

1. **Observed evidence:** PostgreSQL security events with application-owned event IDs and attributes.
2. **ML analysis:** the exact Isolation Forest score, flag, feature values, model version, and provenance.
3. **Policy context:** fictional policy chunks with document, section, source, and chunk citations from Qdrant.
4. **AI interpretation:** Qwen's bounded synthesis, visibly separate from evidence.
5. **Execution details:** selected tools, outcomes, source IDs, graph steps, and evidence sufficiency.

Emphasize that the LLM does not create the citation or source fields.

### 4. Show an honest model limitation — U105 (45–75 seconds)

Submit:

> Is U105 behaving unusually on 2026-08-31?

Show the two successful-login events: Germany at 10:00 UTC and Japan at 10:15 UTC. Then show the typed ML result:

```text
score   = -0.21107408822812324
flagged = false
```

Explain that daily aggregate features do not explicitly model geographic travel velocity. The model therefore misses this obvious sequence. The application keeps the event evidence and negative model flag side by side; it does not change the flag to make the answer look better.

### 5. Close with evaluation and operations (30–45 seconds)

Open **System Health** to show dependency readiness and bounded admin metrics, then briefly show **Audit / About** to demonstrate that authenticated reads create safe audit metadata without prompts, evidence, or tokens.

Finish on the [Phase 10 evaluation table](../evaluation/results/phase10-summary.md): perfect top-five retrieval ranking but 87.18% gate acceptance, 5/6 ML scenario detection with 6.86% false positives, 20/20 integrated provenance fidelity, and roughly 29.6-second median local latency. These are synthetic development results.

## Other evaluated questions

Use these when an interviewer asks to explore a narrower path:

- Policy only: `How long are daily backups retained under the backup policy?`
- Event only: `Show failed logins for U104 on 2026-08-31.`
- Exact event: `Investigate synthetic event EV000001.`
- Policy plus events: `What does the MFA policy require, and what failed login events were recorded for U104 on 2026-08-31?`
- ML only: `What is the anomaly score for U104 on 2026-08-31?`
- Insufficient evidence: `What is the policy for quantum key escrow?`
- Unknown entity: `What is the anomaly score for U999 on 2026-08-31?`

These requests are in the versioned integrated evaluation set. The last two intentionally demonstrate insufficient-evidence behavior.

## Screenshot checklist

Capture only after the live stack has produced the real view. Keep browser zoom and window size consistent, crop unused chrome, and do not expose `.env`, terminal history, bearer tokens, local usernames, or unrelated applications.

1. **Dashboard:** navigation, readiness, totals, and one useful chart.
2. **Three-source investigation:** observed events, typed ML evidence, and at least one policy citation; capture another section only if the first image remains readable.
3. **U105 disagreement:** Germany/Japan evidence and `flagged = false` visible together or in a clearly paired crop.
4. **Evaluation or System Health:** use the tracked Phase 10 table or live ready dependencies and aggregate metrics.

Suggested filenames are `dashboard.png`, `investigation.png`, `u105-disagreement.png`, and `evaluation-health.png` under a future `docs/images/` directory. Add only screenshots captured from this repository's real local run, then reference them from the README. No screenshots are currently committed.
