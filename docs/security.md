# Local demonstration security boundary

The API is a portfolio demonstration over synthetic telemetry and fictional policies. Its `DEMO_READ_TOKEN` and `DEMO_API_TOKEN` are **demo authentication**, not enterprise SSO, and must never be reused as production credentials. Both are supplied through environment settings, kept out of Git, compared with constant-time comparison, and required to be distinct with at least 24 characters. The reader role can view events and cited policy evidence. The admin role can additionally view incidents. Public health reveals only coarse dependency states.

Input is constrained by Pydantic models and route parameters, including ID patterns, enum severity, timezone-aware timestamps, IP address validation, pagination caps, query length, and a POST body limit. Repositories use SQLAlchemy parameter binding and bounded reads. Error responses omit submitted values and dependency exception details. CORS is disabled by default and accepts only explicit HTTP(S) origins. This is a local loopback service; use `127.0.0.1` for the Uvicorn bind address.

Meaningful authenticated reads append audit entries in PostgreSQL. Each entry has an action, resource category, optional synthetic resource ID, outcome, and role. Demo principals are not mapped to synthetic `users`, so `actor_user_id` is null. Query text, retrieved policy content, event payloads, bearer tokens, and connection strings are not written to audit details. The admin-only audit API returns a bounded safe projection and omits its internal details payload. The seed guard tolerates added audit entries while checking the seeded data counts. A seed reset intentionally replaces the local synthetic dataset and audit rows.

For a real deployment, replace demo bearer tokens with OAuth2/OIDC through Entra ID, Keycloak, or another identity provider. Add managed user/group authorization, token lifecycle and revocation, TLS, rate limiting, centralized tamper-resistant audit and log storage, secret management, provenance and access controls for private policy corpora, and an explicit deployment threat model. No production security or real-world detection performance is claimed.

## Phase 11 operational telemetry boundary

Request IDs, JSON logs, and in-process metrics use explicit field and label allowlists. They record timings, counts, component names, safe outcomes, model/version names, aggregate result counts, and stable error categories. They omit submitted requests, prompts, system instructions, evidence text and attributes, generated prose, credentials, connection strings, exception messages, local paths, and hidden reasoning. Unsafe caller-supplied request IDs are replaced.

Operational telemetry and the business audit trail have different purposes. Internal spans never write audit rows. Admin access to the aggregate metrics route is itself an audited API action. The local logger and process registry are not tamper-resistant or durable and do not replace a production monitoring and audit architecture.

## Phase 6 agent boundary

The investigation graph has an explicit tool allowlist and read-only service adapters. It accepts no arbitrary tool name, SQL statement, shell command, or write operation. Model-proposed parameters are parsed with Pydantic bounds; IDs must match strict formats and appear in the request. The incident tool enforces the admin role even if routing selects it for a reader. There are fixed graph/tool/result limits and zero retries.

Retrieved policy chunks and event/incident descriptions are untrusted input. They are serialized as data for the synthesis prompt, separated from system instructions; obvious instruction lines are masked for synthesis while the original source remains in the observed response. Output source IDs and citations are rebuilt from tool results, and generated IDs absent from structured source metadata are rejected. System-changing next-step suggestions are filtered. Known unsupported certainty and absence patterns in generated summaries and interpretations are replaced with conservative application text. This does not guarantee that every natural-language interpretation is factually correct or immune to all prompt injection. Phase 6 tests include a malicious policy chunk, and the development evaluation remains synthetic. Audit metadata excludes prompts, policy text, bearer tokens, and hidden reasoning.

## Phase 8 ML evidence boundary

The anomaly tool is read-only and calls the existing service with an application-derived user and bounded time window. It cannot accept arbitrary model paths, SQL, feature definitions, or model parameters from the LLM. The trusted local joblib artifact remains ignored because loading joblib can execute Python. Missing, corrupt, or incompatible artifacts produce coarse dependency labels.

Observed records, ML output, policy context, interpretation, and recommendations have separate response fields and prompt sections. The application owns event IDs, policy citations, ML source IDs, score, flag, feature values, and model version. Inexact generated score references are removed. ML failure can yield a partial response from remaining sources, with an explicit unavailable reason. The prompt-injection fixture proves that a malicious retrieved line is masked before synthesis, though broad semantic prompt-injection resistance is not claimed.

The graph has no account, password, firewall, process, permission, deletion, arbitrary shell, or arbitrary SQL action. Recommendations containing bounded write-action terms are removed. The system remains a local synthetic demonstration, and anomaly results are not treated as attack determinations.

## Phase 9 frontend boundary

Streamlit is an HTTP client of FastAPI. It has no PostgreSQL, Qdrant, Ollama, LangGraph, or anomaly-service imports and no direct connection configuration for those systems. The API owns validation, role enforcement, audit, tool selection, evidence provenance, and dependency errors.

The user supplies a demo bearer token through a password input. It remains in Streamlit session memory and is sent in the authorization header; it is not hardcoded, logged, placed in the URL, or persisted by the frontend. The API target must be an explicit HTTP(S) URL without embedded credentials. Deployment would require proper identity, TLS, CSRF/session analysis, browser security headers, rate limiting, and managed secrets.

API text and records are untrusted display data. The UI uses Streamlit's text and structured components without unsafe HTML, removes control characters, and bounds long text. It presents model output and LLM interpretation as separate categories and does not convert the anomaly result into a security determination.
