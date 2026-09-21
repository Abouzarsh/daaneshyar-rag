from __future__ import annotations

import asyncio
from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.dependencies import get_container
from app.api.schemas import HealthOut, StatsOut
from app.container import AppContainer

router = APIRouter(tags=["system"])


@router.get("/health", response_model=HealthOut)
async def health(
    container: Annotated[AppContainer, Depends(get_container)],
) -> HealthOut:
    vector = container.vector_store.health()
    llm, embeddings = await asyncio.gather(
        container.llm.health(),
        asyncio.to_thread(container.embeddings.health),
    )
    status = (
        "ok"
        if vector.get("ok") and llm.get("ok") and embeddings.get("ok")
        else "degraded"
    )
    return HealthOut(
        status=status,
        version=container.settings.app_version,
        components={
            "database": {"ok": True, "backend": "sqlite"},
            "vector_store": vector,
            "llm": llm,
            "embeddings": embeddings,
        },
    )


@router.get("/stats", response_model=StatsOut)
def stats(
    container: Annotated[AppContainer, Depends(get_container)],
) -> StatsOut:
    return StatsOut.model_validate(container.database.stats())
