# 1. Python이 설치된 기본 환경을 가져옵니다.
# 태그만 쓰면 원본이 갱신될 때 전체 레이어가 다시 빌드·전송돼 11-05 배포가 40분 제한에 걸렸다. 올릴 때 digest를 직접 바꾼다.
FROM python:3.13-slim@sha256:09a17cad02668ae61ece136b4fd36ac3849e14f670ebedb637ea3e15580525bc

# 2. 도커 내부에서 작업할 폴더 위치를 지정합니다.
WORKDIR /suvisdev

# 2-1. LightGBM(OpenMP)과 OpenCV(GUI 관련 공유 라이브러리)가 런타임에 요구하는 패키지를 설치합니다.
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgomp1 \
    libgl1 \
    libglib2.0-0 \
    libxcb1 \
    libxext6 \
    libsm6 \
    libxrender1 \
    && rm -rf /var/lib/apt/lists/*

# 3. 라이브러리 설치를 위해 패키지 파일을 먼저 복사합니다.
COPY requirements.txt .

# 4. 백엔드에 필요한 라이브러리들을 설치합니다.
#    torch 3종은 CPU 휠로 바꿔 설치한다 — 노트북 backend 파드엔 GPU 런타임이 없어
#    (`k8s/backend.yaml`에 nvidia 설정 없음, 파드 안 `torch.cuda.is_available()`=False)
#    cu126 휠 + nvidia-* 라이브러리 9GB가 전부 죽은 무게였다(2026-09-28, 이미지 14.9GB).
#    requirements.txt는 데스크톱 `.venv`(학습·GPU 테스트)용 cu126 핀을 그대로 유지한다.
RUN sed -e 's#whl/cu126#whl/cpu#' -e 's/+cu126/+cpu/' requirements.txt > /tmp/requirements-cpu.txt \
    && pip install --no-cache-dir --timeout 120 --retries 5 -r /tmp/requirements-cpu.txt \
    && rm /tmp/requirements-cpu.txt

# 4-1. matplotlib 폰트 캐시를 빌드 때 만들어 둔다. 없으면 새 컨테이너가 뜰 때마다 부팅 중에 다시 만든다
#      (집컴 로그 `generated new fontManager`). 시간 단축은 거의 없다 — 11-05 집컴 실측에서 서버 시작 직전 구간이
#      1분 51초 → 1분 47초. 집컴 기동이 느린 건 HDD 에서 라이브러리를 읽는 6분 탓이다(k8s/failover/README.md).
#      캐시 위치를 HOME 과 상관없게 고정한다(/root/.cache 아래에는 hf-cache hostPath 가 붙는다).
ENV MPLCONFIGDIR=/opt/matplotlib
RUN python -c "import matplotlib.font_manager"

# 5. 내 컴퓨터의 suvisdev 폴더 안 소스코드를 도커 컴퓨터로 전부 복사합니다.
COPY . .

# 6. 도커가 실행될 때 FastAPI를 8000포트로 실행합니다.
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
