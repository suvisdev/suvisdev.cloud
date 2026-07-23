# 07. 감정 분석 에이전트 — "Echo"

> **에이전트 이름 추천**: **Echo** (반향 — 텍스트에 담긴 감정을 되울려준다)
> 파일명: `sentiment_analysis_interactor.py`
> **원논문**: Transformer → **최신 대체**: RoBERTa/KLUE-RoBERTa(분류) 또는 EXAONE-3.5-2.4B-Instruct(생성형) + **QLoRA**
> **공통 규약(00_COMMON_conventions.md)을 먼저 읽어라.**
> ⭐ **이 태스크가 QLoRA의 정석 대상이다.**
> **사용자 결정(2026-07-22)**: 생성형 모델은 Qwen 대신 **EXAONE-3.5-2.4B-Instruct**로 고정. 이미 온프레미스 production(mova 채팅)이 EXAONE 2.4B로 마이그레이션 완료됐고, H1에서 QLoRA 적재·forward pass까지 실측 확인됨(아래 참고).

---

## 1. 모델 선택 근거 ⭐ QLoRA가 가장 잘 맞는 태스크

| 후보 | 아키텍처 | QLoRA | 3050 8GB | 추천도 |
|------|---------|-------|----------|--------|
| 원논문 Transformer | 트랜스포머 | ✅ | ✅ | 기준 |
| **KLUE-RoBERTa-base** | 인코더 트랜스포머 | ✅ LoRA(양자화 불필요할만큼 작음) | ✅✅ | ⭐ 한국어 분류 |
| **EXAONE-3.5-2.4B-Instruct + QLoRA** | 디코더 트랜스포머 | ✅ **QLoRA 정석** | ✅ (H1 실측: 4bit 로드 2158MB + LoRA 8MB, forward pass 후 총 2180MB, free 4.25GB) | ⭐ 생성형/설명형 감정분석 — **확정** |

**결정 가이드**:
- **단순 분류(긍/부정/중립 등 라벨)** → KLUE-RoBERTa + LoRA (가볍고 정확, 한국어면 KLUE)
- **감정 + 이유 설명, 다중 감정, 대화형** → **EXAONE-3.5-2.4B-Instruct + QLoRA** (4bit + LoRA, 8GB에 여유 있게 들어감)
- 온프레미스 production(mova 채팅)이 이미 EXAONE 2.4B라 **QLoRA 재활용 시너지** 좋음. Qwen은 더 이상 기본 후보 아님.

이 태스크는 공통 규약 그대로 **QLoRA/LoRA 1순위** 적용.

## 2. 데이터셋 준비 가이드

텍스트 + 감정 라벨. 형식이 가장 단순한 태스크.

**(A) 분류용 (RoBERTa)**
```
dataset/
  train.csv    # columns: text, label
  val.csv
```
- label: 정수(0=부정,1=중립,2=긍정) 또는 문자열
- 한국어면 KLUE-RoBERTa, 영어면 roberta-base

**(B) 생성형 (EXAONE-2.4B QLoRA)**
```
dataset/
  train.jsonl   # {"instruction": "...감정 분석...", "input": "<텍스트>", "output": "긍정 - 이유..."}
  val.jsonl
```
- instruction-tuning 형식, output에 감정+근거

**데이터 규모**:
| 방식 | 샘플 수 |
|------|---------|
| RoBERTa 분류 | 클래스당 300~1000 ✅ |
| EXAONE-2.4B QLoRA | 500~5000 instruction 쌍 ✅ |

**팁**: 공개 한국어 감정 데이터(NSMC, KOTE 등) + 도메인 소량 혼합 권장. 클래스 균형 맞추기.

## 3. Harness 단계

- **H0**: `transformers`, `peft`, `bitsandbytes`, `datasets`, `trl`(생성형 시) 설치. 모델 방식 확정.
- **H1**: VRAM 실측. ✅ **완료(2026-07-22)** — EXAONE-3.5-2.4B-Instruct 4bit(nf4) 로드 2158MB + LoRA(r=8, q/v_proj) 8MB, forward pass 후 총 2180MB 할당, free 4.25GB. 상세: 아래 "H1 완료 기록" 참고.
  - RoBERTa-base LoRA: 여유로움(batch 16~32)
  - EXAONE-2.4B QLoRA(4bit): 8GB에 여유 있게 들어감 (H1 실측), batch 1~4 + grad accum 예상
- **H2**: CSV/JSONL 검증, 라벨 분포 확인, 토크나이저 길이 설정. ✅ **완료(2026-07-22)** — 아래 "6. H2 완료 기록" 참고.
- **H3**: 파인튜닝. ✅ **완료(2026-07-22)** — 아래 "7. H3 완료 기록" 참고.
  - RoBERTa: LoRA, metric F1/accuracy
  - EXAONE-2.4B: **QLoRA(4bit nf4 + LoRA)**, 수동 학습 루프(SFTTrainer 미사용, 이유는 아래)
  - **어댑터 저장** → `apps/ontology/runs/echo_sentiment/adapter`
- **H4**: 추론 어댑터 — `SentimentPort.analyze(text) -> SentimentResult` (label, score, (생성형)reason). ✅ **완료(2026-07-22)** — 아래 "8. H4 완료 기록" 참고.
- **H5**: MCP tool. ✅ **완료(2026-07-23)** — 아래 "9. H5 완료 기록" 참고.
  ```python
  @mcp.tool()
  async def analyze_sentiment(text: str) -> dict:
      """텍스트의 감정을 분석해 극성(긍정/부정/중립)과 신뢰도를 반환한다.
      리뷰·댓글·문장의 감정을 물을 때 사용.
      (생성형)감정 판단 근거도 함께 제공."""
  ```
- **H6**: 시스템 프롬프트
  ```
  너는 감정 분석 에이전트 Echo다.
  - 텍스트 감정을 물으면 analyze_sentiment를 사용한다.
  - 극성과 함께 신뢰도를 제시하고, 애매하면 중립/혼합으로 표시한다.
  - 여러 문장이면 문장별 감정도 분해해 요약한다.
  ```

## 4. Gate 요약
- H1: VRAM + (QLoRA면 4bit 로드 확인) batch 상한
- H2: 라벨 분포 + 토큰 길이 확정
- H3: val F1/accuracy 로그 + 어댑터 저장
- H4: 포트 통해 SentimentResult 반환
- H5: tool 호출 성공
- H6: 텍스트 입력 → 감정+근거 응답

## 5. H1 완료 기록 (2026-07-22, ssu 서버)

**블로커였던 것**: `LGAI-EXAONE/EXAONE-3.5-2.4B-Instruct`의 `trust_remote_code` custom modeling(`modeling_exaone.py`)이 HF Hub에서 최근 업데이트되면서 `transformers.masking_utils.create_causal_mask()`를 `input_embeds=`/`cache_position=` 키워드로 호출하는데, 실제 설치된 `transformers`(4.43도, 최신 5.14.1도 둘 다) 시그니처와 어긋나 있었음. 즉 원인이 하나가 아니라 **모델 repo의 remote code 버전과 transformers 버전이 서로 다른 시점 기준이라 항상 어긋나는 상태**.

**해결**: 버전 다운그레이드가 아니라 **`create_causal_mask` 호출부를 transformers 최신 시그니처(`inputs_embeds`, `cache_position` 없음)로 맞춰주는 얇은 compat 몽키패치**를 `_tmp_h1_exaone_vram_check.py` 최상단에 추가. `get/set_input_embeddings` 패치와 동일한 패턴.

**재현 환경**: 전용 venv(`uv venv`) — `torch==2.13.0+cu126`(`--index-url https://download.pytorch.org/whl/cu126`로 명시 고정 필요, 안 그러면 cu130 빌드가 잡혀 이 서버 드라이버(12.6)와 안 맞아 `cuda available: False`가 됨) + 최신 `transformers`/`peft`/`bitsandbytes`/`accelerate`(구버전 4.43 조합은 위 이유로 오히려 더 일찍 깨짐 — config 로드 단계에서 `RopeParameters` import 실패).

**실측 결과**: 4bit(nf4) 로드 델타 2158MB, LoRA(r=8, q/v_proj) 델타 8MB, forward pass 후 총 할당 2180.1MB, free 4.25GB(8GB 중). **8GB 예산에 여유 충분 — H1 통과.**

**주의**: 이 서버(RTX 3050 8GB)는 `lora_server`(mova 채팅, 상시)가 VRAM을 거의 다 쓰고 있어서 H1 실행 전 `systemctl --user stop lora-server`로 잠시 내렸다가 완료 후 `systemctl --user start lora-server`로 복구함. **H2 이후(학습) 작업도 VRAM이 필요하니 매번 lora_server를 잠시 내렸다 올리는 절차가 필요.**

## 6. H2 완료 기록 (2026-07-22)

**데이터셋**: NSMC(Naver Sentiment Movie Corpus, `github.com/e9t/nsmc`) — mova가 영화 앱이라 도메인이 정확히 맞음. `raw.githubusercontent.com`에서 원본 TSV 직접 다운로드(HF `datasets` 라이브러리의 `nsmc` 스크립트는 최신 `datasets`(legacy script 지원 중단)에서 로드 불가라 우회).

**사용자 결정**: output은 "감정+이유" 대신 **라벨만**("긍정"/"부정"). NSMC 원본에 근거 문장이 없어서 "이유"를 넣으려면 LLM으로 별도 생성해야 하는데(추가 시간+VRAM), 지금은 스킵하고 필요해지면 나중에 별도 라운드로.

**준비 스크립트**: `suvisdev/scripts/prepare_echo_sentiment_dataset.py` — 라벨(긍/부정)당 균형 샘플링, seed=42 고정.
**산출물**: `apps/ontology/resources/echo_sentiment_train/{train,val}.jsonl`
- train: 2000건 (긍정 1000 / 부정 1000)
- val: 400건 (긍정 200 / 부정 200)

**검증 스크립트**: `_tmp_h2_echo_dataset_check.py` (CPU만 사용, GPU 불필요 — lora_server 안 내려도 됨)
- 라벨 분포 재검증 통과
- EXAONE 토크나이저로 실제 chat-template 프롬프트 토큰 길이: min=35 mean=54.9 p50=50 p95=93 max=135 → **max_seq_length=256이면 전체 샘플 여유 있게 수용**(초과 0건)
- batch_size=4 패딩 배치 정상 반환(`input_ids`/`attention_mask` shape 일치) — **H2 Gate 통과**

**H3(파인튜닝) 전 확정해야 할 것**: max_seq_length=256, batch size(H1 VRAM 여유 4.25GB 기준 batch 4~8 + grad accum 검토 필요), 학습 epoch 수. 사용자 확인 후 진행.

## 7. H3 완료 기록 (2026-07-22)

**학습 스크립트**: `suvisdev/scripts/train_echo_sentiment.py` — max_seq_length=256, batch=4, grad_accum=4(effective=16), epochs=2, lr=2e-4. LoRA(r=8, alpha=16, q/v_proj, dropout=0.05) — H1과 동일 구성.

**TRL SFTTrainer 대신 수동 학습 루프를 쓴 이유**: trl까지 pinning하면 transformers/peft/trl 세 라이브러리 버전 호환을 동시에 맞춰야 해서 리스크가 컸고(H1에서 이미 transformers 버전 하나 맞추는 데도 여러 라운드 걸림), 이 태스크는 출력이 "긍정"/"부정" 단 2가지뿐이라 수동 루프로 충분히 단순함.

**결과**:
| 지표 | 값 |
|---|---|
| epoch 1 → 2 평균 loss | 0.7598 → 0.0712 |
| val accuracy | 87.75% (351/400) |
| val precision / recall / F1 | 0.8756 / 0.8800 / 0.8778 |
| 학습 중 최대 VRAM 할당 | 3264.3 MB |
| 어댑터 저장 위치 | `apps/ontology/runs/echo_sentiment/adapter` (`*.safetensors`는 `.gitignore` 대상이라 git에 안 올라감) |

**H3 Gate 통과** — val F1/accuracy 로그 + 어댑터 저장 완료. 학습 전후 `lora-server` 내렸다 올림(정상 확인).

## 8. H4 완료 기록 (2026-07-22)

**중요 발견 — 프로덕션 `transformers==4.47.1`과 HF 리포 최신 커밋 비호환**: H1/H3에서 쓴 임시 venv는 transformers를 최신(5.14.1)까지 올려서 compat 몽키패치로 우회했지만, 실제 백엔드(`suvisdev/requirements.txt`)는 `transformers==4.47.1`로 고정돼 있고 다른 기능(`apps/dispatch/adapter/outbound/llm/kor_unsmile_moderation_adapter.py`)이 이미 이 버전에 의존 중이라 **버전을 올릴 수 없음**(블라스트 반경 큼).

**해결 — 몽키패치 대신 모델 리비전 고정**: HF `LGAI-EXAONE/EXAONE-3.5-2.4B-Instruct` 커밋 이력을 확인해보니 `ccce25bd...`(현재 main, "Update README.md and config.json for Transformers v5")가 v5 전용으로 바뀐 지점이고, 그 이전 커밋 `e949c91dec92095908d34e6b560af77dd0c993f8`(2024-12-11)는 transformers v5 마이그레이션 이전 코드다. 이 리비전으로 `revision=` 고정하면 `transformers==4.47.1` 그대로, **몽키패치 전혀 없이** 로드·forward pass·generate 전부 정상 동작 확인(H3에서 학습한 어댑터도 그대로 얹혀서 3개 샘플 전부 정답 예측 확인).

**변경 사항**:
- `apps/ontology/adapter/outbound/resource_adapters/echo_sentiment/echo_sentiment_adapter.py` — `EchoSentimentAdapter(SentimentAnalysisPort)`. `TimmConvnextAdapter`와 동일하게 호출마다 로드→추론→언로드.
- `apps/ontology/dependencies/echo_sentiment_provider.py` — DI 프로바이더(`image_classifier_provider.py`와 동일 패턴).
- `apps/ontology/test/test_echo_sentiment_adapter.py` — `@pytest.mark.gpu`(신규 마커, `pytest.ini`에 `ollama` 마커와 동일한 방식으로 추가) 통합 테스트. **PASSED** (`transformers==4.47.1` 환경에서 실행 확인).
- `requirements.txt` — `peft==0.19.1`, `bitsandbytes==0.49.2` 추가(기존 `transformers==4.47.1` pin은 안 건드림).

**score 계산 방식**: `model.generate()`로 텍스트를 뽑는 대신, 프롬프트 다음 토큰 위치의 logit에서 "긍정"/"부정" 첫 토큰 둘만 softmax해서 신뢰도로 사용(추가 forward pass 없이 한 번의 forward로 라벨+점수 동시 계산).

**H4 Gate 통과** — 포트(`SentimentAnalysisUseCase.analyze`)를 통해 `SentimentResult` VO가 정상 반환됨.

## 9. H5 완료 기록 (2026-07-23)

`image_classifier_mcp_server.py`와 완전히 동일한 패턴 — MCP 서버는 ontology 내부 모듈에 직접 의존하지 않고 HTTP로만 호출한다(AWS 전환 대비, 00_COMMON_conventions.md 6절).

**추가한 것**:
- `apps/ontology/adapter/inbound/api/v1/sentiment_analysis_router.py` — `POST /sentiment/analyze` (`asyncio.to_thread`로 이벤트 루프 블로킹 방지, 호출당 EXAONE 로드가 수십 초 걸림)
- `apps/ontology/adapter/inbound/api/__init__.py` — `nlp_router`(prefix `/nlp`) 신설, vision/ontology와 별도로 export(Echo가 vision이 아닌 첫 NLP 태스크라 새 그룹 필요)
- `main.py` — `nlp_router`를 `/api` prefix로 include → 최종 경로 `/api/nlp/sentiment/analyze`
- `apps/ontology/adapter/inbound/mcp/sentiment_analysis_mcp_server.py` — `analyze_sentiment(text) -> dict` tool, `INFERENCE_URL` 환경변수로 base URL 설정

**GPU 검증(2026-07-23)**:
- 프로덕션 백엔드 컨테이너를 리빌드(H5 코드 반영, 어제 16:23 빌드본이라 코드 누락돼있었음)+재기동
- `systemctl --user stop lora-server`로 VRAM 확보 후 HTTP 경로 실측: `POST /api/nlp/sentiment/analyze` → `{"label":"긍정","score":0.9986}` 정상(첫 호출은 컨테이너에 HF 캐시 마운트가 없어 모델을 매번 재다운로드함 — 다운로드 117초 포함 총 42초대 응답 이후는 더 빠름, 캐시 볼륨 마운트는 별도 개선 과제로 남김)
- MCP 서버(`mcp` 클라이언트 SDK로 stdio 연결) tool 호출: `{"label":"부정","score":0.9997}` 정상 — **H5 Gate 통과**
- 검증 후 `systemctl --user start lora-server`로 프로덕션 복구 확인(`/docs` 200)

**H6로 넘어가기 전 확인**: H2 결정(라벨만, "이유" 없음)과 H4 구현(logit 기반 score, `reason`은 항상 빈 문자열)에 따라 H6 시스템 프롬프트 초안(중립/혼합 표시, 문장별 분해)은 실제 tool 반환값과 맞지 않음 — 아래 10절에서 조정.

## 10. H6 완료 기록 (2026-07-23)

**시스템 프롬프트 조정 이유**: 위 9절에서 확인했듯 Echo는 긍정/부정 2-클래스만 학습됐고(H2, NSMC에 중립 라벨 없음) `reason`은 생성하지 않는다(H4, 추가 forward pass 없이 logit만 비교). 원안의 "중립/혼합 표시", "문장별 감정 분해" 규칙을 그대로 시스템 프롬프트에 넣으면 tool이 뒷받침 못하는 응답을 LLM이 지어내게 되므로, 실제 반환값(극성+신뢰도)만 자연어로 요약하는 규칙으로 조정했다. tool 호출 오케스트레이션은 `vision_genre_agent.py`와 동일 패턴(소형 모델은 tool_calls가 불안정해 결정적 규칙으로 tool 호출, LLM은 요약만 담당)이되, 요약 LLM은 문서 상단 사용자 결정(생성형 모델은 EXAONE-3.5-2.4B로 고정)에 맞춰 `exaone3.5:2.4b`를 사용(vision_genre_agent.py는 그 결정 이전에 작성되어 qwen2.5:1.5b를 쓰고 있으나 이번 범위 밖이라 손대지 않음).

**추가한 것**: `apps/ontology/adapter/inbound/mcp/sentiment_echo_agent.py` — `answer_sentiment_question(text) -> str`. `analyze_sentiment` API 호출 → Ollama(`exaone3.5:2.4b`)가 시스템 프롬프트 규칙에 따라 결과를 한국어로 요약.

**막혔던 것 — Ollama 전역 설정과 EXAONE-2.4B 비호환**: 호스트 Ollama가 `OLLAMA_KV_CACHE_TYPE=q8_0`(systemd Environment)로 고정돼 있었는데, 이 양자화 블록 크기(32)가 EXAONE-2.4B의 head dimension(80)과 나눠떨어지지 않아 `exaone3.5:2.4b` 로드 자체가 실패(`exaone3.5:7.8b`는 같은 설정에서 정상 — head dim이 달라 우연히 호환). **해결**: `/etc/systemd/system/ollama.service`에서 `OLLAMA_KV_CACHE_TYPE=q8_0` 라인 제거(사용자가 직접 sudo로 실행) 후 `daemon-reload`+재기동 — 캐시 양자화 없이 기본값으로 동작, `exaone3.5:2.4b` 정상 로드 확인. 이 설정은 Ollama를 쓰는 다른 기능(embedding adapter, hub_rag, semantic_router 등)에도 적용되는 전역 값이라 VRAM 사용량이 다소 늘 수 있음(정확도/호환성 우선 트레이드오프로 사용자 승인 하에 변경).

**막혔던 것 2 — 컨테이너에서 호스트 Ollama 접근 불가**: 백엔드 컨테이너는 `host.docker.internal`로 호스트에 붙지만, Ollama가 `127.0.0.1:11434`에만 바인딩돼 있어 컨테이너 등 외부에서는 애초에 접근 불가(호스트 전용 서비스인 걸로 보임 — 별도 손대지 않음). 그래서 이번 H6 검증은 컨테이너가 아니라 **호스트**(`.venv-exaone`)에서, `INFERENCE_URL`은 백엔드 컨테이너의 내부 IP(`172.20.0.7:8000`)로 직접 지정해 실행함(백엔드는 host 포트가 노출돼 있지 않음, 9절 참고).

**검증**: `lora-server` 잠시 내리고 호스트에서 실행 — 입력 "연기도 별로고 스토리도 지루했다. 시간 아까움." → `analyze_sentiment` 결과(부정, 0.9997) 기반으로 EXAONE-2.4B가 자연어 응답 생성 성공("매우 부정적인 의견", "신뢰도 100%" 등 반영). 검증 후 `lora-server` 복구 확인(`/docs` 200). **H6 Gate 통과**(텍스트 입력 → 감정+근거 응답, 1회 성공).

**Echo(감성분석) 에이전트 H0~H6 전체 완료.**
