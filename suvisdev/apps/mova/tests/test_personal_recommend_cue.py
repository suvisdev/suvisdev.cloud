"""취향·유사 추천 단서(2026-09-29) — 조건 추천과 갈라야 하는 발화."""

from __future__ import annotations

from mova.app.use_cases.market_chat_interactor import personal_recommend_cue


def test_similar_to_seed_title():
    assert personal_recommend_cue("기생충 같은 영화 추천해줘") == ("similar", "기생충")
    assert personal_recommend_cue("인셉션이랑 비슷한 거 있어?") == ("similar", "인셉션")
    assert personal_recommend_cue("밤의 해변에서 혼자 느낌의 작품") == (
        "similar",
        "밤의 해변에서 혼자",
    )


def test_taste_cues_and_bare_requests():
    assert personal_recommend_cue("내 취향에 맞는 영화 추천해줘") == ("taste", None)
    assert personal_recommend_cue("내가 본 영화 기준으로 골라줘") == ("taste", None)
    assert personal_recommend_cue("추천해줘") == ("taste", None)
    assert personal_recommend_cue("뭐 볼까?") == ("taste", None)


def test_conditional_requests_stay_conditional():
    assert personal_recommend_cue("비 오는 날 어울리는 영화") == (None, None)
    assert personal_recommend_cue("송강호 나오는 영화") == (None, None)
    assert personal_recommend_cue("2000년대 초반 한국 영화 추천해줘") == (None, None)


def test_taste_query_vector_weights_high_ratings():
    from mova.app.use_cases.market_chat_interactor import taste_query_vector

    emb = {1: [1.0, 0.0], 2: [0.0, 1.0], 3: [1.0, 1.0]}
    v = taste_query_vector([(1, 5.0), (2, 3.0), (9, 5.0)], emb)  # 9는 임베딩 없음 → 무시
    assert v is not None and v[0] > v[1]  # 별점 5(가중 2.5) 쪽으로 기운다
    assert taste_query_vector([(9, 5.0)], emb) is None
