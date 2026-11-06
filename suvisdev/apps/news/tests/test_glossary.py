"""용어 사전 — 찾는 규칙(오탐 방지)과 사전 파일 자체 검사, 읽기 API 에 붙는지."""

import json
from pathlib import Path

import pytest
from news_fakes import FakeRepo

import news.domain.glossary as g
from news.app.dtos.news_dtos import ArticleDto
from news.app.use_cases.news_read_interactor import NewsReadInteractor
from news.domain.glossary import MAX_TERMS_PER_ARTICLE, find_terms
from news.domain.sections import SECTIONS


def _names(text: str, section: str = "ai") -> list[str]:
    return [t.term.split(" (")[0] for t in find_terms(text, section)]


def test_finds_terms_in_order_of_appearance_english_and_korean():
    assert _names("강화학습 기반 역기구학 정책을 PPO 로 학습") == ["강화학습", "역기구학", "PPO"]
    assert _names("We train a policy with reinforcement learning") == ["강화학습"]
    assert _names("모델 양자화를 적용했다") == ["양자화"]  # 조사가 붙어도 잡는다


def test_acronyms_are_case_sensitive_and_need_word_boundary():
    assert _names("RAG 를 썼다") == ["RAG"]
    assert _names("a rag on the floor, storage and drag") == []  # 소문자·단어 일부는 아님
    assert _names("We use MoE routing") == ["MoE"]
    assert _names("I moe the lawn") == []
    assert _names("the reagents were mixed") == []  # agent 가 단어 일부
    assert _names("AI agents plan tasks") == ["AI 에이전트"]


def test_common_english_meanings_are_not_matched():
    assert _names("The launch drew a lot of attention from investors") == []
    assert _names("rigid-body alignment of protein structures") == []
    assert _names("We add multi-head attention") == ["어텐션"]
    assert _names("Training can induce misalignment") == ["AI 정렬"]


def test_section_filter_and_shared_terms():
    assert _names("코스피가 올랐다", "ai") == []
    assert _names("코스피가 올랐다", "economy") == ["코스피"]
    assert _names("LLM 시장", "economy") == []
    assert _names("HBM 수요 증가", "economy") == ["HBM"]  # 양쪽 섹션 공통
    assert _names("HBM 수요 증가", "ai") == ["HBM"]


def test_longer_term_comes_first_at_same_position_and_limit():
    assert _names("희소 어텐션 구조")[0] == "희소 어텐션"
    many = "LLM RAG MoE PPO 강화학습 양자화 임베딩"
    assert len(find_terms(many, "ai")) == MAX_TERMS_PER_ARTICLE


def test_blue_wave_means_election_not_stock_rally():
    (term,) = find_terms("美 블루웨이브 파급 효과", "economy")
    assert "민주당" in term.desc  # 11-06 EXAONE 은 주식 강세장으로 지어냈다


def test_inverse_kinematics_is_not_forward_kinematics():
    (term,) = find_terms("로봇 팔 역기구학", "ai")
    assert "관절" in term.desc and term.desc.index("목표 위치") < term.desc.index("관절")


def test_glossary_file_is_well_formed():
    raw = json.loads(Path(g.__file__).with_name("glossary.json").read_text(encoding="utf-8"))
    assert len(raw) >= 90
    assert len({r["term"] for r in raw}) == len(raw)  # 같은 용어 두 번 없음
    for r in raw:
        assert r["section"] in (*SECTIONS, "both"), r["term"]
        assert r["match"] and all(isinstance(m, str) and m for m in r["match"]), r["term"]
        assert 8 <= len(r["desc"]) <= 120, r["term"]
        for word in ("가짜", "허위"):
            assert word not in r["desc"]


@pytest.mark.asyncio
async def test_read_api_attaches_terms_using_korean_title_and_summary():
    class Repo(FakeRepo):
        async def list_latest(self, *, section, group, limit, before):
            return [
                ArticleDto(
                    id=1,
                    title="PolicyIK",
                    url="https://x.example/1",
                    summary="short",
                    source_domain="x.example",
                    source_name=None,
                    published_at=None,
                    badge="none",
                    reasons_ko=[],
                    section="ai",
                    group="paper",
                    title_ko="역기구학 정책",
                    summary_ko="강화학습으로 학습했다.",
                )
            ]

    (row,) = await NewsReadInteractor(Repo()).list_latest(
        section="ai", group=None, limit=5, before=None
    )
    assert [t.term.split(" (")[0] for t in row.terms] == ["역기구학", "강화학습"]
