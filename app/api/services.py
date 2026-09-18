"""Application operations over existing repositories and the retrieval service."""

import json
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.db import repository
from app.db.models import AuditLog
from app.rag.service import RagService, Retrieval


class ApiService:
    def __init__(self, session: Session):
        self.session = session

    def audit(
        self, action: str, resource_type: str, resource_id: str | None, result: str, role: str
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
                details=json.dumps({"role": role}),
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

    def retrieval(self, rag: RagService, query: str, top_k: int) -> Retrieval:
        return rag.retrieve(query, top_k)
