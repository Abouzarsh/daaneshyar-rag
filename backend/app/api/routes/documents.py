from __future__ import annotations

import hashlib
import re
import uuid
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, UploadFile

from app.api.dependencies import get_container
from app.api.schemas import DeleteResponse, DocumentOut, UploadItem, UploadResponse
from app.container import AppContainer

router = APIRouter(prefix="/documents", tags=["documents"])


def _public_document(document: dict) -> DocumentOut:
    return DocumentOut.model_validate(document)


def _safe_display_name(filename: str | None) -> str:
    name = Path(filename or "document").name.strip()
    name = re.sub(r"[\x00-\x1f\x7f]", "", name)
    return name[:180] or "document"


@router.get("", response_model=list[DocumentOut])
def list_documents(
    container: Annotated[AppContainer, Depends(get_container)],
) -> list[DocumentOut]:
    return [
        _public_document(document) for document in container.database.list_documents()
    ]


@router.post("", response_model=UploadResponse, status_code=202)
async def upload_documents(
    background_tasks: BackgroundTasks,
    files: Annotated[list[UploadFile], File(description="PDF, DOCX, TXT, or MD")],
    container: Annotated[AppContainer, Depends(get_container)],
) -> UploadResponse:
    if not files:
        raise HTTPException(status_code=400, detail="At least one file is required")

    items: list[UploadItem] = []
    settings = container.settings

    for upload in files:
        display_name = _safe_display_name(upload.filename)
        extension = Path(display_name).suffix.lower()
        if extension not in settings.allowed_extension_set:
            items.append(
                UploadItem(
                    filename=display_name,
                    status="rejected",
                    detail=f"Unsupported file type: {extension or 'unknown'}",
                )
            )
            await upload.close()
            continue

        document_id = str(uuid.uuid4())
        stored_name = f"{document_id}{extension}"
        temp_path = settings.uploads_path / f"{stored_name}.part"
        final_path = settings.uploads_path / stored_name
        checksum = hashlib.sha256()
        size = 0

        try:
            with temp_path.open("wb") as destination:
                while chunk := await upload.read(1024 * 1024):
                    size += len(chunk)
                    if size > settings.max_upload_bytes:
                        raise ValueError(
                            f"File exceeds the {settings.max_upload_mb} MB limit"
                        )
                    checksum.update(chunk)
                    destination.write(chunk)
        except ValueError as exc:
            temp_path.unlink(missing_ok=True)
            items.append(
                UploadItem(
                    filename=display_name,
                    status="rejected",
                    detail=str(exc),
                )
            )
            await upload.close()
            continue
        finally:
            await upload.close()

        if size == 0:
            temp_path.unlink(missing_ok=True)
            items.append(
                UploadItem(
                    filename=display_name,
                    status="rejected",
                    detail="File is empty",
                )
            )
            continue

        digest = checksum.hexdigest()
        duplicate = container.database.find_active_document_by_checksum(digest)
        if duplicate:
            temp_path.unlink(missing_ok=True)
            items.append(
                UploadItem(
                    filename=display_name,
                    status="duplicate",
                    detail="This file is already in the knowledge base",
                    duplicate_of=str(duplicate["id"]),
                )
            )
            continue

        temp_path.replace(final_path)
        document = container.database.create_document(
            document_id=document_id,
            name=display_name,
            stored_name=stored_name,
            mime_type=upload.content_type,
            size_bytes=size,
            checksum=digest,
        )
        background_tasks.add_task(
            container.ingestion.ingest,
            document_id,
            final_path,
        )
        items.append(
            UploadItem(
                filename=display_name,
                status="queued",
                document=_public_document(document),
            )
        )

    return UploadResponse(items=items)


@router.delete("/{document_id}", response_model=DeleteResponse)
def delete_document(
    document_id: str,
    container: Annotated[AppContainer, Depends(get_container)],
) -> DeleteResponse:
    if not container.documents.delete(document_id):
        raise HTTPException(status_code=404, detail="Document not found")
    return DeleteResponse(deleted=True, id=document_id)
