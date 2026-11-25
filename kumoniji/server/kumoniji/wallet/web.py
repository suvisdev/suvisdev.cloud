"""/api/wallet — 잔고·출석·상점. POST의 Origin·CSRF 검사는 player()가 한다."""

import time
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from ..accounts import db
from ..accounts.web import player
from . import store

router = APIRouter(prefix="/api/wallet")


class Buy(BaseModel):
    item: Literal["hearts5", "coins1000"]
    rid: str | None = Field(None, min_length=8, max_length=64, pattern=r"^[A-Za-z0-9_-]+$")  # 요청 id — 응답이 유실돼 다시 보내도 한 번만 산다


@router.get("")
def wallet(me: dict = Depends(player)):
    with db.tx() as c:
        return store.snapshot(c, me["account_id"], time.time())


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
