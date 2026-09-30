"""동행(누구와 보는가) → 장르 확장 테스트.

핵심은 오탐 방지다: "아이"·"친구" 같은 짧은 명사가 "아이언맨"·"여자친구"에 부분일치하지 않도록
동반 조사(랑·와·하고)를 요구한다. build_search_filters까지 태워 must.genres에 실리는지도 본다.
"""

from mova.adapter.outbound.llm.intent_extraction import build_search_filters
from mova.domain.value_objects.companion_expansion import expand_companion_genres


def test_partner_maps_to_romance_comedy():
    assert expand_companion_genres("여자친구랑 볼 영화") == ["로맨스", "코미디"]
    assert expand_companion_genres("남친이랑 볼만한거") == ["로맨스", "코미디"]


def test_child_maps_to_animation_adventure():
    assert expand_companion_genres("아이랑 볼 영화") == ["애니메이션", "모험"]
    assert expand_companion_genres("조카랑 볼만한거") == ["애니메이션", "모험"]


def test_date_and_couple_match_without_particle():
    assert expand_companion_genres("데이트 영화 추천") == ["로맨스", "코미디"]
    assert expand_companion_genres("커플이 볼 영화") == ["로맨스", "코미디"]


def test_parents_and_friends_mapping():
    assert expand_companion_genres("부모님이랑 볼 영화") == ["드라마"]
    assert expand_companion_genres("친구들하고 볼만한거") == ["코미디", "액션"]


def test_short_noun_without_particle_does_not_false_match():
    # "아이"가 "아이언맨"·"아이유"에, "친구"가 문맥 없이 걸리면 안 된다.
    assert expand_companion_genres("아이언맨 같은 영화 추천") == []
    assert expand_companion_genres("아이유 나오는 영화") == []
    assert expand_companion_genres("혼자 볼 영화") == []


def test_companion_genres_reach_search_filters():
    _, sf = build_search_filters("여자친구랑 볼 영화 추천해줘", [])
    genres = sf.get("must", {}).get("genres", [])
    assert "로맨스" in genres and "코미디" in genres


def test_no_companion_keeps_existing_genre_guess():
    # 기존 _guess_genres(명시 장르)는 그대로 동작, 동행 확장은 개입하지 않는다.
    _, sf = build_search_filters("스릴러 영화 추천", [])
    genres = sf.get("must", {}).get("genres", [])
    assert genres == ["스릴러"]
