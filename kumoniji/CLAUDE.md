# 쿠모니지 (4인 타일 게임)

- 규칙의 기준은 `server/kumoniji/cases.json`(손으로 계산한 기대값) + `rules.py`. **규칙을 바꾸면 cases.json부터** 고친다. 기획·결정 기록은 바탕화면 `타일게임_기획/`.
- 판정은 서버가 한다(서버 권위). 앱(Flutter)은 서버가 준 상태만 그린다 — 앱에 규칙을 다시 짜지 않는다.
- 그림은 Codex가 만든다(`app/assets/tiles/`).
- **시안·그림·화면 캡처는 모두 앱 기준으로 만든다**(11-27 사용자). 출시는 앱만이라(ADR-0025) 폰 가로가 기준이다. 확인할 때는 `test/landscape_test.dart`의 크기(844×390 등)로 캡처하고, Codex 그림 요청에도 폰 가로 화면에 들어갈 크기와 비율을 적는다. 웹이나 PC 화면을 기준으로 만들거나 그 화면만 보고 끝내지 않는다.
- 서버 테스트: `cd kumoniji/server && uv run --no-project --python 3.13 --with pytest --with httpx --with fastapi==0.136.3 pytest -q`
- 봇 난이도(easy·normal·hard, `server/kumoniji/bots.py`)를 바꾸면 하네스로 잰다: `cd kumoniji/server && uv run --no-project --python 3.13 python -m kumoniji.bench` (기준은 바탕화면 PRODUCT.md §3, 1,000판). 봇은 `Seen`(공개 정보 + 자기 손패)만 받는다.
- 앱: `source ~/.cache/gildle-build/env.sh && cd kumoniji/app && flutter analyze && flutter test`
- 화폐(판돈·하트·보석·출석·미션) 숫자는 `server/kumoniji/wallet/money.py` 한 곳(ADR-0024). 판돈은 자동 매칭만, 증감은 모두 원장 `ledger`.
- 배포: main 머지 → kumoniji-ci 통과 → `kumoniji-deploy` 워크플로가 노트북 러너에서 `kumoniji/deploy.sh` 자동 실행(2026-11-28 사용자 결정, 노트북 k3s, `kumoniji.suvisdev.cloud`). 마이그레이션 PR은 머지 전 사용자 확인. 판은 메모리에만 있어 replicas 1.
