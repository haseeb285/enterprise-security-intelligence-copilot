"""Authenticated evidence-only knowledge retrieval."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.exc import SQLAlchemyError

from app.api.dependencies import Principal, get_api_service, get_principal
from app.api.schemas import ErrorOut, RetrievalIn, RetrievalOut
from app.api.services import ApiService
from app.rag.embeddings import get_embedder
from app.rag.service import RagService
from app.rag.store import VectorStore

router = APIRouter(tags=["Knowledge"])


@router.post(
    "/retrieval",
    response_model=RetrievalOut,
    responses={401: {"model": ErrorOut}, 422: {"model": ErrorOut}, 503: {"model": ErrorOut}},
    summary="Retrieve cited policy evidence",
    description="Evidence only; does not generate an answer. Requires a reader or admin token.",
    dependencies=[Depends(get_principal)],
)
def retrieve(
    body: RetrievalIn,
    request: Request,
    service: Annotated[ApiService, Depends(get_api_service)],
    principal: Annotated[Principal, Depends(get_principal)],
):
    settings = request.app.state.settings
    try:
        rag = request.app.state.rag_service
        if rag is None:
            embedder = get_embedder(settings.embedding_model)
            store = VectorStore(
                str(settings.qdrant_url),
                settings.rag_collection,
                embedder.dimension,
                client=request.app.state.qdrant,
            )
            rag = RagService(
                store,
                embedder,
                settings.rag_chunk_target_chars,
                settings.rag_chunk_overlap_chars,
                settings.rag_min_score,
            )
        result = service.retrieval(rag, body.query, body.top_k)
        service.audit("api_retrieve_policy", "knowledge", None, "success", principal.role)
        return result
    except SQLAlchemyError as exc:
        service.session.rollback()
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "PostgreSQL unavailable") from exc
    except Exception as exc:
        try:
            service.audit("api_retrieve_policy", "knowledge", None, "failure", principal.role)
        except SQLAlchemyError as audit_exc:
            service.session.rollback()
            raise HTTPException(
                status.HTTP_503_SERVICE_UNAVAILABLE, "PostgreSQL unavailable"
            ) from audit_exc
        # No provider/embedding exception details or query text are sent to clients.
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE, "Knowledge retrieval unavailable"
        ) from exc
