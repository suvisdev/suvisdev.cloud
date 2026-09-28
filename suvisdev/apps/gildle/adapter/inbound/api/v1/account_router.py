"""회원 탈퇴 시 gildle 데이터 삭제(2026-09-28, Google Play 계정 삭제 정책).

앱은 이 엔드포인트로 산책 기록·기기 토큰을 지운 뒤, 인증 게이트웨이
`DELETE /auth/mobile/account`로 계정 자체를 지운다."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from shared.security.require_user import UserPrincipal, require_user

from gildle.app.ports.input.account_data_use_case import AccountDataUseCase
from gildle.dependencies.account_data_provider import get_account_data_use_case

account_router = APIRouter(prefix="/me", tags=["gildle-account"])


@account_router.delete("/data")
async def erase_my_data(
    principal: UserPrincipal = Depends(require_user),
    use_case: AccountDataUseCase = Depends(get_account_data_use_case),
) -> dict[str, int]:
    return await use_case.erase(principal.user_id)
