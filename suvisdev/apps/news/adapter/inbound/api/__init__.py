from fastapi import APIRouter

from news.adapter.inbound.api.v1.news_admin_router import news_admin_router
from news.adapter.inbound.api.v1.news_router import news_router

# 앱 라우터 집약 — main.py(Composition Root)에서 이 news_router_root 만 include 한다 (/api/v1/news/...).
news_router_root = APIRouter(prefix="/news")
news_router_root.include_router(news_router)
news_router_root.include_router(news_admin_router)
