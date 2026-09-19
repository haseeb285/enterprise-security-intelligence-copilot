"""API contract tests with isolated SQL and fake external services."""

from datetime import UTC, datetime
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr
from sqlalchemy import create_engine, func, select, text
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.main import create_app
from app.core.settings import Settings
from app.db.models import AuditLog, Base, Incident, SecurityEvent, User
from app.rag.service import Citation, Evidence, Retrieval

ADMIN = "A" * 32
READER = "R" * 32


class QdrantFake:
    def __init__(self):
        self.fail = False
        self.missing = False

    def get_collections(self):
        if self.fail:
            raise OSError("secret-internal-qdrant-location")
        return SimpleNamespace(
            collections=[]
            if self.missing
            else [SimpleNamespace(name="synthetic_policies_e5_small_v1")]
        )


class LlmFake:
    def __init__(self):
        self.reachable = True
        self.model_available = True

    def health(self):
        return SimpleNamespace(reachable=self.reachable, model_available=self.model_available)


class RagFake:
    def __init__(self):
        self.fail = False

    def retrieve(self, query, top_k):
        if self.fail:
            raise RuntimeError("private document content")
        return Retrieval(
            (
                Evidence(
                    "Synthetic evidence",
                    0.9,
                    "chunk-1",
                    Citation("Synthetic policy", "sample.md", "Section", None),
                ),
            ),
            False,
        )


@pytest.fixture
def api():
    engine = create_engine(
        "sqlite+pysqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(engine, expire_on_commit=False)
    now = datetime(2026, 9, 18, tzinfo=UTC)
    with Session(engine) as session, session.begin():
        session.add(
            User(
                user_id="U001",
                display_name="Example",
                department="IT",
                home_country="US",
                privileged=False,
                created_at=now,
            )
        )
        session.add(
            Incident(
                incident_id="INC001",
                title="Synthetic incident",
                severity="high",
                status="open",
                created_at=now,
                description="Demonstration incident",
            )
        )
        session.add(
            SecurityEvent(
                event_id="EV000001",
                timestamp=now,
                user_id="U001",
                source_ip="192.0.2.1",
                destination_ip=None,
                device_id=None,
                event_type="login",
                severity="high",
                action="login",
                status="failed",
                country="US",
                authentication_method=None,
                failed_attempts=1,
                successful_attempts=0,
                privileged_account=False,
                source="synthetic",
                description="Synthetic event",
                incident_id="INC001",
            )
        )
    qdrant, llm, rag = QdrantFake(), LlmFake(), RagFake()
    settings = Settings(
        demo_api_token=SecretStr(ADMIN),
        demo_read_token=SecretStr(READER),
        database_url=None,
        cors_origins=["http://localhost:8501"],
    )
    app = create_app(
        settings, session_factory=factory, qdrant_client=qdrant, llm_provider=llm, rag_service=rag
    )
    with TestClient(app) as client:
        yield client, factory, qdrant, llm, rag
    engine.dispose()


def test_request_correlation_and_admin_metrics(api):
    client, factory, *_ = api
    response = client.get("/api/v1/health", headers={"X-Request-ID": "phase11-live"})
    assert response.headers["X-Request-ID"] == "phase11-live"
    generated = client.get(
        "/api/v1/health", headers={"X-Request-ID": "unsafe request id with spaces"}
    ).headers["X-Request-ID"]
    assert generated != "unsafe request id with spaces" and len(generated) == 32

    assert client.get("/api/v1/metrics").status_code == 401
    assert client.get("/api/v1/metrics", headers=auth(READER)).status_code == 403
    response = client.get("/api/v1/metrics", headers=auth(ADMIN))
    assert response.status_code == 200
    assert response.json()["counters"]["api_requests_total"] >= 4
    assert "api_request_latency_ms" in response.json()["latency_ms"]
    with factory() as session:
        actions = list(
            session.scalars(select(AuditLog.action).where(AuditLog.action == "api_get_metrics"))
        )
    # Internal request/component telemetry does not create business audit entries.
    assert actions == ["api_get_metrics"]


def test_early_request_rejection_is_correlated(api):
    client, *_ = api
    response = client.post(
        "/api/v1/investigate",
        content=b"x" * 8193,
        headers={"X-Request-ID": "oversized-1", "Content-Type": "application/json"},
    )
    assert response.status_code == 413
    assert response.headers["X-Request-ID"] == "oversized-1"


def auth(token):
    return {"Authorization": f"Bearer {token}"}


def test_startup_health_and_openapi(api):
    client, _, qdrant, llm, _ = api
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json()["dependencies"] == {
        "application": "ok",
        "postgresql": "ok",
        "qdrant": "ok",
        "ollama": "ok",
    }
    schema = client.get("/api/v1/openapi.json").json()
    assert "/api/v1/events" in schema["paths"]
    assert "/api/v1/retrieval" in schema["paths"]
    assert schema["components"]["securitySchemes"]["HTTPBearer"]["scheme"] == "bearer"
    assert schema["paths"]["/api/v1/events"]["get"]["security"] == [{"HTTPBearer": []}]
    assert schema["paths"]["/api/v1/incidents"]["get"]["security"] == [{"HTTPBearer": []}]
    assert schema["paths"]["/api/v1/audit"]["get"]["security"] == [{"HTTPBearer": []}]
    assert schema["paths"]["/api/v1/metrics"]["get"]["security"] == [{"HTTPBearer": []}]
    assert "/api/v1/chat" not in schema["paths"]
    qdrant.fail = True
    llm.model_available = False
    degraded = client.get("/api/v1/health")
    assert degraded.status_code == 503
    assert degraded.json()["dependencies"]["ollama"] == "model_missing"
    assert "secret-internal" not in degraded.text
    qdrant.fail = False
    qdrant.missing = True
    assert client.get("/api/v1/health").json()["dependencies"]["qdrant"] == "collection_missing"


def test_auth_roles_and_events(api):
    client, factory, _, _, _ = api
    assert client.get("/api/v1/events").status_code == 401
    assert client.get("/api/v1/events", headers=auth("wrong")).status_code == 401
    assert client.get("/api/v1/incidents", headers=auth(READER)).status_code == 403
    events = client.get("/api/v1/events", headers=auth(READER)).json()
    assert events["total"] == 1 and events["items"][0]["event_id"] == "EV000001"
    assert client.get("/api/v1/events/EV000001", headers=auth(READER)).status_code == 200
    assert client.get("/api/v1/users/U001/events", headers=auth(READER)).json()["total"] == 1
    assert client.get("/api/v1/events?severity=low", headers=auth(READER)).json()["total"] == 0
    assert (
        client.get("/api/v1/events?source_ip=192.0.2.1", headers=auth(READER)).json()["total"] == 1
    )
    assert client.get("/api/v1/incidents", headers=auth(ADMIN)).json()["total"] == 1
    assert client.get("/api/v1/incidents/INC001", headers=auth(ADMIN)).status_code == 200
    with factory() as session:
        logs = list(session.scalars(select(AuditLog).where(AuditLog.action.like("api_%"))))
        assert len(logs) == 7
        assert all(
            READER not in (log.details or "") and ADMIN not in (log.details or "") for log in logs
        )
        assert session.scalar(select(func.count()).select_from(AuditLog)) == 7


def test_admin_only_audit_projection_omits_internal_details(api):
    client = api[0]
    assert client.get("/api/v1/audit", headers=auth(READER)).status_code == 403
    first = client.get("/api/v1/audit?limit=10", headers=auth(ADMIN))
    assert first.status_code == 200
    assert first.json() == {"items": [], "total": 0, "limit": 10, "offset": 0}
    second = client.get("/api/v1/audit?limit=10", headers=auth(ADMIN)).json()
    assert second["total"] == 1
    assert second["items"][0]["action"] == "api_list_audit"
    assert "details" not in second["items"][0]


@pytest.mark.parametrize(
    "url",
    [
        "/api/v1/events?limit=0",
        "/api/v1/events?limit=101",
        "/api/v1/events?offset=-1",
        "/api/v1/events?source_ip=invalid",
        "/api/v1/events?severity=urgent",
        "/api/v1/events?start_time=2026-01-01T00:00:00",
        "/api/v1/events?start_time=2026-09-20T00:00:00Z&end_time=2026-09-18T00:00:00Z",
        "/api/v1/events/garbage",
        "/api/v1/users/garbage/events",
        "/api/v1/incidents/garbage",
        "/api/v1/audit?limit=101",
    ],
)
def test_bad_inputs(api, url):
    client = api[0]
    result = client.get(url, headers=auth(ADMIN))
    assert result.status_code == 422
    assert result.json() == {"detail": "Invalid request input"}


def test_not_found_and_retrieval(api):
    client, factory, _, _, rag = api
    assert client.get("/api/v1/events/EV999999", headers=auth(READER)).status_code == 404
    assert client.get("/api/v1/incidents/INC999", headers=auth(ADMIN)).status_code == 404
    response = client.post(
        "/api/v1/retrieval", headers=auth(READER), json={"query": "synthetic policy?", "top_k": 3}
    )
    assert response.status_code == 200
    assert response.json()["evidence"][0]["citation"]["document"] == "Synthetic policy"
    assert (
        client.post(
            "/api/v1/retrieval", headers=auth(READER), json={"query": " ", "top_k": 3}
        ).status_code
        == 422
    )
    assert (
        client.post(
            "/api/v1/retrieval", headers=auth(READER), json={"query": "test", "top_k": 11}
        ).status_code
        == 422
    )
    rag.fail = True
    failed = client.post("/api/v1/retrieval", headers=auth(READER), json={"query": "test"})
    assert failed.status_code == 503
    assert "private document" not in failed.text
    with factory() as session:
        logs = list(
            session.scalars(select(AuditLog).where(AuditLog.action == "api_retrieve_policy"))
        )
        assert [log.result for log in logs] == ["success", "failure"]
        assert all("synthetic policy?" not in log.details for log in logs)


def test_cors_and_fail_closed(api):
    client = api[0]
    response = client.options(
        "/api/v1/events",
        headers={"Origin": "http://localhost:8501", "Access-Control-Request-Method": "GET"},
    )
    assert response.headers["access-control-allow-origin"] == "http://localhost:8501"
    denied = client.options(
        "/api/v1/events",
        headers={"Origin": "https://unknown.example", "Access-Control-Request-Method": "GET"},
    )
    assert "access-control-allow-origin" not in denied.headers
    with pytest.raises(RuntimeError, match="Set DEMO"):
        create_app(Settings(database_url=None))
    with pytest.raises(RuntimeError, match="distinct"):
        create_app(
            Settings(
                database_url=None, demo_api_token=SecretStr(ADMIN), demo_read_token=SecretStr(ADMIN)
            )
        )
    with pytest.raises(ValueError, match="CORS_ORIGINS"):
        Settings(cors_origins=["*"])


def test_database_failure_is_safe(api):
    client, factory, _, _, _ = api
    with factory() as session:
        session.execute(text("DROP TABLE security_events"))
        session.commit()
    response = client.get("/api/v1/events", headers=auth(READER))
    assert response.status_code == 503
    assert response.json() == {"detail": "PostgreSQL unavailable"}
    assert "security_events" not in response.text
    assert client.get("/api/v1/events").status_code == 401


def test_request_body_limit(api):
    client = api[0]
    response = client.post("/api/v1/retrieval", headers=auth(READER), json={"query": "a" * 9000})
    assert response.status_code == 413


def test_investigation_api_auth_validation_and_audit(api):
    from app.agent.schemas import RoutePlan, Synthesis

    client, factory, _, llm, _ = api

    def generate_structured(_prompt, schema, system=None):
        if schema is RoutePlan:
            return SimpleNamespace(
                value=RoutePlan(
                    classification="incident",
                    tools=["get_incident"],
                )
            )
        return SimpleNamespace(
            value=Synthesis(
                summary="Synthetic incident observed.",
                interpretation="The incident record describes denied authentication.",
                recommended_next_steps=["Review the incident record."],
            )
        )

    llm.generate_structured = generate_structured
    url = "/api/v1/investigate"
    assert client.post(url, json={"request": "Investigate INC001"}).status_code == 401
    assert client.post(url, headers=auth(ADMIN), json={"request": " "}).status_code == 422
    assert client.post(url, headers=auth(ADMIN), json={"request": "x" * 9000}).status_code == 413
    reader_result = client.post(url, headers=auth(READER), json={"request": "Investigate INC001"})
    assert reader_result.status_code == 200
    assert reader_result.json()["tool_results"]["get_incident"] == "forbidden"
    assert reader_result.json()["observed_evidence"] == []
    admin_result = client.post(url, headers=auth(ADMIN), json={"request": "Investigate INC001"})
    assert admin_result.status_code == 200
    assert admin_result.json()["sources"] == ["INC001"]
    assert admin_result.json()["outcome"] == "complete"
    schema = client.get("/api/v1/openapi.json").json()
    assert schema["paths"][url]["post"]["security"] == [{"HTTPBearer": []}]
    response_schema = schema["components"]["schemas"]["AgentResponse"]
    assert "ml_analysis" in response_schema["properties"]
    assert "MLEvidence" in schema["components"]["schemas"]
    assert admin_result.json()["ml_analysis"] == []
    with factory() as session:
        logs = list(session.scalars(select(AuditLog).where(AuditLog.action == "api_investigate")))
    assert len(logs) == 2
    assert '"selected_tools": ["get_incident"]' in logs[1].details
    assert "Investigate INC001" not in logs[1].details
    assert ADMIN not in logs[1].details
