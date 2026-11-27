"""/api/wallet — 잔고·출석·상점. POST의 Origin·CSRF 검사는 player()가 한다."""

import time
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from ..accounts import db
from ..accounts.web import is_app, player
from . import money, store

router = APIRouter(prefix="/api/wallet")


class Buy(BaseModel):
    item: Literal[tuple(money.SHOP)]  # type: ignore[valid-type]  # 상품 목록은 money.SHOP 하나에서
    rid: str | None = Field(None, min_length=8, max_length=64, pattern=r"^[A-Za-z0-9_-]+$")  # 요청 id — 응답이 유실돼 다시 보내도 한 번만 산다


@router.get("")
def wallet(request: Request, me: dict = Depends(player)):
    """잔고. 앱이면 그날 첫 조회에 출석도 한다 — 접속만 해도 출석(11-27 사용자). 로그인한 계정만 여기 온다(player).
    웹(쿠키)은 하지 않는다 — GET은 CSRF 검사를 건너뛰어, 남의 사이트가 잔고 주소로 이동시키기만 해도 출석·보상이
    생긴다(리뷰 1차). 앱 머리글은 다른 사이트의 이동·요청이 붙일 수 없다. 웹은 시험 화면이라 출석 버튼(POST)을 쓴다"""
    with db.tx() as c:
        now = time.time()
        if not is_app(request):
            return store.snapshot(c, me["account_id"], now)
        try:
            return store.attend(c, me["account_id"], now) | {"attended_now": True}
        except LookupError:  # 오늘 이미 함
            return store.snapshot(c, me["account_id"], now)


@router.post("/attend")
def attend(me: dict = Depends(player)):
    try:
        with db.tx() as c:
            return store.attend(c, me["account_id"], time.time())
    except LookupError:
        raise HTTPException(409, {"code": "attended"}) from None


@router.post("/buy")
def buy(body: Buy, me: dict = Depends(player)):
    try:
        with db.tx() as c:
            return store.buy(c, me["account_id"], body.item, time.time(), body.rid)
    except LookupError:
        raise HTTPException(409, {"code": "gems"}) from None
