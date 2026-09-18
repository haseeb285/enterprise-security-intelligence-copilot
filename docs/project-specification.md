You are the lead AI/ML Engineer and Software Engineer responsible for building a complete portfolio-grade project from end to end.

PROJECT NAME
Enterprise Security Intelligence Copilot

PRIMARY GOAL
Build a genuinely working, technically defensible, production-style AI engineering portfolio project demonstrating:

- Python
- FastAPI
- REST APIs
- SQL
- PostgreSQL
- Generative AI
- Local LLM inference
- RAG
- Embeddings
- Vector search
- Agentic AI
- Tool/function calling
- LangGraph
- Machine Learning
- Anomaly Detection
- MLflow
- Evaluation
- Docker
- Docker Compose
- Automated testing
- GitHub Actions / CI
- Observability
- Security engineering principles
- Professional software architecture

This project is intended for an AI/ML Engineer / GenAI Engineer / AI Solutions Engineer / Data Scientist portfolio.

It must NOT be a superficial chatbot or tutorial project.

==================================================
1. DEVELOPMENT ENVIRONMENT
==================================================

Primary development machine:

MacBook Air
Apple M3
16 GB unified memory
macOS
Apple Silicon ARM64

The complete development environment must be practical on this hardware.

IMPORTANT:

Run Ollama NATIVELY on macOS so Apple Silicon / Metal acceleration can be used.

Containerize application infrastructure where appropriate.

Likely Docker services include:

- FastAPI backend
- PostgreSQL
- Qdrant
- MLflow
- Streamlit frontend

The Dockerized application should communicate with Ollama running on the macOS host using an appropriate configuration such as host.docker.internal.

Prefer ARM64-compatible Docker images.

Avoid unnecessary memory consumption.

Do not run multiple large LLMs simultaneously.

Prefer a suitable quantized local model approximately in the 4B–8B range.

The model must be configurable.

Do NOT require a discrete GPU.

==================================================
2. COST / INFRASTRUCTURE CONSTRAINTS
==================================================

The project must NOT require:

- OpenAI API
- Anthropic API
- paid LLM APIs
- Azure subscription
- AWS subscription
- GCP subscription
- commercial SIEM
- commercial vector database
- proprietary enterprise infrastructure

The complete core project must run locally.

Use open-source/local components.

Future cloud deployment should remain possible but is NOT required for the initial implementation.

Do not claim cloud deployment unless it is actually performed.

==================================================
3. SECURITY / PRIVACY CONSTRAINTS
==================================================

Never expose:

- company confidential information
- real customer information
- internal credentials
- API keys
- passwords
- private documents
- proprietary security data
- personally identifiable information

Any security events included in the repository must be synthetic.

Any public demonstration policies must be synthetic.

If I later provide private policies:

- use them only as local development inputs
- do not commit them
- do not reproduce their confidential contents in public files
- do not expose organization names or metadata
- add appropriate paths to .gitignore

Clearly label synthetic data as synthetic.

==================================================
4. SYSTEM CONCEPT
==================================================

Build an Enterprise Security Intelligence Copilot.

The system should allow a user to:

1. Ask questions about enterprise security policies.
2. Search enterprise knowledge through RAG.
3. Investigate synthetic security events.
4. Ask questions about user/device activity.
5. Allow an AI agent to select appropriate tools.
6. Perform ML-based anomaly detection.
7. Combine:
   - structured security evidence
   - ML results
   - retrieved policy information
   - LLM reasoning
8. Produce evidence-based responses.
9. Show citations/sources.
10. Clearly state when evidence is insufficient.

Conceptual architecture:

User
 |
 v
Streamlit
 |
 v
FastAPI
 |
 v
Validation / Authentication
 |
 v
LangGraph Agent
 |
 +----------------------------+
 |              |             |
 v              v             v
RAG          Security       ML Analysis
 |             Tools           |
 v              |              v
Qdrant      PostgreSQL    Anomaly Model
 |
 v
Policies

                 |
                 v
              Ollama

Supporting systems:

- PostgreSQL
- Qdrant
- MLflow
- structured logging
- evaluation
- automated tests
- Docker
- GitHub Actions

==================================================
5. TECHNOLOGY GUIDANCE
==================================================

Preferred technologies:

Python 3.11 or 3.12

Backend:
- FastAPI
- Uvicorn
- Pydantic
- SQLAlchemy
- Alembic

AI:
- Ollama
- LangGraph
- LangChain only where it provides genuine value
- Hugging Face / Sentence Transformers

ML:
- scikit-learn

Vector database:
- Qdrant

Database:
- PostgreSQL

Frontend:
- Streamlit

MLOps:
- MLflow

Testing:
- pytest
- pytest-asyncio
- HTTPX

Quality:
- Ruff
- type hints

Configuration:
- pydantic-settings
- environment variables

Infrastructure:
- Docker
- Docker Compose

CI:
- GitHub Actions

IMPORTANT:

Do not blindly use these libraries if current compatibility or a simpler implementation makes another choice clearly better.

Before implementing a major dependency, verify that it is current, maintained, compatible with Apple Silicon/Python version, and appropriate.

If you choose a different technology, document WHY.

Do not add technologies merely for CV keywords.

Every major technology claimed in README must actually be used.

==================================================
6. LOCAL LLM ARCHITECTURE
==================================================

Use Ollama as the default local inference provider.

Do not tightly couple the application to one LLM.

Create a clean provider abstraction.

Conceptually:

LLMProvider
    |
    +-- OllamaProvider

Configuration should include:

OLLAMA_BASE_URL
OLLAMA_MODEL

Do not hard-code the model throughout the application.

Choose an appropriate default model for an M3 Mac with 16 GB unified memory.

If the model is unavailable, provide a clear actionable error.

Do not automatically download extremely large models.

==================================================
7. RAG KNOWLEDGE SYSTEM
==================================================

Implement a proper RAG pipeline.

Support at minimum:

- PDF
- Markdown
- TXT

Pipeline:

Document
 ↓
Extraction
 ↓
Validation
 ↓
Cleaning
 ↓
Chunking
 ↓
Metadata
 ↓
Embeddings
 ↓
Qdrant
 ↓
Retrieval
 ↓
Grounded generation

Metadata should include where possible:

- document name
- document type
- page
- section
- chunk ID
- source
- ingestion timestamp

Requirements:

- detect empty extraction
- avoid duplicate ingestion where practical
- preserve citation metadata
- provide source references in answers
- handle retrieval failure gracefully
- implement a minimum relevance mechanism
- do not hallucinate policy requirements

If sufficient evidence is unavailable, say so.

Example:

"I could not find sufficient information in the available knowledge base to answer this reliably."

Create a clean ingestion CLI or script.

==================================================
8. SYNTHETIC SECURITY ENVIRONMENT
==================================================

Create realistic but fictional security data.

Example fields:

event_id
timestamp
user_id
source_ip
destination_ip
device
event_type
severity
action
status
country
authentication_method
failed_attempts
successful_attempts
privileged_account
source
description

Example event types:

- failed_login
- successful_login
- unusual_login
- impossible_travel
- account_lockout
- privilege_change
- suspicious_process
- malware_detection
- firewall_block
- endpoint_alert

Use documentation/example IP ranges where appropriate rather than accidentally representing real infrastructure.

Use deterministic random seeds.

Generate enough events to support useful analytics while remaining lightweight.

The dataset must clearly state:

SYNTHETIC DEMONSTRATION DATA.

==================================================
9. SIMULATED SIEM
==================================================

Implement a simulated SIEM/security-event interface.

DO NOT describe it as a real SIEM integration.

Provide functionality such as:

GET /events
GET /events/{event_id}
GET /users/{user_id}/events
GET /incidents
GET /incidents/{incident_id}
GET /events/search

Allow filtering by:

- user
- time
- severity
- event type
- IP
- device

The AI agent should interact with this system through defined tools/functions rather than accessing arbitrary database state.

==================================================
10. AGENTIC AI
==================================================

Use LangGraph for meaningful orchestration.

Do NOT create fake agentic behavior where every tool runs regardless of the question.

The agent should determine which evidence/tools are required.

Potential tools:

search_policy()
search_security_events()
get_user_events()
get_incident()
run_anomaly_detection()
get_security_statistics()

Possible conceptual graph:

START
 |
 v
Request Analysis
 |
 +---------------------------+
 |                           |
Policy Request          Security Investigation
 |                           |
 v                           v
RAG                       Event Tools
 |                           |
 |                           v
 |                       ML Analysis
 |                           |
 +------------+--------------+
              |
              v
        Evidence Aggregation
              |
              v
         LLM Reasoning
              |
              v
        Output Validation
              |
              v
            END

Use structured state.

Use structured outputs where appropriate.

The agent must never invent events.

Security claims must be traceable to retrieved data.

==================================================
11. MACHINE LEARNING
==================================================

Implement a genuine ML component using synthetic security data.

Use an appropriate anomaly detection method.

Isolation Forest is a reasonable starting point, but evaluate whether it is suitable.

Possible features:

- failed login frequency
- unique source IP count
- unique country count
- unusual login hour
- privileged account indicator
- successful/failed ratio
- event frequency
- device diversity

Implement:

- feature engineering
- training
- inference
- model persistence
- experiment tracking
- evaluation

Use MLflow meaningfully.

Do not fabricate accuracy or performance.

Explicitly document:

"This model is trained and evaluated on synthetic demonstration data and is not a production security detection engine."

==================================================
12. ML + GENAI INTEGRATION
==================================================

The strongest demonstration should combine traditional ML and GenAI.

Example question:

"Is user U104 behaving suspiciously?"

Expected workflow:

1. Agent determines investigation is required.
2. Query event data.
3. Aggregate relevant activity.
4. Run anomaly model.
5. Retrieve relevant security policy if appropriate.
6. Assemble evidence.
7. Ask LLM to explain evidence.
8. Return structured response.

Response should distinguish:

OBSERVED EVIDENCE

ML ANALYSIS

POLICY CONTEXT

AI INTERPRETATION

RECOMMENDED NEXT STEPS

SOURCES

The LLM must not present its interpretation as observed fact.

==================================================
13. FASTAPI
==================================================

Create a clean versioned API.

Potential routes:

/api/v1/chat
/api/v1/documents
/api/v1/events
/api/v1/incidents
/api/v1/analysis
/api/v1/audit
/api/v1/health

Use:

- Pydantic models
- dependency injection
- correct status codes
- validation
- exception handling
- OpenAPI documentation
- structured responses

Avoid giant route files.

==================================================
14. DATABASE
==================================================

Use PostgreSQL.

Potential entities:

- security_events
- incidents
- users
- audit_logs

Use SQLAlchemy.

Use Alembic migrations.

A fresh environment must be initializable without manually creating database tables.

==================================================
15. APPLICATION SECURITY
==================================================

Implement reasonable demo security controls:

- request validation
- secrets via environment
- .env excluded from Git
- .env.example
- authentication
- basic role concepts
- audit logging
- safe error responses
- input size limits
- output validation

Do not pretend simple demo authentication is enterprise production authentication.

Document production improvements such as:

- OAuth2/OIDC
- Microsoft Entra ID / enterprise IdP
- Keycloak
- proper RBAC
- TLS
- secret manager
- network segmentation

==================================================
16. FRONTEND
==================================================

Build a professional but simple Streamlit UI.

Potential areas:

Dashboard
Copilot
Security Investigation
Knowledge Base
ML Analytics
System Health
Audit Logs

Users should be able to:

- ask questions
- investigate users/events
- inspect retrieved evidence
- see policy citations
- see anomaly results
- inspect system health

Functionality is more important than elaborate design.

==================================================
17. EVALUATION
==================================================

Evaluation is mandatory.

Create a representative evaluation dataset.

Include:

- answerable policy questions
- unanswerable policy questions
- security investigations
- multi-tool requests
- ambiguous requests
- failure cases

Measure meaningful metrics where feasible.

RAG:

- retrieval recall
- context relevance
- citation/source correctness

Generation:

- groundedness/faithfulness
- answer correctness where measurable
- citation correctness

Agent:

- correct tool selection
- task completion
- error handling

System:

- latency
- failures

Do NOT fabricate results.

README metrics must come from actual runs.

==================================================
18. TESTING
==================================================

Implement meaningful tests.

Unit tests:

- chunking
- metadata
- feature engineering
- validation
- anomaly model logic
- prompt/structured output logic

Integration tests:

- database
- Qdrant
- FastAPI
- tools

API tests:

- health
- events
- chat
- authentication
- invalid requests

RAG tests:

- retrieval
- citations
- no-answer behavior

Agent tests:

- tool selection
- multi-step workflows
- failures

Avoid meaningless tests written only to increase coverage.

Tests must run with:

pytest

==================================================
19. DOCKER
==================================================

Use Docker Compose for appropriate services.

Likely:

api
frontend
postgres
qdrant
mlflow

Ollama should initially run natively on macOS.

Provide:

Dockerfile(s)
docker-compose.yml
.dockerignore

The project should be reproducible.

Document the complete startup process.

==================================================
20. CI/CD
==================================================

Create GitHub Actions workflows.

On push / pull request:

- install dependencies
- lint
- run appropriate tests
- build application image

Do not make CI require a real locally running Ollama server.

Mock LLM inference appropriately in automated tests.

==================================================
21. OBSERVABILITY
==================================================

Implement useful observability without unnecessary infrastructure.

Track where practical:

- API requests
- latency
- failures
- LLM latency
- retrieval latency
- tool execution
- anomaly inference latency
- token counts when available

Use structured logging.

Expose health information.

Only add Prometheus or additional monitoring infrastructure if the benefit justifies the complexity.

==================================================
22. PROJECT STRUCTURE
==================================================

Design a clean maintainable repository.

A likely structure is:

app/
    api/
    agents/
    rag/
    ml/
    database/
    models/
    schemas/
    services/
    tools/
    core/
    evaluation/

frontend/

tests/

scripts/

docs/

data/

Do not treat this structure as mandatory if a cleaner architecture emerges.

Avoid giant files.

Use:

- type hints
- meaningful names
- docstrings where useful
- separation of concerns

==================================================
23. DOCUMENTATION
==================================================

Create professional documentation.

README.md should include:

- project overview
- business problem
- architecture
- capabilities
- technology stack
- setup
- architecture diagram
- RAG workflow
- agent workflow
- ML workflow
- API
- evaluation
- actual results
- testing
- security
- limitations
- future improvements
- demo examples

Create:

docs/architecture.md
docs/api.md
docs/rag.md
docs/agent.md
docs/ml.md
docs/evaluation.md
docs/security.md
docs/deployment.md
docs/limitations.md

Use Mermaid for architecture diagrams where useful.

==================================================
24. DEMONSTRATION
==================================================

Create a reproducible demonstration covering:

1. Policy question
2. Policy citation
3. Security investigation
4. Agent tool selection
5. Multi-tool investigation
6. ML anomaly analysis
7. ML + RAG + LLM combined response
8. Unsupported question / insufficient evidence
9. API request
10. Local application startup

==================================================
25. GITHUB / SECRET SAFETY
==================================================

Before completion, inspect the repository for:

- API keys
- tokens
- passwords
- credentials
- private documents
- confidential organization names
- personal data
- accidental environment files

Create and verify:

.gitignore
.env.example

Never commit .env.

==================================================
26. DEVELOPMENT WORKFLOW
==================================================

THIS IS CRITICAL.

Do NOT attempt to implement the entire project in one uncontrolled pass.

Work incrementally.

PHASE 0
Environment inspection + architecture plan

PHASE 1
Repository foundation + configuration

PHASE 2
PostgreSQL + synthetic security data

PHASE 3
RAG ingestion + embeddings + Qdrant

PHASE 4
Ollama/local LLM integration

PHASE 5
FastAPI

PHASE 6
LangGraph agent + tools

PHASE 7
ML anomaly detection + MLflow

PHASE 8
Agent + RAG + ML integration

PHASE 9
Streamlit frontend

PHASE 10
Evaluation framework

PHASE 11
Observability

PHASE 12
Docker / Docker Compose

PHASE 13
GitHub Actions

PHASE 14
Testing + hardening

PHASE 15
Documentation + demo

PHASE 16
Final engineering audit

At the end of each phase:

1. Inspect changed files.
2. Run relevant tests.
3. Run linting.
4. Verify imports.
5. Verify relevant components start.
6. Fix failures.
7. Summarize what changed.
8. Commit or prepare a logical Git checkpoint.

Do not knowingly build later phases on broken earlier phases.

==================================================
27. CODING BEHAVIOR
==================================================

When working:

FIRST inspect existing code.

Do not overwrite good working implementations unnecessarily.

Do not create duplicate implementations.

Do not introduce a dependency without understanding why it is required.

Do not suppress errors merely to make tests pass.

Do not weaken tests to hide bugs.

Do not hard-code fake outputs.

Do not create placeholder implementations and describe them as complete.

Do not fabricate successful command execution.

Do not fabricate benchmark results.

Do not fabricate evaluation results.

Do not claim something works unless it has actually been tested where the environment allows.

If an external dependency prevents testing, state exactly what could and could not be verified.

==================================================
28. ERROR HANDLING
==================================================

Handle failures explicitly.

Examples:

Ollama unavailable
→ clear actionable error

PostgreSQL unavailable
→ unhealthy dependency status

Qdrant unavailable
→ retrieval service failure

Empty knowledge base
→ instruct user to ingest documents

No relevant document
→ insufficient evidence response

Unknown event
→ 404

Invalid request
→ validation response

Tool failure
→ logged controlled failure

Never silently swallow important exceptions.

==================================================
29. PERFORMANCE
==================================================

Optimize for:

Apple M3
16 GB unified memory

Avoid:

- enormous local models
- excessive containers
- unnecessary background services
- loading multiple embedding/LLM models repeatedly
- excessive synthetic datasets
- memory-heavy architectures without benefit

Measure before optimizing.

==================================================
30. PROJECT INTEGRITY
==================================================

This portfolio project must distinguish between:

ACTUALLY IMPLEMENTED
software, architecture, experiments, tests

SYNTHETIC
security events, fictional organization, demonstration policies

SIMULATED
SIEM/security platform

NOT CLAIMED
production SOC deployment
real-world attack detection
real customer deployment
real enterprise SIEM integration
cloud deployment unless actually performed

==================================================
31. FINAL VALIDATION
==================================================

Before declaring the project complete, validate as much as the environment permits:

- Python environment
- imports
- linting
- unit tests
- integration tests
- API tests
- PostgreSQL
- Qdrant
- synthetic data generation
- document ingestion
- vector retrieval
- Ollama connection
- LLM response
- LangGraph workflow
- tool calling
- ML training
- ML inference
- MLflow
- evaluation
- Streamlit
- Docker build
- Docker Compose
- health endpoints
- GitHub Actions configuration

For every failure:

diagnose
→ fix
→ rerun
→ verify

Do not declare COMPLETE with known critical failures.

==================================================
32. FINAL AUDIT
==================================================

At the end verify that these capabilities are genuinely represented:

Python
FastAPI
REST APIs
PostgreSQL
SQL
RAG
Embeddings
Vector DB
Local LLM
Ollama
LangGraph
Agentic AI
Tool calling
Machine Learning
Anomaly Detection
MLflow
Evaluation
Docker
Docker Compose
Testing
CI/CD
Security
Authentication
Authorization concepts
Audit logging
Observability
Documentation

For each determine:

IMPLEMENTED?
USED?
TESTED?
DOCUMENTED?

Do not add a technology simply to make every row say yes.

Technical credibility is more important than keyword count.

==================================================
33. PERSISTENT CODEX INSTRUCTIONS
==================================================

Create an AGENTS.md file near the beginning of the project containing the important persistent engineering rules from this specification.

Create:

docs/project-specification.md

containing the complete project requirements.

This prevents future Codex sessions from depending on this original chat prompt.

Future work should consult AGENTS.md and the project specification before making architectural changes.

==================================================
34. BEGIN
==================================================

BEGIN WITH PHASE 0 ONLY.

Inspect my actual development environment.

Determine at minimum:

- macOS / architecture
- Python availability/version
- Git availability/version
- Docker availability/version
- Ollama availability/version
- available disk space if practical
- repository status
- existing files

Then:

1. Assess whether the proposed stack is appropriate for this machine.
2. Identify compatibility concerns.
3. Recommend the local Ollama model strategy.
4. Propose the final architecture.
5. Propose the repository structure.
6. Create AGENTS.md.
7. Create docs/project-specification.md containing this project specification.
8. Create a phased implementation checklist.

DO NOT implement Phase 1 yet.

DO NOT install large models yet.

DO NOT start building the application yet.

At the end, give me a concise Phase 0 report containing:

- environment findings
- architecture decision
- important technology decisions
- expected resource considerations
- files created
- blockers, if any
- exact proposed Phase 1 work

Then STOP and wait for my approval before Phase 1.