from fastapi import Depends

from silicon_valley.adapter.outbound.extractor.pdf_loader_extractor import PdfLoaderExtractor
from silicon_valley.adapter.outbound.llm.pdf_loader_ollama_summarizer import (
    OllamaExaonePdfSummarizer,
)
from silicon_valley.adapter.outbound.repositories.pdf_loader_repository import (
    PdfLoaderRepository,
)
from silicon_valley.app.ports.input.pdf_loader_use_case import PdfLoaderUseCase
from silicon_valley.app.ports.output.pdf_loader_extractor_port import PdfExtractorPort
from silicon_valley.app.ports.output.pdf_loader_repository_port import PdfLoaderPort
from silicon_valley.app.ports.output.pdf_loader_summarizer_port import PdfSummarizerPort
from silicon_valley.app.use_case.pdf_loader_interactor import PdfLoaderInteractor


def get_pdf_extractor() -> PdfExtractorPort:
    return PdfLoaderExtractor()


def get_pdf_summarizer() -> PdfSummarizerPort:
    return OllamaExaonePdfSummarizer()


def get_pdf_loader_repository() -> PdfLoaderPort:
    return PdfLoaderRepository()


def get_pdf_loader_use_case(
    extractor: PdfExtractorPort = Depends(get_pdf_extractor),
    summarizer: PdfSummarizerPort = Depends(get_pdf_summarizer),
    repository: PdfLoaderPort = Depends(get_pdf_loader_repository),
) -> PdfLoaderUseCase:
    return PdfLoaderInteractor(extractor=extractor, summarizer=summarizer, repository=repository)
