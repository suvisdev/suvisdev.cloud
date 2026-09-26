---
title: 진수택 개발자 프로필
---

<!-- 홈 AI 채팅(/portfolio/chat) 근거용 공개 프로필. 사이트 /resume 공개 페이지에서 옮겼고,
     전화번호·이메일 같은 연락처는 의도적으로 넣지 않는다(2026-09-27 사용자 결정). -->

# 진수택 개발자 프로필

## Suvisdev라는 이름과 AI 비서

Suvisdev(수비스데브)는 진수택의 개발자 활동명이자 포트폴리오 사이트 이름이고, 이 사이트의 AI 비서 이름이기도 합니다.
이름의 유래: 진수택의 이름에서 '수'를, 영화 아이언맨에 나오는 토니 스타크의 AI 비서 자비스(JARVIS)에서 '비스'를 따서
'수비스(Suvis)'를 만들었고, 개발자(developer)를 뜻하는 'dev'를 붙였습니다. 홈 화면의 AI 비서 Suvisdev는 이 사이트의
공개 자료를 근거로 진수택과 그가 만든 앱(Mova, Gildle, ARDA)에 대해 답합니다.

## 소개

이름은 진수택이고, 풀스택 개발자입니다. 좌우명은 "코드로 문제를 해결하는 개발자"입니다.
AI 영화 추천(Mova), 반려견 산책 경로(Gildle), 모바일 앱(susu)까지 하나의 모듈러 모놀리식
아키텍처 위에서 기획부터 배포까지 전 과정을 개인 프로젝트로 수행했습니다.
LoRA 파인튜닝과 Gemini API를 활용한 AI 파이프라인, Clean Architecture 기반 FastAPI 백엔드,
Next.js + Flutter 멀티플랫폼 프론트엔드를 설계·구현하고 직접 운영하고 있습니다.
포트폴리오 사이트는 suvisdev.cloud, 개발 블로그는 jk.suvisdev.cloud, GitHub 계정은 suvisdev입니다.
연락은 사이트의 Contact 페이지를 통해 할 수 있습니다.

주요 수치: 개발 기간 10주, 백엔드 테스트 550개 이상, Gildle 보행 그래프 233,964 edges.

## 학력·교육

진수택의 학력과 교육 이력은 다음과 같습니다.

- 대학: 2009년 3월부터 2015년까지 경상대학교 건축공학과에 재학했고 졸업하지 않고 자퇴했습니다.
  전공은 건축공학이며, 이후 독학과 실무 프로젝트로 소프트웨어 개발자로 전향했습니다.
- 교육 과정: 2026년 4월부터 2026년 10월까지 하이미디어 생성형 AI 과정을 수료 중입니다(팀 SEUK 소속).
  이 과정에서 AI 모델 운영을 위한 하네스 시스템 설계와 AI 서비스 구현을 다루며, Python · FastAPI ·
  Next.js · Flutter · AI/ML 파이프라인 구축을 실습했습니다. 팀 프로젝트로 AI 채용 도우미 ARDA를 만들었습니다.
- 자격증·수상 정보는 이 자료에 없습니다.

## 프로젝트

- **Mova** — AI 영화 추천 플랫폼. EXAONE-3.5-2.4B LoRA 파인튜닝 모델과 Gemini 듀얼 백엔드로 개인화
  추천을 하고, AI 리뷰 자동 생성, 박스오피스 랭킹, 영화 AI 챗봇을 제공합니다. 기술: FastAPI, Next.js,
  EXAONE LoRA, Gemini, PostgreSQL, pgvector. 주소: suvisdev.cloud/mova
- **Gildle** — 반려견 산책 경로 추천. OpenStreetMap 기반 233,964 edges 보행 그래프에 나무 그늘·결빙 위험·
  반려견 친화라는 3축 환경 점수를 매겨 최적 경로를 찾습니다. 기술: FastAPI, OSM/osmnx, Leaflet, Next.js,
  Overpass API. 주소: suvisdev.cloud/gildle
- **suvisdev.cloud** — 모듈러 모놀리식 풀스택 플랫폼. Clean Architecture와 Star Topology(Hub-Spoke)로
  여러 앱을 한 백엔드에 통합했고, 소셜 로그인(Google·Kakao·Naver), RBAC 어드민, 방문자 통계를 갖췄습니다.
  기술: FastAPI, Next.js, Flutter, Docker, Kubernetes(k3s), Cloudflare Tunnel, Vercel.
- **ARDA** — 팀 SEUK의 AI 채용 도우미(팀 프로젝트). 주소: seuk.suvisdev.cloud

## 기술 스택

- 언어: Python, TypeScript, Dart
- AI · ML: EXAONE (LoRA/QLoRA), Gemini API, LangChain, Hugging Face Transformers, PEFT · AWQ, llama.cpp GGUF, pgvector
- 백엔드: FastAPI, SQLAlchemy, Alembic, PostgreSQL, Redis, JWT · OAuth 2.0
- 프론트엔드: Next.js (App Router), React 19, Tailwind CSS, shadcn/ui, Leaflet
- 모바일: Flutter, Kakao SDK, Dio
- 인프라 · DevOps: Docker, Kubernetes(k3s), AWS EC2 · S3, Cloudflare Tunnel, nginx, GitHub Actions, Vercel
- 데이터: OSM (osmnx), TMDB API, KOFIC API, Overpass API, KOBIS
