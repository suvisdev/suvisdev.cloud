from fastapi import Depends

from execsuite.adapter.outbound.extractor.pdf_loader_extractor import PdfLoaderExtractor
from execsuite.adapter.outbound.llm.pdf_loader_ollama_summarizer import (
    OllamaExaonePdfSummarizer,
)
from execsuite.adapter.outbound.repositories.pdf_loader_repository import (
    PdfLoaderRepository,
)
from execsuite.app.ports.input.pdf_loader_use_case import PdfLoaderUseCase
from execsuite.app.ports.output.pdf_loader_extractor_port import PdfExtractorPort
from execsuite.app.ports.output.pdf_loader_repository_port import PdfLoaderPort
from execsuite.app.ports.output.pdf_loader_summarizer_port import PdfSummarizerPort
from execsuite.app.use_case.pdf_loader_interactor import PdfLoaderInteractor


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
