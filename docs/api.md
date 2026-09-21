# API guide

Interactive OpenAPI documentation is exposed at http://localhost:8000/docs.
All application endpoints use the /api/v1 prefix.

## Upload documents

    curl -X POST http://localhost:8000/api/v1/documents \
      -F "files=@samples/network-operations-handbook-fa.md" \
      -F "files=@samples/remote-work-policy-fa.txt"

The endpoint returns HTTP 202. Each item has one of these states:

| State | Meaning |
| --- | --- |
| queued | Saved and scheduled for ingestion |
| duplicate | The same SHA-256 already exists |
| rejected | Type, size, or content validation failed |

Poll GET /api/v1/documents until queued or indexing becomes ready or failed.

## Stream a question

    curl -N http://localhost:8000/api/v1/chat/stream \
      -H "Content-Type: application/json" \
      -d '{"question":"در رخداد P1 زمان واکنش چقدر است؟"}'

Optional request fields:

| Field | Type | Purpose |
| --- | --- | --- |
| conversation_id | string | Continue an existing conversation |
| document_ids | string array | Restrict retrieval to selected ready documents |
| top_k | integer | Number of evidence chunks, from 1 to 12 |

The response is text/event-stream.

### meta event

Sent after retrieval and before model generation:

    event: meta
    data: {
      "conversation_id": "...",
      "message_id": "...",
      "retrieval_ms": 42,
      "model": "qwen3:4b",
      "sources": [
        {
          "index": 1,
          "document_name": "network-operations-handbook-fa.md",
          "page_number": null,
          "excerpt": "...",
          "score": 1.0,
          "retrieval_methods": ["keyword", "semantic"]
        }
      ]
    }

### token event

    event: token
    data: {"content":"بخش بعدی پاسخ"}

### done event

    event: done
    data: {
      "conversation_id": "...",
      "message_id": "...",
      "total_ms": 1480
    }

### error event

The HTTP request may already have started when the model fails, so generation
errors are represented inside the stream:

    event: error
    data: {
      "message": "پیام قابل نمایش برای کاربر",
      "code": "ConnectError"
    }

## Health

GET /api/v1/health returns separate status for SQLite, vector storage,
embeddings, and the LLM. An unavailable LLM is reported as a component problem;
document management remains usable.

## Typical status codes

| Code | Meaning |
| --- | --- |
| 200 | Read, delete, or stream request accepted |
| 202 | Upload accepted for background processing |
| 400 | Invalid document selection or malformed request |
| 404 | Document or conversation not found |
| 422 | Pydantic request validation failed |
| 500 | Unexpected server error before streaming began |
