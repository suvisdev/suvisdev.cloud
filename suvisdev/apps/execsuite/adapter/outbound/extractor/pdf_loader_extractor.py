"""neo4j-graphrag PdfLoader 기반 PdfExtractorPort 구현체.

PdfLoader.run()은 filepath(str|Path)만 받고 bytes를 직접 못 받으므로,
업로드된 바이트를 임시 파일로 내려서 넘긴다.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

from neo4j_graphrag.experimental.components.data_loader import PdfLoader

from execsuite.app.dtos.pdf_loader_dto import PdfExtractedDocument
from execsuite.app.ports.output.pdf_loader_extractor_port import PdfExtractorPort


class PdfLoaderExtractor(PdfExtractorPort):
    def __init__(self) -> None:
        self._loader = PdfLoader()

    async def extract_text(self, filename: str, content: bytes) -> PdfExtractedDocument:
        with tempfile.NamedTemporaryFile(suffix=".pdf") as tmp:
            tmp.write(content)
            tmp.flush()
            document = await self._loader.run(filepath=Path(tmp.name))

        return PdfExtractedDocument(
            text=document.text,
            source_path=filename,
        )
