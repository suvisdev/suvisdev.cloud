"""어드민 크롤러/스크래퍼 화면 — POST /ontology/harvester/{scrape,crawl}, GET .../sites.

harvester CLI(scripts/harvester_cli.py)와 정확히 같은 use case(ScrapeDatasetInteractor,
CrawlScheduleInteractor)를 재사용한다 — 이 라우터는 (1) 자연어 명령을 keyword/limit으로
해석하고 (2) 동기 use case 호출을 asyncio.to_thread로 감싸는 것만 담당한다.
"""

from __future__ import annotations

import asyncio

from fastapi import APIRouter, HTTPException

from ontology.adapter.inbound.api.schemas.harvester_schema import (
    HarvesterCommandRequestSchema,
    HarvesterRunResponseSchema,
    HarvesterSiteSchema,
)
from ontology.adapter.outbound.scraper.registry import SITE_REGISTRY
from ontology.app.dtos.scrape_dto import ScrapeTarget
from ontology.dependencies.harvester_provider import (
    UnknownSiteError,
    build_crawl_schedule_use_case,
    build_harvester_command_parser,
    build_scrape_dataset_use_case,
    build_site_scraper,
    default_scrape_out_path,
)

harvester_router = APIRouter(prefix="/harvester", tags=["ontology-harvester"])


@harvester_router.get("/sites", response_model=list[HarvesterSiteSchema])
async def sites() -> list[HarvesterSiteSchema]:
    return [
        HarvesterSiteSchema(site_id=site_id, fetcher_kind=cls.fetcher_kind)
        for site_id, cls in sorted(SITE_REGISTRY.items())
    ]


@harvester_router.post("/scrape", response_model=HarvesterRunResponseSchema)
async def scrape(req: HarvesterCommandRequestSchema) -> HarvesterRunResponseSchema:
    """스크래퍼 탭 — 온디맨드 1회 수집 (ScrapeDatasetInteractor, 파일 덮어쓰기)."""
    parser = build_harvester_command_parser()
    command = await parser.parse(req.command_text)

    try:
        scraper = build_site_scraper(req.site_id, rate=1.0, dedup=True)
    except UnknownSiteError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    service = build_scrape_dataset_use_case(scraper)
    out_path = default_scrape_out_path(req.site_id, command.keyword)
    target = ScrapeTarget(site_id=req.site_id, keyword=command.keyword)
    meta = await asyncio.to_thread(service.run, target, limit=command.limit, out_path=out_path)

    return HarvesterRunResponseSchema(
        record_count=meta.record_count,
        path=meta.path,
        parsed_keyword=command.keyword,
        parsed_limit=command.limit,
    )


@harvester_router.post("/crawl", response_model=HarvesterRunResponseSchema)
async def crawl(req: HarvesterCommandRequestSchema) -> HarvesterRunResponseSchema:
    """크롤러 탭 — 즉시 1회 수집 (CrawlScheduleInteractor.run_once, 날짜별 append)."""
    parser = build_harvester_command_parser()
    command = await parser.parse(req.command_text)

    service = build_crawl_schedule_use_case()
    try:
        meta = await asyncio.to_thread(
            service.run_once,
            site_id=req.site_id,
            keywords=(command.keyword,),
            limit=command.limit,
        )
    except UnknownSiteError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    return HarvesterRunResponseSchema(
        record_count=meta.record_count,
        path=meta.path,
        parsed_keyword=command.keyword,
        parsed_limit=command.limit,
    )
