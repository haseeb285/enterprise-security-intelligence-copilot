# Interview and CV guide

This guide helps the repository owner explain the implemented system accurately. Use the ideas in your own words and be ready to open the relevant code or measured result.

## 30-second explanation

I built a local security intelligence demonstration that combines RAG, a bounded LangGraph agent, and an Isolation Forest. A Streamlit user asks a policy or investigation question through FastAPI; the agent selectively retrieves synthetic events from PostgreSQL, fictional policy chunks from Qdrant, and typed anomaly evidence before a local Qwen model produces a grounded interpretation. The system keeps observed facts, ML output, policy context, and generated prose separate, and I evaluated each layer with versioned synthetic cases.

## 2-minute technical explanation

The frontend is a thin Streamlit HTTP client. FastAPI owns validation, demo bearer roles, audit logging, safe dependency handling, and OpenAPI contracts. For an investigation, a five-node LangGraph asks Qwen for tool names only, then application code reconstructs and validates identifiers, dates, filters, and limits from the user's request.

The six tools are read-only. They query deterministic synthetic events and incidents in PostgreSQL, retrieve fictional policy chunks from Qdrant using normalized multilingual E5 embeddings, or call a persisted Isolation Forest. That model scores 20 daily behavioral features and was trained with a chronological split; MLflow records the compared configurations and artifacts.

Evidence is serialized into separate observed, ML, and policy sections for local Qwen synthesis through Ollama. The application rebuilds sources and citations, rejects unknown IDs, filters unsupported score/flag claims and write actions, and returns partial or insufficient evidence when a dependency or lookup fails. Docker Compose reproduces the application services while Ollama remains native for Apple acceleration. The evaluation reports strengths and failures separately rather than presenting one accuracy number.

## End-to-end request flow

1. Streamlit sends an authenticated request and fresh request ID to FastAPI.
2. Pydantic validates size and shape; the demo principal is resolved as reader or admin.
3. LangGraph asks the local model for up to three tool names.
4. Deterministic routing intersects that proposal with explicit request intent and constructs bounded typed arguments.
5. Read-only adapters retrieve PostgreSQL records, Qdrant policy evidence, and/or Isolation Forest output.
6. The graph assesses completeness and serializes typed evidence as untrusted data.
7. Qwen creates a structured summary, interpretation, and limited next steps.
8. Application validation owns provenance, rejects unsupported identifiers, checks score/flag claims, and removes write recommendations.
9. FastAPI stores content-safe audit metadata and returns the structured response.
10. Streamlit renders observed evidence, ML, policy, interpretation, sources, and sufficiency separately.

## Why these technologies

| Choice | Reason in this project |
| --- | --- |
| FastAPI | Typed request/response models, dependency injection, automatic OpenAPI, and straightforward local HTTP integration. |
| PostgreSQL | Security events, incidents, users, and audits are relational and need filtered, indexed, transactional reads. |
| Qdrant | A local vector database that stores embeddings with citation metadata and supports reproducible retrieval. |
| `multilingual-e5-small` | A compact local embedding model with multilingual coverage, normalized vectors, and practical CPU use on the target laptop. E5's query/passage prefixes are applied explicitly. |
| Qwen 3.5 4B | A configurable local model small enough for the M3/16 GB target that produced schema-valid structured outputs in the measured suite. Its latency and occasional generic prose are documented. |
| LangGraph | Explicit typed state and fixed graph transitions make routing, bounds, partial failures, and finalization testable. It is used for orchestration rather than unrestricted autonomy. |
| Isolation Forest | An unsupervised baseline fits the lack of realistic labeled security data and produces rankable anomaly scores. It also exposes useful limitations that can be evaluated honestly. |
| MLflow | Local run tracking records parameters, metrics, and artifacts for the two training configurations without requiring a hosted platform. |
| Docker Compose | Reproduces service topology, migrations, seed/ingest/train bootstrap jobs, volumes, health checks, and container security settings. |
| Native Ollama | Keeps inference local, avoids paid APIs, preserves the provider boundary, and leaves the runtime outside Compose. Native execution can access Apple acceleration, but the recorded Phase 4 smoke run required CPU fallback and did not measure Metal performance. |

## Five concepts to understand well

### 1. RAG and relevance gating

RAG retrieves source text before generation. Here, documents are extracted and chunked, E5 embeds passages and queries with different prefixes, Qdrant returns ranked chunks, and a fixed cosine-score gate of `0.805` decides which chunks count as evidence. Recall@1/3/5 was 100%, but the gate accepted only 34/39 answerable queries. Ranking and answerability gating solve different problems: the right chunk can rank first yet still fall below a conservative threshold.

### 2. Agent routing and tool calling

The model proposes tool names, not executable code or trusted parameters. Application code infers permitted tools and arguments from explicit cues, removes unjustified proposals, adds required evidence sources, and enforces five graph steps, three calls, and bounded results. This is selective orchestration with deterministic guardrails, not an autonomous remediation agent.

### 3. Isolation Forest and feature engineering

Isolation Forest isolates uncommon points through random trees; shorter average paths imply greater anomaly. The application builds 20 UTC daily features such as event counts, failed/success ratios, unique IP/country/device counts, unusual-hour activity, event types, country transitions, active hours, and 15-minute density. Training precedes loading scenario labels, and a chronological split avoids future leakage. The score is not a probability.

### 4. Grounding, provenance, and hallucination control

Grounding means generated claims remain tied to supplied evidence. PostgreSQL and Qdrant adapters create typed records and citations; ML evidence carries exact model values and provenance. The LLM cannot author the response source list. Unknown IDs reject the synthesis, mismatched scores/flags are filtered, policy citations remain application-owned, and prompt-like evidence lines are masked before synthesis. These controls reduce specific failure modes but do not prove universal hallucination resistance.

### 5. Evaluation methodology

The evaluation separates retrieval, structured generation, routing, integrated behavior, ML, latency, and safety because one combined accuracy number would hide trade-offs. Expected routes and deterministic facts were declared before the run. The suite uses automatic structural/fidelity checks plus a recorded manual rubric for generated responses. All results are development measurements on synthetic data.

## Trade-offs and failure cases

- **Retrieval gate:** `0.805` rejected all eight unanswerable queries but also five answerable ones. Lowering it might improve acceptance while increasing irrelevant context; no threshold was tuned on the evaluation set.
- **ML false positives:** the selected Isolation Forest flagged 40/583 normal holdout observations, and only 11.11% of flagged observations belonged to the six synthetic scenarios.
- **Impossible-travel miss:** Germany and Japan logins 15 minutes apart produced score `-0.21107408822812324` and `flagged=false`. Daily aggregates do not explicitly calculate travel velocity.
- **Local LLM latency:** integrated median latency was 29.563 seconds. Local privacy and zero API cost trade against interactive speed.
- **Synthetic evaluation:** deterministic data enables reproducibility but does not represent production prevalence, adversaries, policy complexity, or operational outcomes.
- **Generic password answer:** the correct sixteen-character policy evidence was retrieved, but one generated answer remained generic. Retrieval success does not guarantee a direct answer.

## Likely interview questions

1. **Why use an agent instead of one RAG prompt?**
   Different questions require different evidence. Selective routing avoids running ML or database tools unnecessarily and makes execution observable and testable.

2. **How do you prevent the LLM from running arbitrary actions?**
   It can propose only a Pydantic enum of six read-only names. There is no shell, SQL, HTTP, credential, account, firewall, or write tool; parameters are reconstructed by code.

3. **How are citations kept trustworthy?**
   Citation document, source, section, page, and chunk ID come from ingestion metadata and tool results. They are returned in typed policy evidence rather than generated by Qwen.

4. **Why can Recall@1 be 100% while answerable acceptance is 87.18%?**
   Recall tests rank position before gating. Five correct rank-one chunks scored below the fixed threshold and were deliberately rejected.

5. **Why Isolation Forest, and what does its score mean?**
   It is an unsupervised baseline for scarce labels. Its decision score ranks relative normality under the trained feature distribution; it is not a compromise probability.

6. **How did you avoid ML leakage?**
   Features exclude scenario labels, incident IDs, severity, and descriptions; observations are split chronologically; models are fitted before scenario ground truth is loaded.

7. **Why did impossible travel fail despite country features?**
   A daily aggregate preserves country diversity and transitions but loses geographic distance and precise travel velocity. A sequence or explicit geo-velocity feature would address that, but was outside this baseline.

8. **What happens when one dependency fails?**
   Health becomes degraded. Tool failures return coarse codes without internal details; other evidence can still produce a partial response, while missing all support yields insufficient evidence.

9. **How do you evaluate generated answers without a cloud judge?**
   Pydantic and deterministic checks measure schemas, facts, provenance, sources, scores, flags, tool choices, and insufficiency. A small explicit manual rubric reviews factual support and directness.

10. **Why keep Ollama outside Docker?**
    It avoids duplicating a large model runtime in Compose, keeps provider configuration simple, and preserves access to native macOS acceleration. FastAPI reaches it through `host.docker.internal`. The recorded smoke run used CPU fallback, so I do not claim measured Metal performance.

11. **What would change for production?**
    Replace demo tokens with OIDC and managed RBAC, add TLS and managed secrets, review private-corpus access, centralize durable audit/telemetry, add rate limits and threat modeling, and evaluate with representative approved data.

12. **What result are you least satisfied with?**
    The 11.11% flagged precision and the impossible-travel miss show the daily unsupervised baseline is limited. They are useful because the system exposes rather than hides those failures.

13. **What would you improve first?**
    Define a better approved evaluation set, then compare sequence-aware or explicit travel-velocity features without tuning on the test cases. For user experience, investigate streaming or a faster local model while preserving structured validation.

## CV-ready project summary

### One line

Built a local evidence-grounded security investigation workflow combining RAG, bounded LangGraph tool routing, Isolation Forest anomaly detection, and structured Qwen inference over synthetic data.

### Two bullets

- Built a FastAPI and Streamlit investigation workflow that selectively combines PostgreSQL security events, cited Qdrant policy retrieval, and typed Isolation Forest output through a six-tool read-only LangGraph agent.
- Designed a versioned synthetic evaluation covering 47 retrieval and 20 integrated cases; measured 100% Recall@1/3/5, 20/20 provenance fidelity, and documented the 87.18% relevance-gate acceptance and known impossible-travel miss.

### Three bullets

- Implemented local RAG with `multilingual-e5-small`, Qdrant citation metadata, a fixed relevance gate, and explicit insufficient-evidence behavior for fictional policies.
- Engineered 20 leakage-checked daily features, chronological Isolation Forest training, persisted inference, and MLflow tracking; measured 5/6 synthetic scenario detection with a 6.86% false-positive rate.
- Delivered typed FastAPI contracts, bounded LangGraph orchestration, local Qwen structured generation, Docker Compose bootstrap, structured telemetry, 154 passing tests, and GitHub Actions validation with mocked Ollama behavior.
