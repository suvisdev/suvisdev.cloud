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
- **H5**: MCP tool
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
