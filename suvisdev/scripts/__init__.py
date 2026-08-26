"""suvisdev 루트 CLI 스크립트 패키지.

이 __init__.py가 없으면 scripts/는 네임스페이스 패키지가 되는데, 정규
패키지인 apps/gildle/scripts가 sys.path에 함께 있으면 최상위 `scripts`
이름을 선점해 mova 테스트의 `from scripts.backfill_*` 임포트가 전체
pytest 실행에서만 깨진다(정규 패키지 > 네임스페이스 패키지 우선순위).
"""
