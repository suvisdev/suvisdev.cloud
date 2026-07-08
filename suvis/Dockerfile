# 1. Node.js가 설치된 기본 환경을 가져옵니다.
FROM node:24.15.0-slim

# 2. pnpm을 도커 컴퓨터에 설치합니다.
RUN npm install -g pnpm@9

# 3. 도커 내부에서 작업할 폴더 위치를 지정합니다.
WORKDIR /suvis

# 4. 라이브러리 설치를 위해 패키지 파일들을 먼저 복사합니다.
COPY package.json pnpm-lock.yaml*  ./

# 5. 프론트엔드에 필요한 라이브러리들을 설치합니다.
RUN pnpm install

# 6. 내 컴퓨터의 suvis 폴더 안 소스코드를 도커 컴퓨터로 전부 복사합니다.
COPY . .

# 7. 도커 네트워크에서 백엔드 서비스 이름으로 연결하기 위해 빌드 인자 설정
ARG BACKEND_URL=http://backend:8000
ENV BACKEND_URL=$BACKEND_URL

# 8. Next.js 프로젝트를 빌드(컴파일)합니다.
RUN pnpm build

# 8. 도커가 실행될 때 Next.js를 3000포트로 실행합니다.
CMD ["pnpm", "start"]
