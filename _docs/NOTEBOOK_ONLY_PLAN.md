# 노트북 단독 서빙 전환 계획 (2026-11-08)

**목표:** 집컴 서빙을 멈추고 앱·DB·Redis·lora·임베딩을 모두 노트북(`teagy`)에서 돌린다. 어드민 끄기·노트북 바탕화면 켜기는 지금처럼 유지한다.

**계기:** 11-08 15:35·15:54 집컴 Postgres가 `exit code 2`로 두 번 크래시했고, 디스크·CPU를 못 받아 복구가 각각 약 10분 걸렸다(사이트 530 두 번, 합계 약 22분). 11-06 장애도 같은 집컴 쪽이다.

**구조:** 노트북 도커에 `pgvector/pgvector:pg16`·`redis:7-alpine`을 올리고 포트 5432·6379를 직접 연다. 지금은 `desktop-link`(ssh -L)가 이 두 포트를 집컴으로 중계하므로, 중계를 끄면 `.env`의 `localhost:5432`와 k3s `external-db-redis.yaml`(10.42.0.1)을 그대로 쓸 수 있다. lora-server도 같은 방식으로 노트북 :8200에서 직접 연다.

## 받아들이는 대가 (사용자 확인 필요)

- **노트북을 들고 나가거나 덮개를 닫으면 사이트 전체가 꺼진다.** 예비 서버가 없다.
- 노트북 VRAM을 Ollama 7.8B와 lora 2.4B가 나눠 쓴다. 넘치면 Ollama가 일부 층을 CPU로 돌려 홈 채팅·mova 판단이 느려질 수 있다(1단계에서 측정한다).
- 바깥 백업이 없어진다. 집컴 DB 볼륨은 지우지 않고 2주 동안 보관한다.

## 지키는 것

- 무료만 쓴다. 커밋 전에 Codex OK를 받는다. 집컴에서 SSH로 `journalctl`·`systemctl --user status`는 부르지 않는다.
- 집컴 DB 데이터는 최종 확인 전까지 지우지 않는다(되돌리기의 근거).

---

## 1단계: 서비스 영향 없는 준비 (다운 없음)

### 1-1. 노트북 lora-server 재구성
- `~/.venv-exaone`: `uv venv` + `fastapi==0.142.2 uvicorn==0.54.0 httpx==0.28.1 pydantic==2.13.5`(집컴과 같은 버전).
- `~/llama.cpp`: CUDA 빌드(`-DGGML_CUDA=ON -DCMAKE_CUDA_ARCHITECTURES=89`).
- GGUF: 집컴 `~/lora_adapters/gguf/mova_20260926_161748-Q5_K_M.gguf`(1.7GB)를 scp로 복사하고 `~/lora_adapters/LATEST_GGUF`에 경로를 적는다.
- 시험: 8200은 아직 중계가 쓰므로 `uvicorn ... --port 8299`로 따로 띄운다.
- **검증:** `/health` 200, `/generate` 1건 응답·지연, 7.8B를 올린 상태의 `nvidia-smi` 합계. 넘치면 멈추고 보고한다. 선택지는 lora `-ngl` 일부만 GPU에 올리기, 또는 7.8B `keep_alive`를 줄이기다.

### 1-2. 임베딩(bge-m3)을 노트북 Ollama로
- `ollama pull bge-m3`. VRAM이 모자라면 `num_gpu 0` 변형(CPU)으로 만든다(이해 모델 v6과 같은 방식).
- **검증:** 같은 문장의 임베딩을 집컴(:21435)과 노트북(:11434)에서 받아 차원 1024와 코사인 ≥ 0.999를 확인한다.

### 1-3. DB 리허설
- 노트북에 DB를 임시 포트 15432로 띄운다(untracked `docker-compose.yaml`, `DB_PORT=15432`).
- 집컴에서 `pg_dump -Fc`(운영 중에도 일관된 스냅샷)를 받아 복원한다.
- **검증:** 테이블별 `count(*)`가 집컴과 같고, `vector` 확장·인덱스 개수가 같다. 덤프·복원에 걸린 시간을 재서 다운 시간을 예측한다.

## 2단계: 전환 (다운 약 5~10분, 사용자에게 시작 알림)

1. 집컴 `standby-agent` 끄기 → 집컴 cloudflared 0 확인(집컴이 터널을 다시 올리지 않게).
2. 노트북 `serve-agent` 끄기 → 노트북 cloudflared·backend·auth를 0으로(쓰기 중단).
3. 집컴 최종 `pg_dump -Fc` + Redis `redis-cli --rdb` 복사 → 집컴 DB·Redis 컨테이너 `docker stop -t 60`(볼륨은 유지).
4. 노트북 `desktop-link`·`ollama-tunnel` 끄기(disable) → 리허설 DB 지우기 → 5432·6379로 DB·Redis 띄우고 최종 덤프 복원.
5. `.env`의 `OLLAMA_EMBED_URL=http://host.docker.internal:11434`(1-2에서 CPU 변형을 만들었으면 모델 이름도) → `./k8s/deploy.sh --external-db`(Secret 갱신·apply).
6. 노트북 `lora-server` enable(--now) → backend·auth·cloudflared 1.
7. **검증:**
   - healthz 200, 테이블 `count(*)`가 3번의 덤프와 같음.
   - 로그인 1회(사용자).
   - mova 추천 1건이 lora 경로로 나오는지(로그에서 확인).
   - 벡터 검색 1건.
   - `scripts/eval_chat_queries.py` 23질의.

**되돌리기(새 쓰기가 쌓이기 전까지 유효):** 노트북 DB·lora 멈춤 → 집컴 DB·Redis `docker start` → `desktop-link`·`ollama-tunnel` enable → `.env` 되돌리고 `deploy.sh --external-db` → 집컴 `standby-agent` enable. 전환 뒤 새 쓰기가 생겼다면 노트북 DB를 덤프해 집컴에 복원한 뒤 되돌린다.

## 3단계: 집컴 정리 (전환이 하루 안정된 뒤)

- 집컴 `standby-agent`·`lora-server`·`ollama-warm` disable, k3s 배포를 0으로, DB·Redis 컨테이너는 멈춘 채 둔다.
- k3s·도커 시스템 서비스를 끄는 건 sudo가 필요하다 → 사용자 선택(꺼도 되고, 그대로 두면 유휴).
- 2주 뒤 이상이 없으면 집컴 DB 볼륨 삭제 여부를 사용자가 정한다.

## 4단계: 코드 정리 (PR 1개, 2단계가 끝난 뒤)

| 파일 | 변경 |
|---|---|
| `k8s/ops-agent/ops_agent.py` | `/server/stop`은 넘겨줄 곳 없이 노트북을 전부 끈다: 러너 멈춤 → 터널 0 → Arda stop → `docker stop -t 60 suvisdev-db-1 suvisdev-redis-1` → 스위치 off. `/server/start`는 스위치 on → DB·Redis start·healthy 대기 → 러너 → 터널 1 → Arda. `/server/stop-all`과 집컴 관련 코드(`HOME_*`, `_home`, `check_can_stop`의 집컴 검사) 삭제 |
| `k8s/ops-agent/test_ops_agent.py` | 위 동작으로 바꾸고, DB를 스위치보다 먼저 멈추는지·켤 때 DB가 앱보다 먼저인지 시험 |
| `k8s/failover/`·`k8s/sync-standby.sh` | 삭제(serve-agent·standby-agent·desktop-link 포함). 터널 수는 `deploy.sh`와 켜기가 1로 맞춘다 |
| `.github/workflows/backend-deploy.yml` | "집 밖이면 빌드만" 분기와 `sync-standby.sh` 단계 삭제. 항상 `deploy.sh --external-db --build` |
| `suvisdev/apps/viewer/.../admin_ops_router.py`, `suvis/app/admin/_components/ops-control-card.tsx` | `stop-all` 제거, "서버 끄기" 하나로. 확인 문구: "사이트 전체가 꺼집니다. 켜기는 노트북 바탕화면 `서버 켜기`" — 화면 캡처 확인 |
| 문서 | 루트 `CLAUDE.md` 운영 구성, `k8s/README.md`, ADR-0008(노트북 단독), WORK_LOG·LESSONS·PROGRESS |

- PR #238: `sync-standby.sh` 부분은 필요 없어진다. Dockerfile digest 고정만 남겨 다시 올리거나 닫는다.
- **검증:** `python3 -m pytest k8s/ops-agent -q`, 백엔드 어드민 시험, `pnpm type-check`·`lint`, 실제 끄기 → `서버 켜기.cmd` 한 번(사용자 허락 뒤).

---

## 실행 결과 (2026-11-08)

- **1단계**: lora 재구성 완료. llama.cpp는 집컴과 같은 커밋 `869034b`로 sm_89 빌드했고, GGUF는 sha256이 일치했다. 응답은 200·약 2초이고, VRAM은 7.8B와 함께 7,755/8,188MB였다. bge-m3는 GPU 자리가 없어 `bge-m3-cpu`를 만들었다.
  1-3 리허설은 **생략**했다. 집컴 DB가 16:34에 세 번째로 크래시해서, 덤프를 두 번 받는 것 자체가 위험하다고 판단했다(사용자 승인).
- **2단계**: 16:49에 쓰기를 멈췄다. 덤프는 16:50~16:53에 받았다(49MB, 테이블 69개). 덤프 직후 집컴 Claude가 집컴 DB·Redis를 멈춰서 실시간 행 수 대조와 Redis 2키 복사는 하지 못했다.
  노트북에 복원하는 데 16초가 걸렸고, 69개 테이블 행 수가 덤프 안의 COPY 행 수와 모두 같았다. `.env`의 `OLLAMA_EMBED_URL`·`OLLAMA_EMBED_MODEL` 두 줄을 바꿨다. 16:58에 서빙을 다시 시작했다(다운 약 9분).
  임베딩은 저장된 벡터와 코사인 0.99999였다. mova 하네스는 25/28이었다(실패 3건은 이해 모델이 장르 질문을 `evaluate`로 오분류한 것, 전환과 무관한 것으로 판단·미확정).
- **3단계**: 집컴 Claude가 k3s·Ollama·컨테이너·WSL 자동 시작을 모두 껐다. DB 볼륨과 덤프는 보존했다.
- **4단계**: 이 문서와 같은 PR.
