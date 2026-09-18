"""Text extraction and deterministic, section-aware chunks."""

from __future__ import annotations

import hashlib
import re
import uuid
from dataclasses import dataclass
from pathlib import Path

from pypdf import PdfReader

SUPPORTED = {".md", ".txt", ".pdf"}
POLICY_LABEL = "SYNTHETIC DEMONSTRATION POLICY\nNOT AN ACTUAL ORGANIZATION POLICY"


@dataclass(frozen=True)
class Section:
    title: str
    text: str
    page: int | None = None


@dataclass(frozen=True)
class Document:
    name: str
    source: str
    kind: str
    content_hash: str
    sections: tuple[Section, ...]

    @property
    def document_id(self) -> str:
        return str(uuid.uuid5(uuid.NAMESPACE_URL, self.source))


@dataclass(frozen=True)
class Chunk:
    chunk_id: str
    text: str
    payload: dict


def normalize(text: str) -> str:
    return re.sub(r"[ \t]+", " ", text.replace("\r\n", "\n").replace("\r", "\n")).strip()


def load_document(path: Path, root: Path) -> Document:
    kind = path.suffix.lower()
    if kind not in SUPPORTED:
        raise ValueError(f"Unsupported document type: {kind or '<none>'}")
    try:
        raw = path.read_bytes()
        if not raw:
            raise ValueError("Empty document")
        if kind == ".pdf":
            reader = PdfReader(path, strict=True)
            sections = tuple(
                Section(f"Page {number}", normalize(page.extract_text() or ""), number)
                for number, page in enumerate(reader.pages, 1)
                if normalize(page.extract_text() or "")
            )
        else:
            body = normalize(raw.decode("utf-8"))
            if kind == ".md":
                sections_list: list[Section] = []
                heading = "Introduction"
                lines: list[str] = []
                for line in body.splitlines():
                    if re.match(r"^#{1,6} +", line):
                        if normalize("\n".join(lines)):
                            sections_list.append(Section(heading, normalize("\n".join(lines))))
                        heading = line.lstrip("# ").strip()
                        lines = []
                    else:
                        lines.append(line)
                if normalize("\n".join(lines)):
                    sections_list.append(Section(heading, normalize("\n".join(lines))))
                sections = tuple(
                    section for section in sections_list if section.text != POLICY_LABEL
                )
            else:
                sections = (Section("Document", body),) if body else ()
    except (OSError, UnicodeError) as exc:
        raise ValueError(f"Cannot read {path.name}: {exc}") from exc
    except Exception as exc:
        if kind == ".pdf" and not isinstance(exc, ValueError):
            raise ValueError(f"Malformed PDF {path.name}: {exc}") from exc
        raise
    if not sections:
        raise ValueError(f"No extractable text: {path.name}")
    source = f"{root.name}/{path.resolve().relative_to(root.resolve()).as_posix()}"
    title = path.stem.replace("_", " ").title()
    if kind == ".md":
        title_match = re.search(r"^# +(.+)$", body, re.MULTILINE)
        if title_match:
            title = title_match.group(1).strip()
    return Document(
        title,
        source,
        kind[1:],
        hashlib.sha256(raw).hexdigest(),
        sections,
    )


def _pieces(text: str, target: int, overlap: int):
    """Keep short sections intact; split long sections at paragraph/sentence/word boundaries."""
    if len(text) <= target:
        yield text
        return
    start = 0
    while start < len(text):
        end = min(start + target, len(text))
        if end < len(text):
            boundary = max(
                text.rfind("\n", start + target // 2, end),
                text.rfind(". ", start + target // 2, end),
                text.rfind(" ", start + target // 2, end),
            )
            if boundary > start:
                end = boundary + (2 if text[boundary : boundary + 2] == ". " else 1)
        yield text[start:end].strip()
        if end == len(text):
            break
        start = max(start + 1, end - overlap)


def chunk_document(
    document: Document,
    target: int = 650,
    overlap: int = 80,
    model: str = "intfloat/multilingual-e5-small",
) -> list[Chunk]:
    if overlap >= target // 2:
        raise ValueError("Overlap must be below half the target chunk size")
    chunks = []
    for section in document.sections:
        for index, piece in enumerate(_pieces(section.text, target, overlap)):
            text = f"{document.name} — {section.title}\n{piece}"
            key = (
                f"{document.document_id}:{document.content_hash}:{section.title}:"
                f"{section.page}:{index}:{target}:{overlap}:{model}"
            )
            chunk_id = str(uuid.uuid5(uuid.NAMESPACE_URL, key))
            chunks.append(
                Chunk(
                    chunk_id,
                    text,
                    {
                        "chunk_id": chunk_id,
                        "document_id": document.document_id,
                        "document_name": document.name,
                        "document_type": document.kind,
                        "source": document.source,
                        "page": section.page,
                        "section": section.title,
                        "content_hash": document.content_hash,
                        "embedding_model": model,
                        "target_chars": target,
                        "overlap_chars": overlap,
                        "text": text,
                    },
                )
            )
    return chunks
