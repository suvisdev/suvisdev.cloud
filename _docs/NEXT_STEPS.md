# 다음 할 일 — 2026-09-22 퇴근 시점 정리

> 재개용 체크리스트. 상세 경위는 `WORK_LOG_MOVA.md`·`WORK_LOG_GILDLE.md` 09-22,
> 현황 요약은 `SUVIS_ADMIN_MULTIAGENT_PROGRESS.md`. 여기는 "집에서/내일 무엇부터"만.

## 지금 상태 (운영)

| 항목 | 상태 |
|---|---|
| mova 추천 | **v3 EXAONE**(`mova_20260922_064437`) 서빙, `RECOMMENDATION_BACKEND=lora`, 실패 시 Gemini 폴백 |
| mova 회귀 | v3 21/23 (배우 질의 2건 picks 0 — v4가 겨냥) |
| gildle | 자체 A\* 경로 · 시간 의존 그늘 · 제약 경로 · **루프 `/api/gildle/loops`** 배포됨 |
| 마지막 커밋 | 아래 "커밋 이력" |

## 집에서 할 것 (순서대로)

### 1. mova v4 코랩 학습 (사용자)
- [ ] 드라이브 `qwen-training/chat_teacher_dataset_v4.jsonl` **최신 파일로 다시 업로드**
      (바탕화면 `mova/FT/mova-colab-v4/` — 09-22 저녁 두 번 고침: `src` 보존 → `src` int화)
- [ ] 코랩에서 `mova-colab-v4/mova_exaone_colab.ipynb` 다시 열기(정규식 셀 바뀜) → 모두 실행
- [ ] 3-1 셀에 `원본 236건`, 평가 28행(원본 14 + 멀티턴)이 찍히면 정상
- [ ] 끝나면 `out/v4/`의 GGUF(1.6GB)를 바탕화면 `mova/FT/mova-colab-v4/`에 내려두기
- **합격 기준**: `eval_chat_queries.py`에서 송강호·마동석 질의가 살아나고 나머지 21건 유지

### 2. gildle 그늘 재계산 (수십 분 배치, 노트북)
```bash
cd suvisdev
PYTHONPATH="$PWD:$PWD/apps" .venv/bin/python -m gildle.scripts.compute_shade_scores
```
- 모델 B 예측(`apps/gildle/data/height_model_pred.json`, 84,665동)을 자동으로 적용한다
  (로그에 `높이 모델 예측 적용 84665동`이 찍혀야 함). 없으면 `train_height_model.py --apply` 먼저.
- 끝나면 전후 비교: 슬롯별 그늘 0% 간선 비율·평균 그늘 — `shade_scores.json` 갱신은
  라우터 mtime 캐시가 자동 반영하므로 재배포 불필요.
- .venv에는 shapely가 있다(파드에는 없음 — 파드에서 돌리지 말 것).

### 3. v4 GGUF 반영 (GGUF 받은 뒤, 노트북)
```bash
cp <GGUF> ~/lora_adapters/gguf/ && echo ~/lora_adapters/gguf/<GGUF> > ~/lora_adapters/LATEST_GGUF
curl -X POST http://127.0.0.1:8200/reload -H "X-Lora-Token: $LORA_SERVER_TOKEN"
kubectl -n suvisdev exec deploy/backend -c backend -- sh -c \
  "cd /suvisdev && PYTHONPATH=/suvisdev:/suvisdev/apps python scripts/eval_chat_queries.py"
```
- 21/23 미만이거나 배우 질의가 그대로 0편이면 `LATEST_GGUF`를 v3로 되돌린다.

## 내일 이후 (우선순위)

1. **gildle 그늘 실측 검증** — 아는 거리 5곳, 정오·15시 사진 vs 계산값(가장 큰 구멍,
   `apps/gildle/_docs/GILDLE_ROUTING_ALGORITHM.md` §3-③)
2. **mova `chat`에 `intro` 저장 칼럼** — 운영 응답을 학습 자료로 모으려면 필요(지금은
   `chat_messages` 136행만)
3. gildle Flutter 지도 화면 + FCM(`google-services.json`)
4. 모델 A(간선 선호)는 `walks` 기록이 쌓인 뒤 — 루프 API가 수집 입구
5. 모델 D(결빙) 데이터: DEM(국토지리정보원/SRTM) + 서울 결빙 취약구간
6. 프론트 eslint 설치 안 됨(`node_modules`에 없음) → `pnpm install` 후 lint
7. `~/.venv-exaone` 재학습 전 버전 확인(transformers 5.5.0·peft 0.20.0)

## 커밋 이력 (09-22)

| 커밋 | 내용 |
|---|---|
| `d0fd885` | v3 EXAONE 운영 반영·gildle walks API·앱 출시 준비 |
| `c4f32d8` | GGUF 변환 파이프라인 EXAONE 보정 경유·경로 정정 |
| `4bd0485` | mova v4 학습 데이터 895행 |
| `4d6cfcd` | gildle 경로 탐색 자체 구현·합성 하네스·루프 API |
| `3c260cd` · `e033a47` | v4 데이터 src 보존/int화·노트북 정규식 |
| (다음) | 모델 B 앙상블·A 파이프라인·루프 길이 보정 |

푸시는 하지 않았다(사용자 요청 시).
