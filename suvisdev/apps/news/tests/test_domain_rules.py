from news.domain.relevance import is_relevant, relevance
from news.domain.url import canonical_url, domain_of_url


def test_relevance_title_and_lead():
    assert relevance("반도체 수출", "반도체 수출 3개월 연속 증가", "") == 1.0
    assert relevance("반도체 수출", "수출 늘었다…반도체 호조", "") == 0.8
    assert relevance("반도체", "증시 마감", "반도체 업종이 2% 올랐다") == 0.6
    assert not is_relevant(relevance("반도체 수출", "증시 마감 시황", "외국인 순매수"))


def test_relevance_ignores_spacing_and_case():
    assert relevance("AI 반도체", "ai반도체 투자 확대", "") == 1.0
    assert relevance("", "아무 제목", "") == 0.0


def test_canonical_url_drops_tracking_params_and_fragment():
    a = canonical_url("https://WWW.Example.com/news/1/?utm_source=naver&id=7#top")
    b = canonical_url("https://www.example.com/news/1?id=7&plink=RSS")
    assert a == b == "https://www.example.com/news/1?id=7"
    assert domain_of_url("https://m.news.example.co.kr/a") == "news.example.co.kr"
