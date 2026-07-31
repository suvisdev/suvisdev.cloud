"""어드민 크롤러/스크래퍼 화면 — POST /ontology/harvester/{scrape,crawl}, GET .../sites.

두 모드를 지원한다:
- 등록된 사이트 모드(site_id): harvester CLI와 같은 use case(ScrapeDatasetInteractor,
  CrawlScheduleInteractor)를 재사용. 자연어 명령을 keyword/limit으로 해석한다.
- 임의 URL 모드(url): CustomUrlScrapeInteractor. robots.txt 확인 후 그 페이지 1개만
  가져와 자연어 지시(command_text 전체) 그대로 LLM에 넘겨 원하는 내용만 추출한다.
  keyword/limit 해석은 여기선 의미가 없어서 건너뛴다.

동기 use case 호출은 asyncio.to_thread로 감싼다(CustomUrlScrapeInteractor는 내부에서
직접 감쌈 — LLM 호출이 섞여 있어 인터랙터 자체가 async라서).
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException

from ontology.adapter.inbound.api.schemas.harvester_schema import (
    HarvesterCommandRequestSchema,
    HarvesterPolicySchema,
    HarvesterRunResponseSchema,
    HarvesterSiteSchema,
)
from ontology.adapter.outbound.config.api_keys import MissingApiKeyError
from ontology.adapter.outbound.scraper.registry import SITE_REGISTRY
from ontology.app.dtos.scrape_dto import ScrapeTarget
from ontology.app.ports.output.crawl_errors import CrawlFetchError
from ontology.app.ports.output.hub_rag_errors import HubRagError
from ontology.dependencies.harvester_provider import (
    UnknownSiteError,
    build_crawl_policy_port,
    build_crawl_schedule_state_port,
    build_crawl_schedule_use_case,
    build_custom_url_scrape_use_case,
    build_harvester_command_parser,
    build_scrape_dataset_use_case,
    build_site_scraper,
    custom_url_crawl_out_path,
    custom_url_scrape_out_path,
    default_scrape_out_path,
)
from shared.security.require_admin import AdminPrincipal, require_admin

harvester_router = APIRouter(prefix="/harvester", tags=["ontology-harvester"])


@harvester_router.get("/sites", response_model=list[HarvesterSiteSchema])
async def sites(_: AdminPrincipal = Depends(require_admin)) -> list[HarvesterSiteSchema]:
    return [
        HarvesterSiteSchema(site_id=site_id, fetcher_kind=cls.fetcher_kind)
        for site_id, cls in sorted(SITE_REGISTRY.items())
    ]


@harvester_router.get("/policies", response_model=list[HarvesterPolicySchema])
async def policies(_: AdminPrincipal = Depends(require_admin)) -> list[HarvesterPolicySchema]:
    """크롤링 탭 — crawl_config.yaml 재수집 정책 + site별 마지막 실행 시각 현황판.

    주의: Redis에 남는 마지막 실행 시각은 site_id 단위다. crawl_config.yaml에서 같은
    site(예: google_news)에 정책이 여러 개면 last_run_at이 그 site의 마지막 실행
    시각 하나로 전부 동일하게 나온다 — 정책별이 아니라 사이트별 값이다.
    """
    policy_port = build_crawl_policy_port()
    state_port = build_crawl_schedule_state_port()
    now = datetime.now(UTC)

    out: list[HarvesterPolicySchema] = []
    for p in policy_port.get_policies():
        last_run = state_port.get_last_run(p.site_id)
        is_due = last_run is None or (now - last_run) >= timedelta(minutes=p.interval_minutes)
        out.append(
            HarvesterPolicySchema(
                site_id=p.site_id,
                keywords=list(p.keywords),
                keyword_source=p.keyword_source,
                interval_minutes=p.interval_minutes,
                limit_per_keyword=p.limit_per_keyword,
                last_run_at=last_run.isoformat() if last_run else None,
                is_due=is_due,
            )
        )
    return out


async def _run_custom_url(url: str, instruction: str, *, append: bool) -> HarvesterRunResponseSchema:
    out_path = custom_url_crawl_out_path() if append else custom_url_scrape_out_path(url)
    service = build_custom_url_scrape_use_case()
    try:
        meta = await service.run(url=url, instruction=instruction, out_path=out_path, append=append)
    except (CrawlFetchError, HubRagError) as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail) from e

    return HarvesterRunResponseSchema(
        record_count=meta.record_count,
        path=meta.path,
        parsed_keyword=instruction[:80],
        parsed_limit=1,
    )


@harvester_router.post("/scrape", response_model=HarvesterRunResponseSchema)
async def scrape(
    req: HarvesterCommandRequestSchema,
    _: AdminPrincipal = Depends(require_admin),
) -> HarvesterRunResponseSchema:
    """스크래퍼 탭 — 온디맨드 1회 수집 (파일 덮어쓰기)."""
    if req.url:
        return await _run_custom_url(req.url, req.command_text, append=False)
    if not req.site_id:
        raise HTTPException(status_code=400, detail="site_id 또는 url 중 하나는 있어야 합니다.")

    parser = build_harvester_command_parser()
    command = await parser.parse(req.command_text)

    try:
        scraper = build_site_scraper(req.site_id, rate=1.0, dedup=True)
    except UnknownSiteError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    service = build_scrape_dataset_use_case(scraper)
    out_path = default_scrape_out_path(req.site_id, command.keyword)
    target = ScrapeTarget(site_id=req.site_id, keyword=command.keyword)
    try:
        meta = await asyncio.to_thread(service.run, target, limit=command.limit, out_path=out_path)
    except MissingApiKeyError as e:
        raise HTTPException(status_code=503, detail=str(e)) from e

    return HarvesterRunResponseSchema(
        record_count=meta.record_count,
        path=meta.path,
        parsed_keyword=command.keyword,
        parsed_limit=command.limit,
    )


@harvester_router.post("/crawl", response_model=HarvesterRunResponseSchema)
async def crawl(
    req: HarvesterCommandRequestSchema,
    _: AdminPrincipal = Depends(require_admin),
) -> HarvesterRunResponseSchema:
    """크롤러 탭 — 즉시 1회 수집 (날짜별 append)."""
    if req.url:
        return await _run_custom_url(req.url, req.command_text, append=True)
    if not req.site_id:
        raise HTTPException(status_code=400, detail="site_id 또는 url 중 하나는 있어야 합니다.")

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
    except MissingApiKeyError as e:
        raise HTTPException(status_code=503, detail=str(e)) from e

    return HarvesterRunResponseSchema(
        record_count=meta.record_count,
        path=meta.path,
        parsed_keyword=command.keyword,
        parsed_limit=command.limit,
    )
