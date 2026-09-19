"""Application operations over existing repositories and the retrieval service."""

import json
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session

from app.core.settings import Settings
from app.db import repository
from app.db.models import AuditLog
from app.rag.embeddings import get_embedder
from app.rag.service import RagService, Retrieval
from app.rag.store import VectorStore


def build_rag_service(settings: Settings, qdrant_client: Any) -> RagService:
    """Lazily load the one cached embedder and reuse the lifespan Qdrant connection."""
    embedder = get_embedder(settings.embedding_model)
    store = VectorStore(
        str(settings.qdrant_url),
        settings.rag_collection,
        embedder.dimension,
        client=qdrant_client,
    )
    return RagService(
        store,
        embedder,
        settings.rag_chunk_target_chars,
        settings.rag_chunk_overlap_chars,
        settings.rag_min_score,
    )


class ApiService:
    def __init__(self, session: Session):
        self.session = session

    def audit(
        self,
        action: str,
        resource_type: str,
        resource_id: str | None,
        result: str,
        role: str,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        # Demo principals have no user record; never store credentials or queries.
        self.session.add(
            AuditLog(
                timestamp=datetime.now(UTC),
                actor_user_id=None,
                action=action,
                resource_type=resource_type,
                resource_id=resource_id,
                result=result,
                details=json.dumps({"role": role, **(metadata or {})}),
            )
        )
        self.session.commit()

    def events(self, filters: repository.EventFilters, limit: int, offset: int):
        return repository.search_events(self.session, filters, limit=limit, offset=offset)

    def event(self, event_id: str):
        return repository.get_event(self.session, event_id)

    def user_events(self, user_id: str, limit: int, offset: int):
        return repository.get_user_events(self.session, user_id, limit=limit, offset=offset)

    def incidents(self, limit: int, offset: int):
        return repository.get_incidents(self.session, limit=limit, offset=offset)

    def incident(self, incident_id: str):
        return repository.get_incident(self.session, incident_id)

    def audit_logs(self, limit: int, offset: int):
        return repository.get_audit_logs(self.session, limit=limit, offset=offset)

    def retrieval(self, rag: RagService, query: str, top_k: int) -> Retrieval:
        return rag.retrieve(query, top_k)
