import asyncio
import csv
import logging
import sys
from pathlib import Path

from sqlalchemy import select

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))

from app.db.models import MedicalDocument
from app.db.session import AsyncSessionLocal


logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)
FALLBACK_EMBEDDING = [0.0] * 768


def _read_text_file(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore").strip()


def _read_csv_file(path: Path, max_rows: int = 5000) -> str:
    lines: list[str] = []
    with path.open("r", encoding="utf-8", errors="ignore", newline="") as f:
        reader = csv.DictReader(f)
        headers = reader.fieldnames or []
        if headers:
            lines.append("Columns: " + ", ".join(h.strip() for h in headers if h))

        for idx, row in enumerate(reader, start=1):
            if idx > max_rows:
                lines.append(f"... truncated after {max_rows} rows")
                break
            parts = []
            for key, value in row.items():
                key_str = (key or "").strip()
                value_str = (value or "").strip()
                if key_str and value_str:
                    parts.append(f"{key_str}: {value_str}")
            if parts:
                lines.append("; ".join(parts))

    return "\n".join(lines).strip()


def _read_document(path: Path) -> str:
    ext = path.suffix.lower()
    if ext == ".txt":
        return _read_text_file(path)
    if ext == ".csv":
        return _read_csv_file(path)
    return ""


async def index_documents() -> None:
    docs_path = BASE_DIR / "data" / "raw" / "medical_pdfs"
    if not docs_path.exists():
        print(f"Directory not found: {docs_path}")
        return

    supported_files = sorted(
        [
            p
            for p in docs_path.rglob("*")
            if p.is_file() and p.suffix.lower() in {".txt", ".csv"}
        ]
    )
    if not supported_files:
        print(f"No supported documents (.txt, .csv) found in: {docs_path}")
        return

    inserted = 0
    skipped = 0

    async with AsyncSessionLocal() as db:
        for file_path in supported_files:
            content = _read_document(file_path)
            if not content:
                skipped += 1
                continue

            title = file_path.stem.replace("_", " ").strip() or file_path.name

            existing = await db.execute(
                select(MedicalDocument.id).where(MedicalDocument.title == title)
            )
            if existing.scalar_one_or_none() is not None:
                skipped += 1
                continue

            db.add(
                MedicalDocument(
                    title=title,
                    content=content,
                    embedding=FALLBACK_EMBEDDING,
                    metadata_json={
                        "source": file_path.name,
                        "path": str(file_path.relative_to(BASE_DIR)),
                        "ingested_by": "scripts/index_documents.py",
                    },
                )
            )
            inserted += 1

        await db.commit()

    print("Medical document indexing complete")
    print(f"Inserted: {inserted}")
    print(f"Skipped: {skipped}")
    print(f"Scanned: {len(supported_files)}")


if __name__ == "__main__":
    asyncio.run(index_documents())