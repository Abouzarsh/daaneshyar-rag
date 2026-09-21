from __future__ import annotations

import asyncio
import time
from collections.abc import AsyncIterator, Sequence
from typing import Any

from app.db.database import Database
from app.rag.llm import LLMProvider
from app.rag.prompts import build_prompts
from app.rag.retriever import HybridRetriever


class RAGPipeline:
    def __init__(
        self,
        *,
        database: Database,
        retriever: HybridRetriever,
        llm: LLMProvider,
        default_top_k: int = 6,
        history_limit: int = 8,
    ):
        self.database = database
        self.retriever = retriever
        self.llm = llm
        self.default_top_k = default_top_k
        self.history_limit = history_limit

    async def stream_answer(
        self,
        *,
        question: str,
        conversation_id: str | None = None,
        document_ids: Sequence[str] | None = None,
        top_k: int | None = None,
    ) -> AsyncIterator[tuple[str, dict[str, Any]]]:
        started = time.perf_counter()
        if conversation_id:
            conversation = self.database.get_conversation(conversation_id)
            if conversation is None:
                raise KeyError("Conversation not found")
        else:
            conversation = self.database.create_conversation(question)
            conversation_id = str(conversation["id"])

        history = self.database.recent_messages(
            conversation_id,
            limit=self.history_limit,
        )
        user_message = self.database.add_message(
            conversation_id=conversation_id,
            role="user",
            content=question,
        )

        retrieval_started = time.perf_counter()
        sources = await asyncio.to_thread(
            self.retriever.retrieve,
            question,
            top_k=top_k or self.default_top_k,
            document_ids=document_ids,
        )
        retrieval_ms = round((time.perf_counter() - retrieval_started) * 1000)
        citations = [
            source.citation_dict(index) for index, source in enumerate(sources, start=1)
        ]

        yield (
            "meta",
            {
                "conversation_id": conversation_id,
                "message_id": user_message["id"],
                "sources": citations,
                "retrieval_ms": retrieval_ms,
                "model": self.llm.model_name,
            },
        )

        if not sources:
            answer = (
                "در اسناد موجود اطلاعات مرتبط و قابل اتکایی برای پاسخ به این "
                "پرسش پیدا نکردم. می‌توانید سند دقیق‌تری اضافه کنید یا پرسش را "
                "با جزئیات بیشتری بنویسید."
            )
            yield "token", {"content": answer}
        else:
            system_prompt, user_prompt = build_prompts(question, sources)
            pieces: list[str] = []
            async for token in self.llm.stream(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                history=[
                    {"role": item["role"], "content": item["content"]}
                    for item in history
                ],
            ):
                pieces.append(token)
                yield "token", {"content": token}
            answer = "".join(pieces).strip()
            if not answer:
                answer = "مدل زبانی پاسخی تولید نکرد. وضعیت سرویس مدل را بررسی کنید."
                yield "token", {"content": answer}

        assistant_message = self.database.add_message(
            conversation_id=conversation_id,
            role="assistant",
            content=answer,
            citations=citations,
        )
        yield (
            "done",
            {
                "conversation_id": conversation_id,
                "message_id": assistant_message["id"],
                "total_ms": round((time.perf_counter() - started) * 1000),
            },
        )
