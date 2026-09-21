def test_complete_document_and_chat_flow(client):
    content = (
        "سیاست دورکاری شرکت آریا\n"
        "کارکنان می‌توانند حداکثر دو روز در هفته دورکار باشند. "
        "ثبت درخواست باید تا پایان روز چهارشنبه انجام شود."
    )
    upload = client.post(
        "/api/v1/documents",
        files={"files": ("remote-policy.txt", content, "text/plain")},
    )
    assert upload.status_code == 202
    document_id = upload.json()["items"][0]["document"]["id"]

    documents = client.get("/api/v1/documents")
    assert documents.status_code == 200
    assert documents.json()[0]["status"] == "ready"
    assert documents.json()[0]["chunk_count"] == 1

    response = client.post(
        "/api/v1/chat/stream",
        json={"question": "چند روز در هفته می‌توان دورکار بود؟"},
    )
    assert response.status_code == 200
    assert "event: meta" in response.text
    assert "remote-policy.txt" in response.text
    assert "event: token" in response.text
    assert "event: done" in response.text

    conversations = client.get("/api/v1/conversations").json()
    assert len(conversations) == 1
    detail = client.get("/api/v1/conversations/" + conversations[0]["id"]).json()
    assert [item["role"] for item in detail["messages"]] == [
        "user",
        "assistant",
    ]
    assert detail["messages"][1]["citations"][0]["document_id"] == document_id


def test_duplicate_file_is_not_indexed_twice(client):
    files = {"files": ("same.txt", "یک متن تکراری برای آزمایش", "text/plain")}
    first = client.post("/api/v1/documents", files=files)
    second = client.post("/api/v1/documents", files=files)

    assert first.json()["items"][0]["status"] == "queued"
    assert second.json()["items"][0]["status"] == "duplicate"
    assert len(client.get("/api/v1/documents").json()) == 1


def test_invalid_extension_is_rejected(client):
    response = client.post(
        "/api/v1/documents",
        files={"files": ("payload.exe", b"not a document", "application/octet-stream")},
    )
    assert response.status_code == 202
    assert response.json()["items"][0]["status"] == "rejected"


def test_health_reports_all_local_demo_components(client):
    response = client.get("/api/v1/health")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["components"]["embeddings"]["detail"] == "ready"
    assert payload["components"]["llm"]["model"] == "extractive-demo"


def test_unknown_conversation_returns_404(client):
    response = client.post(
        "/api/v1/chat/stream",
        json={
            "question": "این پرسش معتبر است؟",
            "conversation_id": "does-not-exist",
        },
    )
    assert response.status_code == 404
