# LLM 코딩 행동 지침 (Karpathy 원칙)

LLM의 일반적인 코딩 실수를 줄이기 위한 행동 지침이다. [Andrej Karpathy의 관찰](https://x.com/karpathy/status/2015883857489522876)에서 출발한 네 가지 원칙을 한국어로 정리한 것이다.

## 응답 언어

**항상 한국어로만 답변한다.** 영어를 포함한 다른 언어는 사용하지 않는다.

## 배경: 무엇을 고치려는가

Karpathy가 지적한 전형적인 문제는 다음과 같다.

> 모델이 대신 잘못된 가정을 하고, 확인 없이 그대로 밀어붙인다. 혼란을 관리하지 않고, 명확히 하지 않으며, 모순을 드러내지 않고, 트레이드오프를 말하지 않고, 밀어붙여야 할 때도 반대하지 않는다.
>
> 코드와 API를 과하게 복잡하게 만들고, 추상을 비대하게 키우고, 데드 코드를 정리하지 않는다… 100줄이면 될 일을 1000줄짜리 덩어리로 만든다.
>
> 때로는 과제와 직교인 코드·주석까지 이해 없이 바꾸거나 없앤다.

| 원칙 | 겨냥하는 문제 |
|------|----------------|
| 구현 전 사고 | 잘못된 가정, 숨겨진 혼란, 트레이드오프 부재 |
| 단순성 우선 | 과도한 복잡도, 비대한 추상 |
| 정밀한 수정 | 과제와 무관한 편집, 건드리면 안 되는 코드 변경 |
| 목표 중심 실행 | 테스트·검증 가능한 성공 기준 없이 진행 |

## 트레이드오프

본 지침은 **속도보다 신중함**에 우선순위를 둔다. 사소한 작업(명백한 오타 수정, 한 줄 수정 등)은 상황에 맞게 판단한다.

---

## 1. 구현 전 사고 (Think Before Coding)

- 자신의 가정을 **명시**한다. 불확실하면 **질문**한다.
- 해석의 여지가 여러 가지면 임의로 고르지 말고 **대안을 제시**한다.
- 더 단순한 접근이 있으면 **제안**한다.
- 불분명하면 **멈춘다**.

## 2. 단순성 우선 (Simplicity First)

- 요청되지 않은 기능·추상·설정은 넣지 않는다.
- **발생 불가능한** 시나리오를 위한 예외 처리는 하지 않는다.

## 3. 정밀한 수정 (Surgical Changes)

- 인접 코드를 임의로 "개선"하지 않는다.
- **기존 스타일**을 따른다.
- 변경으로 불필요해진 import·변수만 제거한다.

## 4. 목표 중심 실행 (Goal-Driven Execution)

모호한 지시를 검증 가능한 목표로 바꾼다.

```text
1. [단계] → 검증: [확인 사항]
2. [단계] → 검증: [확인 사항]
```

## 5. 작업 기본 프롬프트 (2026-10-02, 사용자 지시로 상시 적용)

- **LLM이 들어간 기능은 트리거와 처리를 나눈다.** "언제 실행되나"가 모델 판단에만 걸려 있으면, 코드로 확실히
  판정되는 경우는 코드로 먼저 잡는다. 모델이 다른 걸 골랐을 때의 동작을 테스트로 보인다.
- **실사용 오류는 원인부터**(`systematic-debugging`). 그 문장만 고치지 말고 같은 유형 전체가 고쳐지는지 테스트로 보인다.
- **완료는 실제로 돌려 본 결과로만 말한다**(`verification-before-completion`). 못 돌려 본 것은 따로 적는다.
- **재학습·사용자 작업(코랩 실행, 집컴 조작 등)은 해결책으로 바로 내밀지 않는다.** 코드·설정으로 되는지 먼저 보고,
  꼭 필요하면 기대 효과·근거·사용자 수고를 먼저 밝혀 사용자가 고르게 한다.

---

## 저장소 구조 및 하위 문서

```text
cloud.suvisdev/
├── _docs/                 ← 공통 문서 (워크스페이스·인프라·도구 설정, 작업 일지)
├── suvisdev/              ← 백엔드 (FastAPI, Clean Architecture)
│   ├── CLAUDE.md          ← 백엔드 SSOT(레이어·SOLID·스타-토폴로지)
│   ├── _docs/             ← 백엔드 문서 (엔티티·인증·DB·배포 규칙)
│   └── apps/<app>/_docs/  ← 앱별 ERD·도메인 문서 + CLAUDE.md
├── suvis/                 ← 프론트엔드 (Next.js)
│   ├── CLAUDE.md          ← 프론트 SSOT(디렉터리·컴포넌트 규칙)
│   └── _docs/             ← 프론트 문서 (React 세부 규칙·디자인 정책)
└── gildle/                ← 모바일 (Flutter)
    ├── CLAUDE.md          ← 아직 비어 있음 — 당분간 _docs/ 하네스 문서가 대신함
    └── _docs/             ← Flutter 문서 (카카오 OAuth·Android/iOS 하네스)
```

> `_claude/` 라는 이름의 하위 폴더는 어디에도 없다 — 각 스택의 규칙은
> 스택 루트의 `CLAUDE.md` + 그 옆 `_docs/`에 있다.

### 문서 배치 규칙

| 문서 성격 | 위치 |
|-----------|------|
| 공통·인프라·워크스페이스 설정 (Obsidian, 심볼릭 링크 등) | `_docs/` |
| 백엔드 아키텍처·API·ERD·FastAPI 규칙 | `suvisdev/_docs/` |
| 앱별 ERD·도메인 설계 | `suvisdev/apps/<app>/_docs/` |
| 프론트엔드 화면 설계·컴포넌트·Next.js 규칙 | `suvis/_docs/` |
| Flutter 화면 설계·위젯·Dart 규칙 | `gildle/_docs/` |

> **규칙:** 새 문서를 만들 때 위 표에서 성격에 맞는 폴더에 배치한다. 루트나 임의 경로에 두지 않는다.

| 작업 영역 | CLAUDE.md |
|-----------|-----------|
| 백엔드 (FastAPI · Clean Architecture) | [`suvisdev/CLAUDE.md`](suvisdev/CLAUDE.md) |
| 프론트엔드 (Next.js) | [`suvis/CLAUDE.md`](suvis/CLAUDE.md) |
| 모바일 (Flutter) | `gildle/CLAUDE.md`는 비어 있음 — `gildle/_docs/`의 하네스 문서(카카오 OAuth·Android·iOS)를 대신 참조 |

**Karpathy 네 원칙은 모든 영역에서 항상 유효하다.**

## 작업 일지

**의미 있는 작업(코드 수정, 조사·디버깅, 데이터 변경, 문서화 등)을 한
세션은 끝나기 전에 작업 영역에 맞는 워크로그에 그날 날짜로 기록한다.**
워크로그는 영역별로 분리돼 있다(2026-08-19 분리, 구 `WORK_LOG.md`는
`WORK_LOG_MOVA.md`로 개명됨 — 과거 문서의 `WORK_LOG.md` 인용은 대부분
이 파일을 가리킨다):

| 파일 | 영역 |
|------|------|
| `_docs/WORK_LOG_MOVA.md` | mova(영화 추천·채팅·게임) |
| `_docs/WORK_LOG_GILDLE.md` | gildle(산책 경로) |
| `_docs/WORK_LOG_MAINPAGE.md` | 그 외 전부(메인페이지·어드민·인증·gildle·인프라) |

세션 종료가 트리거다. 파일 상단의 템플릿(작업 내용/수정·구현/오류·막힌 점/
데이터/산출물)을 따르고, 최신 날짜가 맨 위에 오게 추가한다. 이미 그날
항목이 있으면 새로 만들지 말고 이어서 보강한다. 단순 질의응답·읽기
전용 조사만 한 세션은 생략해도 된다.

**워크로그와 함께 `_docs/INTERVIEW_QUESTIONS.md`도 갱신한다** — 그날
작업으로 학습·면접 대비용 인터뷰 질문 5~10개를 추가한다(최신 날짜가 맨 위,
답은 `<details>`로 접기, "무엇을"보다 "왜 그렇게"를 묻기). 사용자가 변경
내용을 스스로 설명할 수 있게 하는 장치다.

**`_docs/LESSONS.md`도 함께 갱신한다(2026-09-29 신설)** — 그날 **잘못됐던 것을
어떻게 극복했는지**를 한 줄씩 적는 압축 층이다(증상 → 원인 → 극복 · 상태 · 근거
WORK_LOG 날짜). WORK_LOG는 상세 기록이라 사용자가 다 읽을 수 없으니, 실패를
해결(또는 미결로 확정)한 세션은 반드시 이 파일에 한 줄을 남긴다. 사소한 오타
수정은 제외. 같은 사건이 이어지면 새 줄을 만들지 말고 기존 줄의 상태를 갱신한다.

`_docs/SUVIS_ADMIN_MULTIAGENT_PROGRESS.md`는 WORK_LOG와 짝을 이루는
**재개용 요약**이다 — WORK_LOG가 "그날 있었던 일"의 상세 기록이라면,
PROGRESS.md는 "지금 뭐가 끝났고 뭐가 남았는지"만 압축해서 유지한다.
완료된 항목은 상세 대신 WORK_LOG 날짜만 남기고, 백로그는 최신 상태로
갱신한다(오래된 항목이 이미 완료돼 있으면 확인 후 옮긴다).

## 명령어

세 스택이 한 저장소에 있으므로 **어느 디렉터리에서 실행하는지**가 중요하다.

```bash
# 프론트엔드 (suvis/) — pnpm 사용, npm 아님
pnpm dev             # 개발 서버
pnpm build
pnpm lint
pnpm type-check      # tsc --noEmit
pnpm format          # prettier --write

# 백엔드 (suvisdev/)
python main.py                    # uvicorn 127.0.0.1:8000, reload
pytest                            # pytest.ini의 testpaths 전체
pytest -m "not gpu and not ollama"  # 외부 자원 필요한 테스트 제외(로컬 표준)
alembic upgrade head              # 마이그레이션 적용
alembic history                   # 리비전 체인 확인
PYTHONPATH="$PWD:$PWD/apps" lint-imports   # 클린 아키텍처 의존 규칙 검사
python scripts/check_env_drift.py # .env.example 키가 .env에 다 있는지(값 비교 안 함)

# 모바일 (gildle/)
flutter run

# 인프라 (루트) — k8s로 전환됨(2026-09-07, 데스크톱). WSL2에 k3s 직접 설치.
./k8s/deploy.sh            # Secret(.env→suvisdev-env) 갱신 + 전체 apply
./k8s/deploy.sh --build    # 이미지 재빌드 + rollout restart 포함
kubectl -n suvisdev get pods   # 상태 확인. 상세: k8s/README.md
# CI/CD(2026-10-01): PR·main push마다 GitHub Actions가 3스택 검사. main에 백엔드가 머지되고
# backend-ci가 통과하면 노트북의 셀프호스티드 러너(유일)가 deploy.sh --external-db --build로 빌드·배포하고
# sync-standby.sh로 집컴에 반영한다 — 수동 배포는 Secret(.env)만 바꿀 때. 노트북이 집 밖이면 실패(미결,
# k8s/failover/README.md "배포"). 상세: k8s/README.md "CI/CD"
```

**구 `docker-compose.yaml`은 삭제됐다(2026-09-07)** — 데스크톱은 k8s가 대체.
`suvisdev/.env`는 deploy.sh가 매번 Secret으로 변환해 주입하므로 compose 시절
`--env-file` 누락 사고(빈 자격증명 502, 2026-07-30·08-04)는 구조적으로 재발
불가(.env 없으면 스크립트가 즉시 실패). **운영 구성(2026-10-05~06)은 아래 "주의사항 · 개인 배포 환경"** —
두 기기 모두 k3s(backend·auth·cloudflared 파드), DB·Redis는 집컴 도커 한 곳. 배포는
`./k8s/deploy.sh --external-db [--build]`. 노트북의 untracked `docker-compose.yaml`은 예전 롤백용 — 손대지 않는다.
절차는 `k8s/README.md`·`k8s/failover/README.md`.

## 테스트

- 프레임워크는 **pytest**다(백엔드). 프론트(`suvis/`)에는 현재 테스트 코드·테스트
  의존성이 없다 — 검증은 `pnpm type-check`·`pnpm lint`로 한다.
- 마커(`suvisdev/pytest.ini`): `gpu`(실제 GPU + 모델 가중치 필요),
  `ollama`(실제 Ollama 서버 필요). 일반 실행은 **`-m "not gpu and not ollama"`**를
  붙인다 — `apps/titanic/tests/conftest.py`의 ollama 자동 skip은 `markexpr`이
  **비어 있을 때만** 걸리므로, `-m "not gpu"`만 주면 자동 skip이 꺼지면서
  ollama 테스트가 실행돼 로컬에 모델이 없으면 실패한다(2026-08-07 확인).
- `apps/ontology/test/conftest.py`가 `HF_HUB_OFFLINE`을 켜 둔다. GPU 테스트는
  **로컬에 이미 캐시된** HF 모델만 쓰며, 캐시가 없으면 hang 대신 즉시 실패한다.
- 학습 산출물(`apps/ontology/runs/`)은 `.gitignore` 대상이라 클론 직후에는 이를
  요구하는 테스트가 실패할 수 있다(정상).

## 환경 변수

- 파일은 **`suvisdev/.env` 하나**다(`.env.local` 아님). `suvis/`에는 `.env`가 없고,
  백엔드 주소는 `NEXT_PUBLIC_API_URL` 미설정 시 `http://127.0.0.1:8000`으로 폴백한다.
- 필수: `DATABASE_URL`, `MOVA_DATABASE_URL`, `JWT_SECRET`
- 외부 API: `GEMINI_API_KEY`, `TMDB_API_KEY`, `KOFIC_API_KEY`, `OPENWEATHERMAP_API_KEY`
- OAuth: `{GOOGLE,KAKAO,NAVER}_CLIENT_ID` / `_CLIENT_SECRET` / `_REDIRECT_URI`
- **S3는 연결돼 있다(2026-08-10 실측 정정)**: `AWS_ACCESS_KEY_ID`·
  `AWS_SECRET_ACCESS_KEY`·`AWS_REGION`·`VISION_S3_BUCKET` 네 키가 로컬·EC2 `.env`에
  모두 채워져 있고, EC2 컨테이너에서 `Tank.list_buckets()`가
  `suvisdev-s3-584569945696-ap-northeast-2-an`을 반환한다(구 susu 앱 업로드 객체
  `media/{user_id}/...` 존재). **이 문서에 오래 남아 있던 "미설정" 기술은 틀린
  것이었다** — S3 경로를 타는 코드는 정상 동작한다는 전제로 작업할 것.
  버킷은 **비공개**라 객체 공개 URL은 403이다. 표시에는
  `Tank.generate_presigned_url()`(기본 1시간)을 쓴다.
- **`RECOMMENDATION_BACKEND`(mova 추천, 기본값 `lora`)**: 운영은 기본 `lora`를 쓴다 —
  `LORA_SERVER_URL=http://host.docker.internal:8200`. lora-server는 **집컴**(GPU, `:8200`)에 있고, 노트북 앱은
  `desktop-link`(ssh -L 8200)로 같은 서버에 닿는다(k3s hostAliases가 `host.docker.internal`→`10.42.0.1`). lora 호출 실패 시 Gemini 자동 폴백 DI(2026-08-26 배선)가
  받친다. 수동 전환이 필요하면 `suvisdev/.env`에서
  `RECOMMENDATION_BACKEND=gemini`로 바꾸고 `./k8s/deploy.sh --external-db`
  (Secret 갱신) + `kubectl -n suvisdev rollout restart deploy/backend`.
  배포 후 확인: `kubectl -n suvisdev exec deploy/backend -- printenv |
  grep -E 'RECOMMENDATION_BACKEND|LORA_SERVER_URL'`. 데스크톱 GGUF 서버를
  쓰려면 `LORA_SERVER_URL=https://lora.suvisdev.cloud`로 전환(현재 미사용).
- **`MOVA_CHAT_AGENT`(2026-09-29, 기본 0)**: 1이면 mova 채팅이 학습한 판단 모델(`MOVA_AGENT_MODEL`, 기본
  `mova-agent-v9`, Ollama CPU)로 도구를 골라 답한다(`MovaChatAgent`). 6칸 이해 단계는 폴백·롤백용으로 그대로.
  설명 `suvisdev/apps/mova/_docs/MOVA_CHAT_ORCHESTRATOR.md` §8.
- **`MOVA_ORCHESTRATOR_SHADOW_MODEL`(2026-09-28, 노트북 `mova-understand`)**: 학습한 이해 모델을
  응답에 영향 없이 백그라운드로 비교해 `suvisdev/datasets/understanding/shadow_log.jsonl`에 쌓는다.
  v6는 Modelfile `num_gpu 0`으로 **CPU 전용**(GPU는 운영 7.8B·lora-server로 꽉 참). 비우면 꺼짐.
  설명 `suvisdev/apps/mova/_docs/MOVA_CHAT_ORCHESTRATOR.md` §7.

## 브랜치 전략

- `main` — 기본 브랜치(PR 대상). `suvisdev` — 주 작업 브랜치. `suvis` — 프론트 작업용.
- **`develop` 브랜치는 없다.** 머지 방향은 `suvisdev` → `main`이다.
- 커밋·푸시는 사용자가 요청할 때만 한다.

## 주의사항

- **VRAM**: `lora-server`(EXAONE-3.5-2.4B, llama.cpp GGUF Q5_K_M —
  2026-09-02 전환, 구 fp16 hf `serve.py`는 롤백용)가 데스크톱
  DESKTOP-IOAQ7L7의 systemd 유저 서비스로 기동된다(2026-09-01 노트북→
  데스크톱 이전). 모델 학습 전 `systemctl --user stop lora-server`, 학습 후
  `start` + `:8200/health` 확인. 재학습 후엔 `export_mova_gguf.py`로 GGUF
  변환 필수. `nvidia-smi`의 free 수치는 WSL2에서 불안정하니 그것만 믿지 말 것.
- 개인 배포 환경(2026-10-05~06, 인수인계 바탕화면 `HANDOFF_suvisdev_2026-10-06.md`):
  - **집컴 `DESKTOP-T89E5ID`**(GTX 1650 SUPER 4GB, 상시 가동): **Postgres·Redis(도커, 유일)**·lora-server(GPU :8200)·
    Ollama(CPU)·HAProxy `ollama-proxy`(:11435 노트북 GPU 우선/집컴 CPU 예비, :11436 노트북 전용)·로컬 레지스트리.
    **이미지를 빌드하지 않는다**(메모리 부족으로 DB 크래시 2회, 10-05).
  - **노트북 `teagy`**(RTX 4060, 들고 다님): Ollama GPU · CD 러너(유일) · 이미지 빌드. 집 LAN이면 노트북이
    우선 서빙(`desktop-link`로 집컴 DB 사용), **집 밖이면 앱 서빙은 집컴, 노트북은 GPU만**(Tailscale `ollama-tunnel`).
  - 누가 서빙할지는 노트북 `serve-agent`·집컴 `standby-agent`가 cloudflared replicas로 자동 전환(`k8s/failover/README.md`).
  - Tailscale: 노트북 100.118.78.100, 집컴 100.91.129.31(내부 IP 172.30.1.21은 집에서만). 집컴 SSH:
    `ssh -i ~/.ssh/home_desktop -o UserKnownHostsFile=~/.ssh/known_hosts_ollama_tunnel suvisdev@100.91.129.31`
  - 구 개인 EC2는 중지 보관(Arda는 별도 `arda-api`). mova 부팅 작업은 `ENABLE_MOVA_STARTUP=false`로 끈다(집컴 `.env`만).

## 하네스 설정 (`.claude/`)

```text
.claude/
├── settings.json          # 훅 설정 (커밋됨, 팀 공용)
├── settings.local.json    # 개인 권한 허용 목록
├── rules/                 # 경로별 코딩 규칙 — 해당 파일을 다룰 때 자동 로드
│   ├── typescript.md      #   **/*.ts, **/*.tsx
│   ├── api-standards.md   #   suvis/lib/*-api.ts, suvis/app/api/**/route.ts
│   ├── testing.md         #   suvisdev/**/test(s)/**/*.py
│   ├── security/auth.md   #   라우터·프록시·세션 — require_admin, 토큰 3계층 전달
│   └── security/pci.md    #   결제 코드가 생기면 발동 (현재 대상 파일 없음)
└── projects/-home-a-projects-suvis/memory/   # 주제별 메모 — 자동 로드 아님
    ├── MEMORY.md          #   인덱스              (읽으라고 지시해야 반영됨)
    ├── auto-memory.md     #   자동 메모리(홈 경로)가 뭘 언제 읽는지 설명
    ├── debugging.md       #   원인 규명한 문제와 진단 방법
    └── patterns.md        #   계층 구조·마이그레이션·테스트 패턴
```

### 규칙 문서를 새로 쓸 때

- **경로가 한정되는 규칙**(특정 언어·디렉터리)은 `.claude/rules/`에 둔다. 이 파일에
  넣지 않는다 — 여기는 매 세션 로드되므로 전 영역 공통 지침만 남긴다.
- `rules/*.md`는 `paths:` frontmatter가 **필수**다. 없으면 언제 적용되는지 알 수 없다.
- 규칙은 **저장소에서 실측한 관례**만 적는다. 다른 프로젝트 템플릿을 그대로 옮기지
  않는다(명령어·디렉터리·클래스가 실재하는지 `ls`/`grep`으로 확인할 것).

### 메모리 두 곳의 차이

| 위치 | 자동 로드 | 커밋 | 용도 |
|------|-----------|------|------|
| 저장소 안 `.claude/projects/-home-a-projects-suvis/memory/` | ✗ | ✓ | 팀·다른 에이전트와 공유하는 주제별 메모 |
| 홈 `~/.claude/projects/-home-a-projects-suvis/memory/` | ✓ | ✗ | 세션 간 개인 메모리(사실 하나당 파일 하나) |

**두 경로는 `~/`(홈)이냐 저장소 루트냐만 다르고 나머지가 같다.** 헷갈리면
자동 로드되는 쪽은 항상 홈이다.

같은 내용을 양쪽에 두지 않는다. 갈라지면 어느 쪽이 맞는지 알 수 없다.

### 훅

`settings.json`의 `UserPromptSubmit` 훅이 프롬프트에 "commit·커밋"이 들어오면
**영역별 `_docs/WORK_LOG_*.md`와 `_docs/SUVIS_ADMIN_MULTIAGENT_PROGRESS.md`를 먼저
갱신하라**는 지시를 주입한다. 위 "작업 일지" 규칙을 커밋 시점에 강제하는 장치다.

## 커밋 메시지 규칙

- Conventional Commits 형식 사용 (`feat:`, `fix:`, `docs:`, `refactor:`)
- 제목은 50자 이내
- 한국어로 작성
- 예시: `feat: 사용자 로그인 기능 추가`
