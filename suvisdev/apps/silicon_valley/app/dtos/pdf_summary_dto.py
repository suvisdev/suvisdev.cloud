from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PdfSummaryCommand:
    filename: str
    content: bytes


@dataclass(frozen=True)
class PdfExtractedDocument:
    text: str
    source_path: str


@dataclass(frozen=True)
class PdfSummaryRecord:
    filename: str
    extracted_text: str
    summary: str


@dataclass(frozen=True)
class PdfSummaryResponse:
    id: int
    filename: str
    text_excerpt: str
    summary: str
