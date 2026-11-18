# 쿠모니지 (4인 타일 게임)

- 규칙의 기준은 `server/kumoniji/cases.json`(손으로 계산한 기대값) + `rules.py`. **규칙을 바꾸면 cases.json부터** 고친다. 기획·결정 기록은 바탕화면 `타일게임_기획/`.
- 판정은 서버가 한다(서버 권위). 앱(Flutter)은 서버가 준 상태만 그린다 — 앱에 규칙을 다시 짜지 않는다.
- 그림은 Codex가 만든다(`app/assets/tiles/`).
- 서버 테스트: `cd kumoniji/server && uv run --no-project --python 3.13 --with pytest --with httpx --with fastapi==0.136.3 pytest -q`
- 앱: `source ~/.cache/gildle-build/env.sh && cd kumoniji/app && flutter analyze && flutter test`
- 배포: `kumoniji/deploy.sh`(노트북 k3s, `kumoniji.suvisdev.cloud`). 판은 메모리에만 있어 replicas 1.
