# Architecture

## Product boundary

Daaneshyar is a single-user, local-first document assistant. Version 1.0 is
optimized for transparent retrieval, an easy local setup, and code that can be
discussed in a technical interview. It is not presented as a multi-tenant SaaS.

## Components

~~~mermaid
flowchart TB
    subgraph Browser
        UI["React RTL client"]
        SSE["SSE parser"]
    end

    subgraph API["FastAPI application"]
        DOC["Document routes"]
        CHAT["Chat route"]
        ING["Ingestion service"]
        RET["Hybrid retriever"]
        PIPE["RAG pipeline"]
    end

    subgraph Data
        SQL["SQLite metadata + FTS5"]
        VEC["Qdrant vectors"]
        FILES["Local uploads"]
    end

    subgraph Models
        EMB["Ollama embeddinggemma"]
        LLM["Ollama / compatible LLM"]
    end

    UI --> DOC
    UI --> CHAT
    CHAT --> SSE
    DOC --> ING
    ING --> FILES
    ING --> EMB
    ING --> SQL
    ING --> VEC
    CHAT --> PIPE
    PIPE --> RET
    RET --> SQL
    RET --> VEC
    RET --> EMB
    PIPE --> LLM
~~~

## Ingestion sequence

~~~mermaid
sequenceDiagram
    participant U as User
    participant A as API
    participant I as Ingestion
    participant E as Embeddings
    participant Q as Qdrant
    participant S as SQLite

    U->>A: Upload document
    A->>A: Validate size and extension
    A->>A: Calculate SHA-256
    A->>S: Create queued document
    A-->>U: 202 + document id
    A->>I: Background ingestion
    I->>I: Extract and normalize
    I->>I: Sentence-aware chunking
    I->>E: Embed chunks
    E-->>I: Dense vectors
    I->>Q: Upsert vectors
    I->>S: Save chunks + FTS rows
    I->>S: Mark document ready
~~~

The file is written before a background task starts. A failed ingestion removes
partial vectors and lexical rows, marks the document failed, and keeps a short
error description for the UI.

## Query sequence

~~~mermaid
sequenceDiagram
    participant U as User
    participant A as API
    participant R as Retriever
    participant Q as Qdrant
    participant S as FTS5
    participant L as LLM

    U->>A: Question
    A->>R: Retrieve top evidence
    par Semantic branch
        R->>Q: Query embedding
        Q-->>R: Dense ranking
    and Lexical branch
        R->>S: Normalized terms
        S-->>R: BM25 ranking
    end
    R->>R: Weighted RRF
    R-->>A: Diverse source chunks
    A-->>U: SSE meta event + sources
    A->>L: Grounded prompt
    loop Generated tokens
        L-->>A: Token
        A-->>U: SSE token event
    end
    A-->>U: SSE done event
~~~

## Retrieval details

Dense search uses the multilingual embedding model and cosine similarity in
Qdrant. Lexical search uses normalized text in a SQLite FTS5 virtual table.

Ranks are fused rather than raw scores because cosine similarity and BM25 scores
are not directly comparable. For a chunk at rank r, its contribution is:

    contribution = weight / (60 + r)

The default dense and lexical weights are 0.65 and 0.35. The retriever then
limits the number of chunks from a single document, preventing one long file
from crowding all other evidence out of the prompt.

## Citation contract

The model sees each source in a numbered, delimited block. The same ordered
source list is sent to the client before generation begins. This keeps UI
citations tied to retrieval results instead of trying to reconstruct citations
from generated prose.

The model is instructed to use inline markers such as [1]. Version 1.0 does not
claim that every marker emitted by an arbitrary model is valid. A production
extension should validate marker ranges and calculate citation precision.

## Data model

| Table | Responsibility |
| --- | --- |
| documents | Upload identity, checksum, processing status, file metadata |
| chunks | Extracted content, page, chunk order, and document relation |
| chunks_fts | Lexical index of normalized chunk text |
| conversations | Conversation title and timestamps |
| messages | User/assistant content plus a citation snapshot |

Qdrant payload stores chunk_id, document_id, page_number, and chunk_index.
Complete text remains in SQLite so vector storage is not treated as the source
of truth.

## Failure handling

- Invalid types and oversized files are rejected before indexing.
- Duplicate content is detected before embeddings are computed.
- Vector writes are removed if metadata persistence fails.
- A failed document remains visible with its error instead of disappearing.
- Chat errors are emitted as explicit SSE error events.
- Reverse-proxy buffering is disabled for the streaming endpoint.

## Security notes

Source text is wrapped as data and the system prompt explicitly says to ignore
instructions found inside documents. This is a useful first boundary, not a
complete prompt-injection defense.

Before internet-facing deployment, add authentication, authorization,
tenant-level filters, malware scanning, rate limiting, encrypted object
storage, a secrets manager, and an audit trail.

## Decision record

### No LangChain in the core

The goal is to make retrieval mechanics readable. The project uses small
interfaces for embeddings, vector storage, and LLM streaming. A framework can
be added later without rewriting domain behavior.

### SQLite FTS5 instead of a second search service

For a local portfolio project, FTS5 gives exact-term retrieval, simple backup,
and no extra container. PostgreSQL or OpenSearch would be reasonable when
tenancy, high write volume, or distributed search becomes a requirement.

### FastAPI BackgroundTasks instead of a durable queue

It keeps setup small and makes ingestion status visible. The tradeoff is that
jobs do not survive a process crash. A production version should move ingestion
to a durable worker queue.

### SSE instead of WebSockets

Chat output is one-way after the request begins. SSE works through standard HTTP,
is easy to inspect, and needs less connection lifecycle code than WebSockets.

### Store citation snapshots with messages

Documents can later change or be deleted. Saving the citation payload alongside
the answer preserves what the user saw when the answer was produced.
