from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PdfExtractedDocument:
    text: str
    source_path: str


@dataclass(frozen=True)
class PdfLoaderRecord:
    filename: str
    extracted_text: str
    summary: str


@dataclass(frozen=True)
class PdfLoaderResponse:
    id: int
    filename: str
    text_excerpt: str
    summary: str
