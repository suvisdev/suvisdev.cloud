# 07. 감정 분석 에이전트 — "Echo"

> **에이전트 이름 추천**: **Echo** (반향 — 텍스트에 담긴 감정을 되울려준다)
> 파일명: `echo_interactor.py`
> **원논문**: Transformer → **최신 대체**: RoBERTa/KLUE-RoBERTa(분류) 또는 Qwen/EXAONE(생성형) + **QLoRA**
> **공통 규약(00_COMMON_conventions.md)을 먼저 읽어라.**
> ⭐ **이 태스크가 QLoRA의 정석 대상이다.**

---

## 1. 모델 선택 근거 ⭐ QLoRA가 가장 잘 맞는 태스크

| 후보 | 아키텍처 | QLoRA | 3050 8GB | 추천도 |
|------|---------|-------|----------|--------|
| 원논문 Transformer | 트랜스포머 | ✅ | ✅ | 기준 |
| **KLUE-RoBERTa-base** | 인코더 트랜스포머 | ✅ LoRA(양자화 불필요할만큼 작음) | ✅✅ | ⭐ 한국어 분류 |
| **Qwen2.5-1.5B/3B + QLoRA** | 디코더 트랜스포머 | ✅ **QLoRA 정석** | ✅ | ⭐ 생성형/설명형 감정분석 |

**결정 가이드**:
- **단순 분류(긍/부정/중립 등 라벨)** → KLUE-RoBERTa + LoRA (가볍고 정확, 한국어면 KLUE)
- **감정 + 이유 설명, 다중 감정, 대화형** → Qwen/EXAONE + **QLoRA** (4bit + LoRA, 8GB에 딱)
- 이미 온프레미스에 EXAONE/Qwen 있으니 **QLoRA 재활용 시너지** 좋음.

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

**(B) 생성형 (Qwen QLoRA)**
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
| Qwen QLoRA | 500~5000 instruction 쌍 ✅ |

**팁**: 공개 한국어 감정 데이터(NSMC, KOTE 등) + 도메인 소량 혼합 권장. 클래스 균형 맞추기.

## 3. Harness 단계

- **H0**: `transformers`, `peft`, `bitsandbytes`, `datasets`, `trl`(생성형 시) 설치. 모델 방식 확정.
- **H1**: VRAM 실측.
  - RoBERTa-base LoRA: 여유로움(batch 16~32)
  - Qwen 1.5B/3B QLoRA(4bit): 8GB에 들어감, batch 1~4 + grad accum
- **H2**: CSV/JSONL 검증, 라벨 분포 확인, 토크나이저 길이 설정.
- **H3**: 파인튜닝
  - RoBERTa: LoRA, metric F1/accuracy
  - Qwen: **QLoRA(4bit nf4 + LoRA)**, SFTTrainer
  - **어댑터 저장**
- **H4**: 추론 어댑터 — `SentimentPort.analyze(text) -> SentimentResult` (label, score, (생성형)reason)
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
