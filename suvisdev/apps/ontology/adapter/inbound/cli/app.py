"""스크래퍼 CLI — scripts/harvester_cli.py {scrape|interactive|sites|crawl-batch|generate-reviews}.

진행 상황은 완료 시 건수·경로·소요시간으로 요약한다. search()가 제너레이터라 정확한
"[23/50]" 실시간 카운터를 보여주려면 백그라운드 스레드로 폴링해야 하는데, 그러면
Ctrl+C가 메인 스레드에만 꽂혀 작업 스레드를 못 끊는 문제가 생긴다 — 안전한 중단(수집분
보존)이 실시간 진행률 표시보다 우선이라 단일 스레드로 유지하고 spinner만 보여준다.
"""

from __future__ import annotations

import asyncio
import time
from pathlib import Path

import typer
from rich.console import Console

from ontology.adapter.outbound.scraper.registry import SITE_REGISTRY
from ontology.app.dtos.scrape_dto import ScrapeTarget
from ontology.dependencies.harvester_provider import (
    build_crawl_schedule_use_case,
    build_scrape_dataset_use_case,
    build_site_scraper,
    default_scrape_out_path,
)

app = typer.Typer(help="사이트+키워드로 데이터셋을 수집하는 스크래퍼 CLI")
console = Console()


def _run_scrape(site_id: str, keyword: str, limit: int, out: Path | None, rate: float) -> None:
    if site_id not in SITE_REGISTRY:
        console.print(f"[red]등록되지 않은 사이트: {site_id}[/red]")
        console.print(f"등록된 사이트: {', '.join(sorted(SITE_REGISTRY)) or '(없음)'}")
        raise typer.Exit(code=2)

    target = ScrapeTarget(site_id=site_id, keyword=keyword)
    out_path = out or default_scrape_out_path(site_id, keyword)

    scraper = build_site_scraper(site_id, rate=rate, dedup=True)
    service = build_scrape_dataset_use_case(scraper)

    started = time.monotonic()
    try:
        with console.status(f"수집 중 (site={site_id}, keyword={keyword})..."):
            meta = service.run(target, limit=limit, out_path=out_path)
    except KeyboardInterrupt:
        console.print(
            f"\n[yellow]중단됨 — 지금까지 수집된 데이터는 {out_path}에 남아있습니다.[/yellow]"
        )
        raise typer.Exit(code=130) from None

    elapsed = time.monotonic() - started
    console.print(
        f"[green]✔ 수집 완료[/green]: {meta.record_count}건 → {meta.path} ({elapsed:.1f}s)"
    )


@app.command()
def scrape(
    site: str = typer.Option(..., "--site", "-s", help="SITE_REGISTRY에 등록된 사이트 ID"),
    keyword: str = typer.Option(..., "--keyword", "-k", help="검색 키워드"),
    limit: int = typer.Option(50, "--limit", "-l", help="최대 수집 건수"),
    out: Path | None = typer.Option(None, "--out", "-o", help="출력 JSONL 경로"),
    rate: float = typer.Option(1.0, "--rate", help="요청 간 최소 간격(초)"),
) -> None:
    """사이트 하나에서 키워드로 검색해 JSONL 데이터셋을 만든다."""
    _run_scrape(site, keyword, limit, out, rate)


@app.command()
def interactive() -> None:
    """대화형으로 site/keyword/limit을 입력받아 수집한다."""
    console.print(f"등록된 사이트: {', '.join(sorted(SITE_REGISTRY)) or '(없음)'}")
    site = typer.prompt("site")
    keyword = typer.prompt("keyword")
    limit = typer.prompt("limit", default=50, type=int)
    try:
        _run_scrape(site, keyword, limit, None, 1.0)
    except KeyboardInterrupt:
        console.print("\n[yellow]중단됨.[/yellow]")
        raise typer.Exit(code=130) from None


@app.command(name="crawl-batch")
def crawl_batch() -> None:
    """crawl_config.yaml에 등록된 사이트 중 재수집 주기(interval_minutes)가 된 것만
    증분 수집한다. cron/systemd timer로 주기 호출하는 배치 진입점 — due 여부는 레디스에
    저장된 사이트별 마지막 실행 시각으로 매번 새로 판단하므로 이 커맨드 자체는 상태가 없다.
    """
    service = build_crawl_schedule_use_case()
    results = service.run_due_batches()
    if not results:
        console.print("이번 주기에 실행할 정책이 없습니다 (등록된 정책이 없거나 전부 interval 전).")
        return
    for meta in results:
        console.print(f"[green]✔[/green] {meta.record_count}건 → {meta.path}")


@app.command(name="generate-reviews")
def generate_reviews(
    data_dir: Path = typer.Option(
        Path("apps") / "ontology" / "resources" / "crawled",
        "--data-dir",
        "-d",
        help="수집된 JSONL 파일 디렉터리",
    ),
) -> None:
    """수집된 JSONL 데이터를 기반으로 AI 리뷰를 생성해 reviews 테이블에 저장한다."""
    from ontology.dependencies.harvester_provider import build_ai_review_generator

    generator = build_ai_review_generator()

    started = time.monotonic()
    try:
        with console.status("AI 리뷰 생성 중..."):
            report = asyncio.run(generator.generate_from_directory(data_dir))
    except KeyboardInterrupt:
        console.print("\n[yellow]중단됨.[/yellow]")
        raise typer.Exit(code=130) from None

    elapsed = time.monotonic() - started
    console.print(f"\n[bold]AI 리뷰 생성 리포트[/bold] ({elapsed:.1f}s)")
    console.print(f"  수집 원재료: {report.total_materials}건")
    console.print(f"  DB 매칭:    {report.matched_movies}건")
    console.print(f"  생성 완료:  {report.generated_reviews}건")
    console.print(f"  기존 스킵:  {report.skipped_existing}건")
    console.print(f"  실패:       {report.failed}건")

    for r in report.results:
        console.print(
            f"  [green]✔[/green] {r.movie_title} → ★{r.rating:.1f} (review_id={r.review_id})"
        )
    for err in report.errors:
        console.print(f"  [red]✘[/red] {err}")


@app.command()
def sites() -> None:
    """등록된 사이트 목록과 fetcher 타입을 보여준다."""
    if not SITE_REGISTRY:
        console.print("등록된 사이트가 없습니다.")
        return
    for site_id, scraper_cls in sorted(SITE_REGISTRY.items()):
        console.print(f"{site_id}\t{scraper_cls.fetcher_kind}")


if __name__ == "__main__":
    app()
