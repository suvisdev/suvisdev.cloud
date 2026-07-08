from __future__ import annotations

import logging
import re
from typing import Any

import pandas as pd
from kiwipiepy import Kiwi

from titanic.adapter.inbound.api.schemas.crew_andrews_architect_schema import AndrewsArchitectSchema
from titanic.app.constants.intent_map import INTENT_MAP
from titanic.app.dtos.crew_andrews_architect_dto import (
    AndrewsArchitectQuery,
    AndrewsArchitectResponse,
)
from titanic.app.ports.input.crew_andrews_architect_use_case import AndrewsArchitectUseCase
from titanic.app.ports.output.crew_andrews_architect_port import AndrewsArchitectPort

logger = logging.getLogger(__name__)

_GENDER_MAP = {"여성": "female", "여자": "female", "남성": "male", "남자": "male"}
_AGE_GROUP_MAP: dict[str, tuple[int, int]] = {
    "유아": (0, 5), "아기": (0, 5),
    "어린이": (0, 12), "아이": (0, 12),
    "청소년": (12, 18), "십대": (13, 19),
    "청년": (18, 35),
    "중년": (35, 60),
    "노인": (60, 120), "어르신": (60, 120),
}
_FEATURE_NAMES = ["gender", "sib_sp", "parch", "pclass", "embarked", "Title", "AgeGroup", "FareBand"]

_HYPOTHETICAL_MARKERS = ["이라면", "라면", "살았을까", "살 수 있었을까", "살 수 있을까", "었을까", "겠어", "생존할까", "예측해줘", "예측해"]

# 귀족/직함 → (pclass, title_code, fare_band)
_NOBILITY_MAP: dict[str, tuple[int, int, int]] = {
    "귀족": (1, 5, 4), "경": (1, 5, 4), "공작": (1, 5, 4),
    "백작": (1, 5, 4), "남작": (1, 5, 4), "상류층": (1, 5, 4),
    "의사": (2, 6, 3), "박사": (2, 6, 3), "목사": (2, 6, 3),
    "평민": (3, 1, 1), "노동자": (3, 1, 1), "서민": (3, 1, 1),
}


def _age_to_group(age: int) -> int:
    if age <= 0:  return 0
    if age <= 5:  return 1
    if age <= 12: return 2
    if age <= 18: return 3
    if age <= 24: return 4
    if age <= 35: return 5
    if age <= 60: return 6
    return 7


class AndrewsArchitectInteractor(AndrewsArchitectUseCase):

    def __init__(self, repository: AndrewsArchitectPort):
        self.repository = repository
        # kiwipiepy==0.23.1 이 기능이 주입되는 곳
        self.kiwi = Kiwi()

    def analyze_intent(self, messages: str) -> dict[str, Any]:
        '''Kiwi 형태소 분석으로 프론트 질문의 의도를 파악하는 메소드

        반환값:
            intent   : 감지된 의도 (SURVIVAL_PREDICT / STATISTICS / PASSENGER_SEARCH / MODEL_TRAIN / UNKNOWN)
            keywords : 분석에 사용된 핵심 형태소 목록
            scores   : 의도별 매칭 점수
            tokens   : Kiwi가 분석한 전체 (형태소, 품사) 쌍 목록
        '''
        tokens = self.kiwi.tokenize(messages)
        keywords = [t.form for t in tokens if t.tag.startswith(("NN", "VV", "VA", "XR"))]

        scores: dict[str, int] = {intent: 0 for intent in INTENT_MAP}
        for keyword in keywords:
            for intent, kw_set in INTENT_MAP.items():
                if keyword in kw_set:
                    scores[intent] += 1

        best_intent = max(scores, key=lambda k: scores[k])
        intent = best_intent if scores[best_intent] > 0 else "UNKNOWN"

        logger.info(
            f"[AndrewsArchitectInteractor] analyze_intent | messages={messages!r} "
            f"intent={intent} scores={scores}"
        )
        return {
            "intent": intent,
            "keywords": keywords,
            "scores": scores,
            "tokens": [(t.form, str(t.tag)) for t in tokens],
        }

    def generate_reply(self, question: str, ml_context: dict) -> str:
        '''ML 예측 결과를 받아 Kiwi entity 추출 기반으로 응답 문자열을 반환'''
        analysis   = self.analyze_intent(question)
        intent     = analysis["intent"]

        predictions: list[float] = ml_context.get("predictions", [])
        test_meta: pd.DataFrame | None = ml_context.get("test_meta")
        best_model: str   = ml_context.get("best_model", "unknown")
        accuracy: float   = ml_context.get("accuracy", 0.0)
        n_train: int      = ml_context.get("n_train", 0)
        n_test            = len(predictions)
        n_sur_all         = sum(1 for p in predictions if p >= 0.5)
        rate_all          = n_sur_all / n_test if n_test else 0.0

        def predict_subset(mask: pd.Series) -> tuple[int, int, float]:
            idx   = mask[mask].index.tolist()
            preds = [predictions[i] for i in idx if i < n_test]
            n     = len(preds)
            n_sur = sum(1 for p in preds if p >= 0.5)
            return n, n_sur, (n_sur / n if n else 0.0)

        # ── entity 추출 ───────────────────────────────────────────────
        gender_kw        = next((k for k in _GENDER_MAP if k in question), None)
        age_group_kw     = next((k for k in _AGE_GROUP_MAP if k in question), None)
        age_exact_match  = re.search(r"(\d+)\s*(?:세|살)", question)
        age_decade_match = re.search(r"(\d+)대", question)
        pclass_match     = re.search(r"([1-3])등석", question)

        is_total        = any(w in question for w in ["탑승객", "총 몇", "몇명이야", "몇 명이야", "인원", "총인원", "전체"])
        is_avg_age      = any(w in question for w in ["평균 나이", "평균나이", "나이 평균", "평균 연령", "몇살"])
        is_class_stat   = "등급" in question or ("통계" in question and not gender_kw and not age_exact_match)
        is_captain      = "선장" in question
        is_important    = any(w in question for w in ["중요", "영향", "핵심", "결정", "요인", "피처"])
        is_hypothetical = any(m in question for m in _HYPOTHETICAL_MARKERS)

        # ── 가정형 질문 — ML 모델로 직접 예측 ───────────────────────
        if is_hypothetical and (age_exact_match or gender_kw or pclass_match or any(k in question for k in _NOBILITY_MAP)):
            return self._predict_hypothetical(question, ml_context, age_exact_match, gender_kw, pclass_match)

        # ── 특수 키워드 응답 ──────────────────────────────────────────
        if is_captain:
            return (
                "에드워드 존 스미스 선장은 타이타닉과 운명을 함께했습니다. "
                "승객 탈출을 지휘한 뒤 배와 함께 침몰해 생존하지 못했습니다. "
                f"({best_model} 모델 기준 미확인 승객 전체 생존 예측률 {rate_all:.1%})"
            )

        if is_total:
            return (
                f"데이터셋 기준 총 {n_train + n_test}명 탑승 "
                f"(생존여부 확인 {n_train}명 + 미확인 {n_test}명). "
                f"미확인 승객 중 {best_model} 모델이 {n_sur_all}명({rate_all:.1%}) 생존 예측."
            )

        if is_important:
            return self._feature_importance_reply(ml_context, best_model)

        # train_set: 실제 생존 기록이 있는 891명 데이터
        train_df: pd.DataFrame | None = ml_context.get("train_set")

        if is_avg_age and train_df is not None:
            avg = pd.to_numeric(train_df["age"], errors="coerce").dropna().mean()
            return f"실제 탑승객 {n_train}명의 평균 나이는 {avg:.1f}세입니다."

        # ── 조건 조합 응답 — train_set 실제 생존율 기반 ──────────────
        if train_df is not None and (age_exact_match or age_decade_match or age_group_kw or gender_kw or pclass_match):
            df         = train_df.copy()
            df["age"]  = pd.to_numeric(df["age"], errors="coerce")
            df["survived"] = pd.to_numeric(df["survived"], errors="coerce")
            df["pclass"]   = pd.to_numeric(df["pclass"], errors="coerce")
            mask       = pd.Series([True] * len(df), index=df.index)
            conditions: list[str] = []

            if age_exact_match:
                age  = int(age_exact_match.group(1))
                mask &= df["age"] == age
                conditions.append(f"{age}세")
            elif age_decade_match:
                age_start = int(age_decade_match.group(1))
                mask &= (df["age"] >= age_start) & (df["age"] < age_start + 10)
                conditions.append(f"{age_start}대")
            elif age_group_kw:
                start, end = _AGE_GROUP_MAP[age_group_kw]
                mask &= (df["age"] >= start) & (df["age"] < end)
                conditions.append(age_group_kw)

            if gender_kw:
                mask &= df["gender"] == _GENDER_MAP[gender_kw]
                conditions.append(gender_kw)

            if pclass_match:
                cls  = int(pclass_match.group(1))
                mask &= df["pclass"] == cls
                conditions.append(f"{cls}등석")

            subset = df[mask]
            n      = len(subset)
            n_sur  = int(subset["survived"].sum())
            rate   = n_sur / n if n else 0.0
            desc   = " ".join(conditions)

            if n == 0:
                return f"'{desc}' 조건에 맞는 탑승객 데이터가 없습니다."
            verdict = "생존 가능성이 높습니다" if rate >= 0.5 else "생존 가능성이 낮습니다"
            return (
                f"실제 데이터 기준 {desc} 탑승객 {n}명 중 {n_sur}명({rate:.1%}) 생존.\n"
                f"→ {verdict}."
            )

        if is_class_stat and train_df is not None:
            df = train_df.copy()
            df["survived"] = pd.to_numeric(df["survived"], errors="coerce")
            df["pclass"]   = pd.to_numeric(df["pclass"], errors="coerce")
            lines = []
            for cls in sorted(df["pclass"].dropna().unique()):
                subset = df[df["pclass"] == cls]
                n      = len(subset)
                n_sur  = int(subset["survived"].sum())
                rate   = n_sur / n if n else 0.0
                lines.append(f"{int(cls)}등석({n_sur}/{n}명 {rate:.1%})")
            return (
                f"실제 데이터 기준 등급별 생존율: {', '.join(lines)}. "
                f"전체 {n_train}명 중 {int(df['survived'].sum())}명({df['survived'].mean():.1%}) 생존."
            )

        # ── intent 기반 응답 ─────────────────────────────────────────
        if intent == "TITANIC_FACTS":
            return (
                f"1912년 4월 15일 빙산 충돌로 침몰. "
                f"{best_model} 모델이 미확인 승객 {n_test}명 중 "
                f"{n_sur_all}명({rate_all:.1%}) 생존을 예측합니다."
            )

        if intent == "SURVIVAL_PREDICT" and train_df is not None:
            df = train_df.copy()
            df["survived"] = pd.to_numeric(df["survived"], errors="coerce")
            female = df[df["gender"] == "female"]
            male   = df[df["gender"] == "male"]
            f_rate = female["survived"].mean()
            m_rate = male["survived"].mean()
            total_rate = df["survived"].mean()
            return (
                f"실제 데이터({n_train}명) 기준 생존율 {total_rate:.1%}. "
                f"여성 {f_rate:.1%} / 남성 {m_rate:.1%}."
            )

        if intent == "STATISTICS" and train_df is not None:
            df = train_df.copy()
            df["survived"] = pd.to_numeric(df["survived"], errors="coerce")
            df["pclass"]   = pd.to_numeric(df["pclass"], errors="coerce")
            lines = []
            for cls in sorted(df["pclass"].dropna().unique()):
                subset = df[df["pclass"] == cls]
                n      = len(subset)
                n_sur  = int(subset["survived"].sum())
                rate   = n_sur / n if n else 0.0
                lines.append(f"{int(cls)}등석({n_sur}/{n}명 {rate:.1%})")
            return (
                f"실제 데이터 기준 등급별 생존율: {', '.join(lines)}."
            )

        if intent == "MODEL_TRAIN":
            trained = ml_context.get("trained_models", [])
            return (
                f"총 {len(trained)}개 모델 훈련 완료. "
                f"최고 성능: {best_model} (정확도 {accuracy:.1%})"
            )

        return (
            f"{best_model} 모델 기준 미확인 승객 {n_test}명 중 "
            f"{n_sur_all}명({rate_all:.1%}) 생존 예측. 정확도 {accuracy:.1%}."
        )

    def _predict_hypothetical(self, question: str, ml_context: dict, age_match, gender_kw, pclass_match) -> str:
        best_model = ml_context.get("best_model", "unknown")
        trained_strategies = ml_context.get("trained_strategies", {})
        strategy  = trained_strategies.get(best_model)
        estimator = getattr(strategy, "_estimator", None)
        if estimator is None:
            return "현재 모델로는 가상 예측이 불가합니다."

        # ── 피처 추출 ─────────────────────────────────────────────────
        gender   = 0  # male default
        pclass   = 3
        title    = 1  # Mr default
        fare_band = 1
        age      = 30
        sib_sp   = 0
        parch    = 0
        embarked = 1  # S default

        if gender_kw:
            gender = 0 if _GENDER_MAP[gender_kw] == "male" else 1

        if age_match:
            age = int(age_match.group(1))

        # 귀족/직함 키워드 → pclass, title, fare_band 결정
        nobility_kw = next((k for k in _NOBILITY_MAP if k in question), None)
        if nobility_kw:
            pclass, title, fare_band = _NOBILITY_MAP[nobility_kw]
        elif pclass_match:
            pclass = int(pclass_match.group(1))
            fare_band = {1: 4, 2: 2, 3: 1}.get(pclass, 1)

        # title 보정: 명시적 귀족 없을 때 성별·나이로 결정
        if not nobility_kw:
            if gender == 1:
                title = 3 if age >= 18 else 2  # Mrs / Miss
            elif age <= 12:
                title = 4  # Master

        age_group = _age_to_group(age)

        feature_vector = [[gender, sib_sp, parch, pclass, embarked, title, age_group, fare_band]]

        try:
            proba = estimator.predict_proba(feature_vector)[0][1]
        except Exception as e:
            logger.warning(f"[Andrews] 가상 예측 실패: {e}")
            return "가상 예측 중 오류가 발생했습니다."

        # ── 응답 구성 ─────────────────────────────────────────────────
        desc_parts = []
        if age_match:       desc_parts.append(f"{age}세")
        if gender_kw:       desc_parts.append(gender_kw)
        if nobility_kw:     desc_parts.append(nobility_kw)
        elif pclass_match:  desc_parts.append(f"{pclass}등석")
        desc = " ".join(desc_parts) if desc_parts else "해당 조건의 승객"

        verdict = "생존했을 가능성이 높습니다" if proba >= 0.5 else "생존하지 못했을 가능성이 높습니다"
        return (
            f"{desc} 승객의 ML 예측 생존 확률: {proba:.1%}\n"
            f"→ {verdict}. ({best_model} 기준)"
        )

    def _feature_importance_reply(self, ml_context: dict, best_model: str) -> str:
        trained_strategies = ml_context.get("trained_strategies", {})
        strategy  = trained_strategies.get(best_model)
        estimator = getattr(strategy, "_estimator", None)

        if estimator is not None and hasattr(estimator, "feature_importances_"):
            importances = estimator.feature_importances_.tolist()
            if len(importances) == len(_FEATURE_NAMES):
                ranked = sorted(zip(_FEATURE_NAMES, importances, strict=False), key=lambda x: x[1], reverse=True)
                lines  = [f"{i+1}. {n}({v:.3f})" for i, (n, v) in enumerate(ranked[:5])]
                return f"[{best_model} 모델 기준 실제 피처 중요도]\n" + "\n".join(lines)

        return (
            "[상관계수 기준 피처 중요도]\n"
            "1. gender(0.54)  2. Title(0.37)  3. pclass(-0.36)\n"
            "4. FareBand(0.32)  5. cabin(0.29)"
        )

    async def introduce_myself(self, schema: AndrewsArchitectSchema) -> AndrewsArchitectResponse:
        '''앤드류 설계자의 자기소개 인터렉트'''
        return await self.repository.introduce_myself(AndrewsArchitectQuery(
            id=schema.id,
            name=schema.name,
        ))
