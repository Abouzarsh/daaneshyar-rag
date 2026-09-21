from __future__ import annotations

import mimetypes
from pathlib import Path

import httpx

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SAMPLES = PROJECT_ROOT / "samples"
API_URL = "http://localhost:8000/api/v1"


def main() -> None:
    files = []
    for path in sorted(SAMPLES.iterdir()):
        if path.suffix.lower() not in {".txt", ".md", ".pdf", ".docx"}:
            continue
        mime = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        files.append(("files", (path.name, path.read_bytes(), mime)))

    if not files:
        raise SystemExit("No sample documents found.")

    with httpx.Client(timeout=60, trust_env=False) as client:
        try:
            client.get(API_URL + "/health").raise_for_status()
        except httpx.HTTPError as exc:
            raise SystemExit(
                "Backend is not available at http://localhost:8000"
            ) from exc
        response = client.post(API_URL + "/documents", files=files)
        response.raise_for_status()

    for item in response.json()["items"]:
        print(f"{item['filename']}: {item['status']}")


if __name__ == "__main__":
    main()
