# 프로젝트 메모리 인덱스

이 저장소에서 작업하며 얻은, **코드·문서만 봐서는 알기 어려운** 정보를 주제별로
모아 둔다. 커밋되므로 팀·다른 에이전트가 함께 본다.

> **이 디렉터리(저장소 안)는 Claude Code가 자동으로 읽지 않는다.** 반영하려면
> 읽으라고 지시해야 한다.
>
> 자동 로드되는 개인 메모리는 **홈**의 `~/.claude/projects/-home-a-projects-suvis/memory/`에
> 따로 있다. 두 경로는 `~/`(홈) 여부만 다르고 나머지가 같으니 헷갈리지 말 것 —
> 커밋되는 건 이쪽(저장소), 세션마다 자동 로드되는 건 홈이다. 같은 내용을 양쪽에
> 두지 않는다.

| 파일 | 내용 |
|------|------|
| [debugging.md](debugging.md) | 삽질했던 문제의 원인과 진단 방법 (CLIP hang, lint-imports, DB 미기동) |
| [patterns.md](patterns.md) | 코드 패턴 — 백엔드 계층 구조, 프론트 규칙 문서 위치 |

## 관련 문서

| 문서 | 위치 |
|------|------|
| 루트 지침 (Karpathy 원칙 · 명령어 · 환경변수 · 브랜치) | `CLAUDE.md` |
| 작업 일지 (날짜별 상세) | `_docs/WORK_LOG.md` |
| 어드민·멀티에이전트 진행 상황 · 백로그 | `_docs/SUVIS_ADMIN_MULTIAGENT_PROGRESS.md` |
| 경로별 코딩 규칙 | `.claude/rules/` |
| 프론트엔드 상세 규칙 | `suvis/CLAUDE.md` · `suvis/_docs/react-rules.md` |
