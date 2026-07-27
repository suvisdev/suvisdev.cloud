from fastapi import Depends

from silicon_valley.adapter.outbound.extractor.pdf_summary_pdfloader_extractor import (
    PdfLoaderExtractor,
)
from silicon_valley.adapter.outbound.llm.pdf_summary_ollama_summarizer import (
    OllamaExaonePdfSummarizer,
)
from silicon_valley.adapter.outbound.repositories.pdf_summary_repository import (
    PdfSummaryRepository,
)
from silicon_valley.app.ports.input.pdf_summary_use_case import PdfSummaryUseCase
from silicon_valley.app.ports.output.pdf_summary_extractor_port import PdfExtractorPort
from silicon_valley.app.ports.output.pdf_summary_repository_port import PdfSummaryPort
from silicon_valley.app.ports.output.pdf_summary_summarizer_port import PdfSummarizerPort
from silicon_valley.app.use_case.pdf_summary_interactor import PdfSummaryInteractor


def get_pdf_extractor() -> PdfExtractorPort:
    return PdfLoaderExtractor()


def get_pdf_summarizer() -> PdfSummarizerPort:
    return OllamaExaonePdfSummarizer()


def get_pdf_summary_repository() -> PdfSummaryPort:
    return PdfSummaryRepository()


def get_pdf_summary_use_case(
    extractor: PdfExtractorPort = Depends(get_pdf_extractor),
    summarizer: PdfSummarizerPort = Depends(get_pdf_summarizer),
    repository: PdfSummaryPort = Depends(get_pdf_summary_repository),
) -> PdfSummaryUseCase:
    return PdfSummaryInteractor(extractor=extractor, summarizer=summarizer, repository=repository)
