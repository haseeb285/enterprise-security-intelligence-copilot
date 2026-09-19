"""Allowlisted read-only evidence tools backed by existing services."""

import re
from collections.abc import Callable
from math import ceil

from app.agent.routing import required_tools
from app.agent.schemas import EvidenceRecord, MLEvidence, ToolDecision, ToolName
from app.api.services import ApiService
from app.db.repository import EventFilters
from app.ml.model import IncompatibleModelArtifact, ModelArtifactError
from app.ml.service import (
    AnomalyDetectionService,
    InsufficientHistoryError,
    InvalidAnalysisWindow,
    UnknownUserError,
)
from app.rag.service import RagService


class ToolInputError(ValueError):
    pass


class ToolAccessError(PermissionError):
    pass


class ToolExecutionError(RuntimeError):
    """Safe failure label for a bounded tool execution."""

    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


class AgentTools:
    def __init__(
        self,
        service: ApiService,
        rag_loader: Callable[[], RagService],
        anomaly_service: AnomalyDetectionService | None = None,
    ):
        self.service = service
        self.rag_loader = rag_loader
        self.anomaly_service = anomaly_service

    def run(
        self, decision: ToolDecision, request: str, role: str
    ) -> list[EvidenceRecord | MLEvidence]:
        if decision.name == ToolName.search_security_events:
            requested_users = re.findall(r"\bU\d{3}\b", request)
            requested_incidents = re.findall(r"\bINC\d{3}\b", request)
            if (requested_users and decision.user_id not in requested_users) or (
                requested_incidents and decision.incident_id not in requested_incidents
            ):
                raise ToolInputError("explicit identifier missing from event filter")
        if decision.user_id and decision.user_id not in re.findall(r"\bU\d{3}\b", request):
            raise ToolInputError("user identifier not supplied by requester")
        if decision.incident_id and decision.incident_id not in re.findall(
            r"\bINC\d{3}\b", request
        ):
            raise ToolInputError("incident identifier not supplied by requester")
        if decision.event_id and decision.event_id not in re.findall(r"\bEV\d{6}\b", request):
            raise ToolInputError("event identifier not supplied by requester")
        if decision.name == ToolName.search_policy:
            policy_query = self._policy_clause(request)
            result = self.service.retrieval(self.rag_loader(), policy_query, top_k=3)
            if not self._policy_relevant(request, [item.text for item in result.evidence]):
                return []
            return [
                EvidenceRecord(
                    kind="policy",
                    source_id=item.chunk_id,
                    source=item.citation.source,
                    text=item.text[:1000],
                    citation={
                        "document": item.citation.document,
                        "source": item.citation.source,
                        "section": item.citation.section,
                        "page": item.citation.page,
                    },
                )
                for item in result.evidence[:3]
            ]
        if decision.name == ToolName.search_security_events:
            start, end = decision.start_time, decision.end_time
            if (
                decision.user_id
                and ToolName.analyze_user_anomaly in required_tools(request)
                and start is None
                and end is None
                and self.anomaly_service is not None
            ):
                try:
                    start, end = self.anomaly_service.default_user_window(decision.user_id)
                except (UnknownUserError, InsufficientHistoryError):
                    # The event query can still return its own independent evidence.
                    pass
            filters = EventFilters(
                user_id=decision.user_id,
                incident_id=decision.incident_id,
                event_type=decision.event_type,
                severity=decision.severity.value if decision.severity else None,
                start_time=start,
                end_time=end,
            )
            page = self.service.events(filters, limit=decision.limit, offset=0)
            return [self._event(item) for item in page.items]
        if decision.name == ToolName.get_user_events:
            page = self.service.user_events(decision.user_id, limit=decision.limit, offset=0)
            return [self._event(item) for item in page.items]
        if decision.name == ToolName.get_event:
            item = self.service.event(decision.event_id)
            return [self._event(item)] if item is not None else []
        if decision.name == ToolName.get_incident:
            if role != "admin":
                raise ToolAccessError("incident tool requires admin")
            item = self.service.incident(decision.incident_id)
            if item is None:
                return []
            return [
                EvidenceRecord(
                    kind="incident",
                    source_id=item.incident_id,
                    source="postgresql.incidents",
                    text=(
                        f"{item.title}; severity={item.severity}; status={item.status}; "
                        f"created_at={item.created_at.isoformat()}; {item.description}"
                    )[:1000],
                    attributes={
                        "severity": str(item.severity),
                        "status": item.status,
                        "created_at": item.created_at.isoformat(),
                    },
                )
            ]
        if decision.name == ToolName.analyze_user_anomaly:
            return [self._anomaly(decision)]
        raise ToolInputError("tool not allowed")

    def _anomaly(self, decision: ToolDecision) -> MLEvidence:
        if self.anomaly_service is None:
            raise ToolExecutionError("dependency_failure")
        try:
            start, end = decision.start_time, decision.end_time
            if start is None or end is None:
                start, end = self.anomaly_service.default_user_window(decision.user_id)
            result = self.anomaly_service.analyze_user(decision.user_id, start, end)
        except UnknownUserError as exc:
            raise ToolExecutionError("unknown_entity") from exc
        except InsufficientHistoryError as exc:
            raise ToolExecutionError("insufficient_history") from exc
        except (InvalidAnalysisWindow, ValueError) as exc:
            raise ToolExecutionError("invalid_window") from exc
        except (FileNotFoundError, IncompatibleModelArtifact, ModelArtifactError) as exc:
            raise ToolExecutionError("dependency_failure") from exc
        except Exception as exc:
            raise ToolExecutionError("inference_failure") from exc
        source_id = (
            f"ml:{result.model_version}:user:{result.entity_id}:"
            f"{result.window_start.date().isoformat()}"
        )
        return MLEvidence(
            **result.model_dump(),
            source_id=source_id,
            provenance={
                "service": "app.ml.service.AnomalyDetectionService",
                "model_version": result.model_version,
                "data_source": "postgresql.security_events",
            },
        )

    @staticmethod
    def _policy_clause(request: str) -> str:
        return re.split(
            r",\s+and\s+|\s+and\s+(?=(?:what|which|did|were|show|summarize)\b)",
            request,
            maxsplit=1,
            flags=re.I,
        )[0].strip()

    @staticmethod
    def _policy_relevant(request: str, texts: list[str]) -> bool:
        """Conservative subject check on top of the RAG score threshold."""
        if not texts:
            return False
        clause = AgentTools._policy_clause(request)
        words = set(re.findall(r"[a-zA-Z]{3,}", clause.lower()))
        words -= {
            "the",
            "what",
            "which",
            "how",
            "does",
            "did",
            "this",
            "that",
            "policy",
            "policies",
            "require",
            "requires",
            "requirement",
            "requirements",
            "for",
            "from",
            "under",
            "are",
            "was",
            "were",
            "with",
            "about",
            "cooperative",
            "their",
            "when",
            "who",
            "long",
            "many",
            "much",
            "determine",
            "whether",
            "relevant",
            "controls",
            "apply",
            "investigate",
            "suspicious",
            "activity",
        }
        if not words:
            return True
        corpus = " ".join(texts).lower()
        synonyms = {"mfa": "multifactor authentication", "vpn": "virtual private network"}
        hits = sum(word in corpus or synonyms.get(word, "\x00") in corpus for word in words)
        return hits >= max(1, ceil(len(words) / 2))

    @staticmethod
    def _event(item) -> EvidenceRecord:
        attributes = {
            "timestamp": item.timestamp.isoformat(),
            "user_id": item.user_id,
            "event_type": item.event_type,
            "severity": str(item.severity),
            "status": item.status,
            "source_ip": item.source_ip,
            "device_id": getattr(item, "device_id", None),
            "country": getattr(item, "country", None),
            "incident_id": item.incident_id,
        }
        return EvidenceRecord(
            kind="event",
            source_id=item.event_id,
            source="postgresql.security_events",
            text=(
                f"timestamp={item.timestamp.isoformat()}; user_id={item.user_id}; "
                f"event_type={item.event_type}; severity={item.severity}; "
                f"status={item.status}; source_ip={item.source_ip}; "
                f"device_id={getattr(item, 'device_id', None)}; "
                f"country={getattr(item, 'country', None)}; incident_id={item.incident_id}; "
                f"description={item.description}"
            )[:1000],
            related_ids=[value for value in (item.user_id, item.incident_id) if value],
            attributes=attributes,
        )
