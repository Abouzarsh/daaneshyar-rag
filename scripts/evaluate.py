from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

import httpx

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATASET = PROJECT_ROOT / "docs" / "evaluation-set.json"
REPORTS = PROJECT_ROOT / "reports"
API_URL = "http://localhost:8000/api/v1"


def parse_sse(text: str) -> list[tuple[str, dict[str, Any]]]:
    events = []
    for block in text.replace("\r\n", "\n").split("\n\n"):
        event = "message"
        data = None
        for line in block.splitlines():
            if line.startswith("event:"):
                event = line[6:].strip()
            if line.startswith("data:"):
                data = json.loads(line[5:].strip())
        if data is not None:
            events.append((event, data))
    return events


def main() -> None:
    cases = json.loads(DATASET.read_text(encoding="utf-8"))
    results = []
    with httpx.Client(timeout=240, trust_env=False) as client:
        for case in cases:
            started = time.perf_counter()
            response = client.post(
                API_URL + "/chat/stream",
                json={"question": case["question"]},
            )
            response.raise_for_status()
            events = parse_sse(response.text)
            meta = next(data for event, data in events if event == "meta")
            answer = "".join(
                data.get("content", "")
                for event, data in events
                if event == "token"
            )
            sources = {source["document_name"] for source in meta["sources"]}
            passed = case["expected_document"] in sources
            result = {
                "id": case["id"],
                "passed": passed,
                "latency_ms": round((time.perf_counter() - started) * 1000),
                "expected_document": case["expected_document"],
                "retrieved_documents": sorted(sources),
                "answer": answer,
            }
            results.append(result)
            print(("PASS" if passed else "FAIL") + "  " + case["id"])

    REPORTS.mkdir(exist_ok=True)
    target = REPORTS / "evaluation.json"
    target.write_text(
        json.dumps(results, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    passed_count = sum(item["passed"] for item in results)
    print(f"\n{passed_count}/{len(results)} retrieval checks passed")
    print(f"Report: {target}")


if __name__ == "__main__":
    main()
