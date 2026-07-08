# cloud.suvisdev

이 저장소는 애플리케이션·문서 등 작업물과 함께, **코딩 에이전트용 하네스 엔지니어링**을 [Andrej Karpathy의 관찰](https://x.com/karpathy/status/2015883857489522876)에 맞춰 정리해 둔 프로젝트이다. “똑똑해져라”가 아니라 **반복 적용되는 짧은 규칙**으로 묵시적 가정·과도한 복잡도·직교 수정·모호한 목표를 줄이는 것이 목적이다.

## 하네스가 무엇을 겨냥하는가

Karpathy가 지적한 패턴을 네 가지 원칙으로 맞춘다.

| 원칙 | 한 줄 |
|------|--------|
| 구현 전 사고 | 가정을 말로 밝히고, 모호하면 멈추고 질문한다. |
| 단순성 우선 | 요청 밖 기능·비대 추상·불필요한 예외 처리를 넣지 않는다. |
| 정밀한 수정 | 요청과 직결된 줄만 바꾸고, 지나가며 “개선”하지 않는다. |
| 목표 중심 실행 | “작동하게”보다 테스트·재현 등 **검증 가능한 성공 기준**으로 일을 맡긴다. |

에이전트에게 **명령만 나열**하기보다 **성공 기준 + 검증 방법**을 주면, 기준을 만족할 때까지 루프하기 쉽다는 점이 Karpathy식 하네스의 핵심 통찰이다. 전체 문장·인용·표는 `_docs/CLAUDE.MD`에 있다.

## 문서와 규칙 파일

| 경로 | 역할 |
|------|------|
| `_docs/CLAUDE.MD` | 백엔드 인수인계 SSOT (`CLAUDE.md`는 심볼릭 링크). |
| [`.cursorrules`](../.cursorrules) | Cursor에 걸리는 **하네스**(PKS · SOLID · 아키텍처 + 한국어 요약). |
| [`.cursorignore`](../.cursorignore) | 인덱스·검색 제외 경로 (삭제된 파일·외부 agora 등). |

원칙을 바꿀 때는 **`_docs/CLAUDE.MD`와 `.cursorrules`를 한 세트로** 맞춘다. Cursor는 `CLAUDE.md`를 자동으로 읽지 않으므로, 상세는 `@suvisdev/_docs/CLAUDE.MD`로 명시 참조하거나 `.cursor/rules/*.mdc`에 `alwaysApply: true`로 끌어온다.

## 빠른 시작 (Cursor)

1. 이 폴더를 Cursor로 연다.  
2. 에이전트와 작업할 때는 가능한 한 **검증 가능한 목표**로 요청한다.  
3. 규칙을 손보려면 `_docs/CLAUDE.MD`를 고치고, Cursor용 요약은 [`.cursorrules`](../.cursorrules)에 맞춘다.

## 저장소 안의 다른 디렉터리 (요지)

- `agora/` — 관련 애플리케이션·패키지가 하위에 있다.  
- `_docs/` — 백엔드 코딩 규칙·entity-rules (SSOT).
- `apps/<app>/_docs/` — 앱별 ERD·도메인 위키.

앱별 빌드·실행 방법은 각 하위 프로젝트의 README나 설정을 따른다.

## 참고

- Karpathy 원 트윗: [https://x.com/karpathy/status/2015883857489522876](https://x.com/karpathy/status/2015883857489522876)  
- 비슷한 “한 파일 지침” 패턴을 정리한 커뮤니티 예시: [forrestchang/andrej-karpathy-skills](https://github.com/ForrestChang/andrej-karpathy-skills) (영문)

## 라이선스

하위 프로젝트에 라이선스 파일이 있으면 그 디렉터리 기준을 따른다.
