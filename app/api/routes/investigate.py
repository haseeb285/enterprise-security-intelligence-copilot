"""Versioned, authenticated LangGraph investigation endpoint."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.exc import SQLAlchemyError

from app.agent.graph import InvestigationAgent
from app.agent.schemas import AgentResponse
from app.agent.tools import AgentTools
from app.api.dependencies import Principal, get_api_service, get_principal
from app.api.schemas import ErrorOut
from app.api.services import ApiService, build_rag_service

router = APIRouter(tags=["Investigation"])


class InvestigationIn(BaseModel):
    request: str = Field(min_length=1, max_length=4000)

    @field_validator("request")
    @classmethod
    def nonblank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Request cannot be blank")
        return value


@router.post(
    "/investigate",
    response_model=AgentResponse,
    responses={401: {"model": ErrorOut}, 422: {"model": ErrorOut}, 503: {"model": ErrorOut}},
    summary="Investigate synthetic security evidence",
    description=(
        "A bounded read-only LangGraph workflow selects only needed policy, event, user-event, "
        "and incident tools. Incident evidence requires the admin role. The response separates "
        "observed evidence from model interpretation."
    ),
    dependencies=[Depends(get_principal)],
)
def investigate(
    body: InvestigationIn,
    request: Request,
    principal: Annotated[Principal, Depends(get_principal)],
    service: Annotated[ApiService, Depends(get_api_service)],
):
    def rag_loader():
        return request.app.state.rag_service or build_rag_service(
            request.app.state.settings, request.app.state.qdrant
        )

    agent = InvestigationAgent(request.app.state.llm, AgentTools(service, rag_loader))
    result = agent.run(body.request, principal.role)
    metadata = {
        "selected_tools": [name.value for name in result.selected_tools],
        "tool_results": result.tool_results,
        "tool_calls": result.tool_calls,
        "graph_steps": result.graph_steps,
        "outcome": result.outcome,
    }
    try:
        service.audit(
            "api_investigate",
            "investigation",
            None,
            result.outcome,
            principal.role,
            metadata=metadata,
        )
    except SQLAlchemyError as exc:
        service.session.rollback()
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "PostgreSQL unavailable") from exc
    return result
