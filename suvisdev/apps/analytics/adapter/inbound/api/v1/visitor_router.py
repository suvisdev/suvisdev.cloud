from __future__ import annotations

from fastapi import APIRouter, Depends, Response
from shared.security.require_admin import AdminPrincipal, require_admin

from analytics.adapter.inbound.api.schemas.visitor_schema import (
    DailyVisitorCountSchema,
    VisitorSummarySchema,
    VisitPingRequestSchema,
)
from analytics.app.ports.input.get_visitor_summary_use_case import GetVisitorSummaryUseCase
from analytics.app.ports.input.record_visit_use_case import RecordVisitUseCase
from analytics.dependencies.visitor_provider import (
    get_record_visit_use_case,
    get_visitor_summary_use_case,
)

visitor_router = APIRouter(prefix="/visitors", tags=["analytics-visitors"])


@visitor_router.post("/ping", status_code=204)
async def ping(
    req: VisitPingRequestSchema,
    use_case: RecordVisitUseCase = Depends(get_record_visit_use_case),
) -> Response:
    # 무인증: 로그인하지 않은 익명 방문자도 집계 대상이라 인증을 요구할 수 없다.
    # 받는 값은 클라이언트가 만든 UUID 문자열 1개뿐(PII 없음), (visitor_id, visit_date)
    # upsert 1건만 발생해 남용 시 영향 범위가 제한적이다.
    await use_case.record(req.visitor_id)
    return Response(status_code=204)


@visitor_router.get("/summary", response_model=VisitorSummarySchema)
async def summary(
    _: AdminPrincipal = Depends(require_admin),
    use_case: GetVisitorSummaryUseCase = Depends(get_visitor_summary_use_case),
) -> VisitorSummarySchema:
    dto = await use_case.summary()
    return VisitorSummarySchema(
        now_active=dto.now_active,
        today=dto.today,
        last_7_days_total=dto.last_7_days_total,
        cumulative_total=dto.cumulative_total,
        last_7_days_series=[
            DailyVisitorCountSchema(date=d.date, count=d.count) for d in dto.last_7_days_series
        ],
    )
