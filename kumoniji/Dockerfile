# 웹 앱은 deploy.sh가 노트북에서 먼저 빌드한다(app/build/web) — 공개 Flutter 이미지에 쓰는 버전(3.47)이 없어서.
FROM python:3.13-slim
WORKDIR /srv
COPY server/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY server/kumoniji ./kumoniji
COPY app/build/web ./web
USER 10001
CMD ["uvicorn", "kumoniji.api:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers", "--forwarded-allow-ips", "*", "--ws-max-size", "4096"]
