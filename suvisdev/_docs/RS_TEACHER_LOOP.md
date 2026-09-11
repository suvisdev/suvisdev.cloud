# RS 교사 루프 + RAG 임베딩 컷오버 런북 (2026-09-11)

두 작업의 실행 절차 SSOT. 배경 결정: 엑사온 학습은 "교사가 대신 쓰기"에서
**rejection sampling(학생 생성 → 교사 선별)**로 전환, RAG 임베딩은
nomic-embed-text → **bge-m3**(한국어 recall@8 0.390→0.860 실측).

운영 원칙은 그대로 유효하다: 재학습은 배치 큐(트리거 모일 때 한 번에),
학습 전 `systemctl --user stop lora-server` → VRAM 하강 확인, 재학습 후
`export_mova_gguf.py` 필수, 회귀 하네스(`eval_chat_queries.py`) 전후 비교.

---

## 1. RS 교사 루프 (엑사온 데이터셋 v2)

기존 `datasets/gen_teacher_dataset.py`(교사 직접 작성)의 후속. 학생(EXAONE
LoRA)이 온도 4종(greedy 포함)으로 후보를 만들고, 그라운딩 하드 필터를 통과한
후보를 Gemini가 루브릭(그라운딩>말투>hook>정직성)으로 심판한다. 10점 만점
7점 미만이거나 유효 후보가 없으면 교사 작성 폴백(source=teacher).

### 스크립트

| 파일 | 역할 |
|------|------|
| `scripts/rs_mine_queries.py` | chats에서 실사용 질의 채굴(추천 트랙만, 빈도순) |
| `scripts/rs_generate_and_judge.py` | 후보 생성→검증→심판→`datasets/chat_teacher_dataset_v2.jsonl` |
| `datasets/rs_audit.jsonl` | 질의별 채택 소스·점수·사유(재개 로그 겸용 — 지우면 처음부터) |

### 실행 위치 — 노트북 **호스트**에서 (파드 아님)

프롬프트의 카탈로그가 프로덕션 DB(859편+태그)여야 학생 채택률이 나온다
(데스크톱 스냅샷 205편·장르 태그뿐이라 심판 점수가 낮게 나옴 — 스모크에서
score 6으로 전건 교사 폴백된 게 그 증거). 또 후보 샘플링은 lora-server
**내부** llama-server(127.0.0.1:8201, OpenAI 호환)를 직접 호출한다 — 공개
`/generate`(:8200)는 greedy 고정이라 파드에서는 온도 샘플링이 안 된다.

```bash
# 노트북 WSL 호스트, suvisdev/에서 (.env가 DB·Gemini 키 제공)
python scripts/rs_mine_queries.py                       # → datasets/rs_queries.jsonl
python scripts/rs_generate_and_judge.py --limit 5       # 소량 검증
python scripts/rs_generate_and_judge.py --queries datasets/rs_queries.jsonl
```

- Gemini 무료 티어 준수(질의당 심판 1회, 4.5s 슬립) — 300질의 ≈ 30~40분.
- 중단해도 재실행하면 audit 로그 기준으로 이어서 돈다.
- `student` 채택률이 낮으면(예: <30%) 임계값·루브릭을 조정하기 전에 audit의
  reason부터 읽을 것 — 카탈로그 품질 문제인지 모델 문제인지 갈린다.

### 학습 트리거(배치 큐) — 이 조건이 모이면 한 번에

v2 데이터셋이 기존 94건 대비 **유의미 증분(권장 300건+)**이 됐을 때:

```bash
systemctl --user stop lora-server   # VRAM 하강 확인(nvidia-smi 맹신 금지)
# v2 + no-pick 예시 병합본으로 학습(gen_teacher_dataset.py의 NO_PICK 세트 재사용)
python scripts/train_mova_lora.py --dataset datasets/chat_teacher_dataset_v2.jsonl
python scripts/export_mova_gguf.py
systemctl --user start lora-server && curl -s localhost:8200/health
curl -s -X POST localhost:8200/reload -H "X-LoRA-Token: $LORA_SERVER_TOKEN"
python scripts/eval_chat_queries.py   # 전후 비교 없이 배포 금지
```

---

## 2. RAG 임베딩 컷오버 (nomic → bge-m3)

### 근거 (scripts/eval_embedding_models.py, 로컬 205편·60질의·패러프레이즈 포함)

| 모델 | recall@8 | mrr@8 | 비고 |
|------|----------|-------|------|
| **BAAI/bge-m3** | **0.860** | **0.940** | 1024차원, 접두사 불요, Ollama 공식 |
| intfloat/multilingual-e5-base | 0.765 | 0.870 | 768 드롭인이나 query:/passage: 접두사 리팩터 필요 |
| nomic-embed-text (현행) | 0.390 | 0.536 | 한국어 취약 |

bge-m3 채택 — 최고 성능 + 접두사 불요(포트 무변경). 비용은 hub_knowledge
한 테이블의 1024 마이그레이션뿐(movies/reviews/taste·dispatch는 각자 768
공간이라 무관).

### 코드 반영(완료, 배포 대기)

- `EMBEDDING_DIM` 768→1024, Ollama 어댑터 기본모델 bge-m3,
  alembic `20260911_0001`(vector(1024), 기존 벡터 NULL).
- 데스크톱 검증 완료: alter 적용 + gemini 백엔드 10편 색인 + 1024 쿼리
  벡터 검색 히트 확인.

### 노트북 컷오버 절차 (순서 엄수)

```bash
ollama pull bge-m3                                   # ① 모델 선다운로드(~1.2GB)
cd ~/suvisdev.cloud && git pull
./k8s/deploy.sh --external-db --build                # ② 코드 배포
kubectl -n suvisdev exec deploy/backend -- alembic upgrade head   # ③ 마이그레이션
# ④ 재임베딩 — 호스트에서(Ollama가 호스트에 있음), 859편 수 분 소요
python scripts/ingest_hub_knowledge.py --reset --embedding-backend ollama
# ⑤ 검증
python scripts/eval_chat_queries.py                  # RAG 경로 회귀
# 채팅 1건 실측 + backend 로그 [HubRagInteractor] vector_search hits= 확인
```

- ③~④ 사이 RAG는 벡터 0건이라 태그 폴백으로만 동작(채팅은 계속 됨 —
  설계된 폴백). 트래픽 낮은 시간대 권장.
- `EMBEDDING_BACKEND`는 ollama 유지. gemini로 바꿀 일이 생기면 그때도
  전체 재임베딩 필수(공간 상이) — 기존 규칙 동일.
- 롤백: `alembic downgrade -1` + 코드 revert + nomic 재색인.

### 잔여

- 데스크톱 로컬 hub는 gemini 10편 스모크 상태 — 로컬 RAG를 실제로 쓰려면
  로컬도 `--reset` 재색인(백엔드는 gemini 권장, 데스크톱에 Ollama 없음).
- mova `movies.embedding`/`reviews.embedding`(취향 벡터, Gemini 768)은 별도
  트랙 — 이번 전환과 무관하게 유지.
