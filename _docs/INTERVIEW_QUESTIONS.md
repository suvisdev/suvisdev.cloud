# 데일리 인터뷰 질문지 — 작업 내용 학습·면접 대비

그날 변경·작업한 내용을 **사용자가 스스로 설명할 수 있는지** 확인하는 문답.
세션 마무리 때 그날 작업으로 질문을 추가한다(최신 날짜가 맨 위).
답은 `<details>` 안에 — **먼저 소리 내어 답해 보고** 펼쳐서 대조할 것.
질문 수는 하루 5~10개, "무엇을"보다 **"왜 그렇게"**를 묻는다.

---

## 2026-09-07

### 1. 단일 노드인데 쿠버네티스로 전환하면 운영상 얻는 게 거의 없다고 결론 내렸다. 그런데도 전환한 이유와, 그 판단이 뒤집히는 조건은?

<details><summary>답 확인</summary>

k8s의 핵심 가치(스케줄링·자가 치유·롤링 업데이트·오토스케일)는 노드가 여러
대일 때 나온다. 단일 노드에선 compose 대비 운영 이득이 거의 없고 RAM
오버헤드만 늘어난다. 그래도 전환한 건 **학습·이력서 가치**라는 별도 목적이
있어서다 — 목적이 다르면 같은 기술의 채택 결론도 달라진다. 판단이 뒤집히는
조건: 노드가 2대 이상이 되거나(데스크톱+노트북 클러스터링), 무중단 배포가
실제 요구사항이 될 때.
</details>

### 2. 서브도메인 분리(mova.suvisdev.cloud 등)는 왜 k8s 전환과 무관하다고 봤나?

<details><summary>답 확인</summary>

서브도메인은 **URL 레이어**의 문제(OAuth redirect URI 재등록, 쿠키 도메인
분리, 세션 갈라짐)고, k8s가 다루는 건 **배포 단위**의 문제다. Ingress
라우팅 학습은 이미 있는 api./auth. 두 호스트로 충분하다. 09-03에 서빙
실익이 없어 원복했던 결정의 사유가 오케스트레이터를 바꿔도 그대로 살아
있다 — 레이어가 다른 결정은 서로를 강제하지 않는다.
</details>

### 3. Dockerfile은 남기고 docker-compose.yaml만 지웠다. 두 파일의 역할 차이는?

<details><summary>답 확인</summary>

Dockerfile은 **이미지를 만드는** 빌드 명세, compose는 **컨테이너를 띄우고
엮는** 오케스트레이션 명세다. k8s는 후자만 대체한다 — 파드가 돌릴
`suvisdev-app:latest`는 여전히 Dockerfile로 빌드한다. "도커 파일 전부
제거"라는 요구를 문자 그대로 수행하면 시스템이 돌 수 없는 이유가 이
역할 분리에 있다.
</details>

### 4. compose의 `depends_on: service_healthy`를 k8s에선 어떻게 대체했고, 왜 k8s에는 depends_on이 없나?

<details><summary>답 확인</summary>

initContainer(`until nc -z db 5432`)로 대체했다. k8s에 기동 순서 개념이
없는 건 철학 차이다 — 파드는 언제든 죽고 재스케줄될 수 있으므로 "순서
보장"이 아니라 **"의존 대상이 없어도 견디다 재시도"**가 정답이라고 본다.
initContainer는 그 재시도를 크래시 루프 대신 조용한 대기로 바꾸는 완충일
뿐, 본질적 해법은 앱의 재연결 내성이다.
</details>

### 5. db·redis 접근을 NodePort가 아니라 LoadBalancer 타입으로 만든 이유는? 클라우드도 아닌데 LoadBalancer가 동작하는 이유는?

<details><summary>답 확인</summary>

LoadBalancer는 원래 클라우드가 L4 LB를 프로비저닝해 채우는 타입인데,
k3s는 **ServiceLB(Klipper)**를 내장해 그 자리를 채운다 — svclb 데몬셋
파드가 노드(이 WSL 호스트)의 해당 포트를 직접 바인딩한다. 덕분에
alembic·psql이 compose 시절과 동일하게 `localhost:5432`로 붙는다 —
개발 UX를 바꾸지 않는 게 목적. NodePort는 30000~32767 대역이라 포트가
바뀌어 기존 도구·습관이 다 깨진다.
</details>

### 8. k3s 파드에서 호스트(WSL)의 Ollama·lora-server에 어떻게 접근하나? compose의 host.docker.internal은 왜 안 되나?

<details><summary>답 확인</summary>

host.docker.internal은 **Docker Desktop이 주입하는 매직 DNS**라 k3s엔 없다.
대신 flannel CNI의 브리지(cni0) 게이트웨이 `10.42.0.1`이 곧 노드(=이 WSL
호스트)이므로, 파드 스펙의 hostAliases로 host.docker.internal→10.42.0.1을
매핑해 기존 env 값을 안 바꾸고 해결했다. 전제 조건은 호스트 프로세스가
0.0.0.0에 바인딩돼 있을 것 — 127.0.0.1에만 물려 있으면 cni0 쪽 요청을
못 받는다.
</details>

### 6. .env를 ConfigMap이 아니라 Secret으로 넣었다. 그리고 Secret인데도 왜 커밋하면 안 되나?

<details><summary>답 확인</summary>

내용이 자격증명(DB 비밀번호·API 키·터널 토큰)이라 의미상 Secret이 맞다.
하지만 k8s Secret은 기본이 **base64 인코딩일 뿐 암호화가 아니다** —
매니페스트로 만들어 커밋하면 평문 커밋과 같다. 그래서 deploy.sh가 배포
시점에 `--from-env-file`로 생성하고, 저장소에는 .env도 Secret 매니페스트도
남기지 않는다. compose 시절 ".env는 이미지·저장소에 안 넣는다" 원칙의
k8s 버전.
</details>

### 7. cloudflared 매니페스트를 만들어 두고 replicas: 0으로 박아둔 이유는?

<details><summary>답 확인</summary>

`.env`의 TUNNEL_TOKEN은 api./auth.suvisdev.cloud **프로덕션 터널** 토큰이다.
데스크톱에서 켜는 순간 Cloudflare가 이 커넥터로도 실트래픽을 흘려
프로덕션 요청이 개발 클러스터로 들어온다. 매니페스트는 노트북 k3s 컷오버
때 재사용할 자산이라 만들어 두되, 기본값을 "안전한 꺼짐"으로 — 실수 한
번(apply)으로는 사고가 안 나고 명시적 scale-up이 있어야만 켜지는 구조다.
</details>

### 9. k3s가 `wrong number of fields (expected 6, got 7)`로 죽었다. 이 에러에서 어떻게 `/proc/mounts`를 의심했고, 재설치가 무효인 이유는?

<details><summary>답 확인</summary>

"fields"를 세는 파서는 정형 텍스트를 읽는 코드다. kubelet이 ContainerManager
기동 시 검증하는 6필드 정형 파일이 `/proc/mounts`(장치·마운트점·타입·옵션·
dump·pass)다. `awk 'NF!=6' /proc/mounts`로 실측하니 Docker Desktop WSL
통합의 `/Docker/host`(9p) 라인 하나가 7필드 — 옵션 안의
`path=C:\Program Files\...` 공백이 원인이었다(커널은 경로의 공백은 `\040`으로
이스케이프하지만 9p **옵션 문자열** 안의 공백은 그대로 둔다). 재설치가
무효인 이유: 에러의 주체가 k3s 바이너리가 아니라 **호스트의 마운트 테이블**
이라서다. 환경 원인 오류는 소프트웨어를 다시 깔아도 재현된다.
</details>

### 10. 마운트 해제를 한 번 하고 끝내지 않고 systemd drop-in의 `ExecStartPre`로 넣은 이유는? `ExecStartPre=-`의 `-`는 뭘 하나?

<details><summary>답 확인</summary>

`/Docker/host`는 Docker Desktop이 재시작할 때마다 다시 마운트한다. 한 번의
umount는 다음 부팅에서 같은 크래시 루프를 재현시키므로, "k3s가 시작되기
직전마다 자동으로 풀리는" 위치인 유닛의 `ExecStartPre`에 넣어야 구조적으로
재발이 막힌다. drop-in(`k3s.service.d/*.conf`)으로 한 이유는 본 유닛 파일은
k3s 설치 스크립트가 재설치 때 덮어쓰기 때문 — 실제로 이날 재설치가 한 번
있었고 drop-in은 살아남는다. `-` 접두사는 "이 명령이 실패해도(이미 풀려
있어도) 유닛 기동을 계속하라"는 뜻이다.
</details>

### 11. 파드가 `ErrImageNeverPull`이었다. 도커에 이미지가 분명히 있는데 왜 k3s는 못 찾고, 이 상태가 "정상 경유지"였던 이유는?

<details><summary>답 확인</summary>

도커 데몬과 k3s의 containerd는 **이미지 저장소가 완전히 분리**돼 있다.
`docker build` 결과는 도커 쪽에만 있으므로 `docker save | k3s ctr images
import`로 명시적으로 옮겨야 한다. 매니페스트가 `imagePullPolicy: Never`라
레지스트리 pull 시도 대신 "로컬에 없음" 에러가 난 것 — 이건 실패가 아니라
import가 끝나기를 기다리는 대기 상태고, kubelet이 sync 루프마다 재확인하므로
import가 끝나면 파드 재생성 없이 자동으로 기동된다.
</details>

### 12. 구 DB 데이터를 복원할 때 backend·auth를 replicas 0으로 내리고 했다. 왜 필요했고, 복원 검증은 뭘 봤나?

<details><summary>답 확인</summary>

앱이 살아 있으면 복원 도중 스키마가 절반만 생긴 DB에 쓰기·마이그레이션이
끼어들어 일관성이 깨질 수 있다. 복원은 "쓰는 사람이 없는 상태"에서 하는 게
원칙이라 컴퓨트만 잠시 내렸다(StatefulSet db는 그대로). 검증은 세 층위 —
① 스키마: 테이블 42개·`alembic_version`이 덤프와 일치, ② 데이터: groups
2행·movies 199행 실측, ③ 동작: 재기동한 backend 로그에 `UndefinedTable`
부재 + `/docs` 200. "복원 스크립트가 안 죽었다"는 검증이 아니다.
</details>

---

### 13. 데스크톱용 deploy.sh를 노트북(프로덕션)에서 그대로 돌리면 데이터는 안 지워지는데도 "사고"라고 판단했다. 무슨 일이 벌어지나?

<details><summary>답 확인</summary>

db.yaml이 무조건 apply돼 **빈** pgvector StatefulSet과 셀렉터 있는 Service `db`가
생긴다. backend 파드의 연결 문자열은 `@db:5432`라 클러스터 DNS가 그 빈 DB로
풀린다. 프로덕션 데이터는 도커 볼륨에 그대로 있지만 서비스는 빈 데이터로
응답하고, 쓰기 요청이 오면 두 DB로 갈라진다. "데이터 손실 없음"과 "서비스
정상"은 다른 문제다.
</details>

### 14. 도커 컨테이너로 남겨둔 db·redis를 k8s 파드에서 쓰려고 ExternalName Service가 아니라 "셀렉터 없는 Service + EndpointSlice"를 골랐다. 왜?

<details><summary>답 확인</summary>

ExternalName은 DNS CNAME을 돌려주는 방식이라 **호스트 이름**만 가리킬 수 있고
IP(10.42.0.1)는 못 가리킨다. 셀렉터 없는 Service는 kube-proxy가 EndpointSlice의
주소로 그대로 부하분산해 주므로 IP·포트를 직접 지정할 수 있다. 이름을
`db`/`redis`로 두면 앱 연결 문자열 수정도 없다.
</details>

### 15. hostPath 경로를 매니페스트에 하드코딩하지 않고 `__REPO_ROOT__` 플레이스홀더 + sed 치환으로 바꿨다. `DirectoryOrCreate`가 이 문제를 더 위험하게 만든 이유는?

<details><summary>답 확인</summary>

경로가 틀려도 `DirectoryOrCreate`는 에러 대신 **빈 디렉터리를 만들어** 파드를
정상 기동시킨다. 즉 gildle `scored_edges.json`이나 harvester 출력이 사라져도
`get pods`는 Running이라 배포 시점에 알아챌 수 없다. 조용한 실패가 시끄러운
실패보다 위험하다. 대안은 `Directory` 타입(없으면 기동 실패)인데, 데스크톱에서
폴더가 없을 수 있어 치환 방식을 택했다.
</details>

### 16. Cloudflare 터널의 `auth.suvisdev.cloud → http://auth:9000` 라우트는 대시보드를 안 바꿔도 k8s에서 그대로 동작한다고 봤다. 근거는? 그리고 `api → http://nginx:80`은 왜 안 되나?

<details><summary>답 확인</summary>

cloudflared 파드는 `suvisdev` 네임스페이스에서 돌고, 파드의 resolv.conf 검색
도메인이 `suvisdev.svc.cluster.local`이라 `auth`가 k8s Service `auth`로 풀린다.
도커에서는 같은 이름이 compose 서비스로 풀렸을 뿐, 이름 해석 주체만 바뀐 것.
반면 `nginx`는 k8s에 그 이름의 Service가 없어 NXDOMAIN이다. 그래서 api
라우트만 Traefik(`traefik.kube-system.svc.cluster.local:80`)으로 바꾼다.
</details>

### 17. 노트북 k3s는 `--disable servicelb`로 설치하기로 했다. 이유와, 그러면 LoadBalancer 타입 Service들은 어떻게 되나?

<details><summary>답 확인</summary>

ServiceLB(Klipper)는 노드 호스트 포트를 직접 점유한다. 노트북엔 nginx(80/443)와
도커 db·redis(5432/6379)가 이미 그 포트를 쓰고 있어 svclb 파드가 크래시 루프를
돈다. 끄면 LoadBalancer Service는 EXTERNAL-IP `<pending>`으로 남지만, 트래픽
경로가 cloudflared→Traefik→backend로 **전부 ClusterIP**라 동작에 영향이 없고
LAN 노출도 사라진다(compose 시절에도 8000/9000 포트 제거가 목표였다).
</details>

### 18. 트래픽 전환 시 "대시보드 라우트 변경 → 도커 cloudflared stop → 파드 scale 1" 순서로 수 초 단절을 감수했다. 무단절 대안은 무엇이었고 왜 기각했나?

<details><summary>답 확인</summary>

k8s에 `nginx`라는 셀렉터 없는 Service(→10.42.0.1:80, 도커 nginx)를 미리 만들면
k8s cloudflared도 기존 라우트로 도커 스택을 서빙할 수 있어, 커넥터를 먼저
둘 다 붙인 뒤 라우트를 바꾸는 식으로 단절 없이 넘어갈 수 있다. 하지만
일회성 컷오버를 위해 리소스와 절차가 하나 더 늘고, 개인 프로젝트에서 수 초
단절은 허용 범위라 과설계로 봤다. 규모가 커지면 판단이 뒤집힌다.
</details>

### 19. 컷오버 직후 api만 502이고 auth는 200이었다. 원인을 어떻게 좁혔고, 대시보드 라우트를 바꾸는 대신 ExternalName Service를 택한 이유는?

<details><summary>답 확인</summary>

cloudflared 파드 로그에 `lookup nginx on 10.43.0.10:53` 실패가 찍혔고 config
version이 전과 같아 라우트가 안 바뀐 걸 알았다. auth 라우트는 대상이 `auth`라
k8s Service로 해석돼 살아 있었으니, 문제는 "이름 해석"뿐임이 확정됐다. 해결은
k8s에 `nginx`라는 이름을 만들어 주면 되는데, 대상이 Traefik의 **호스트명**이라
ExternalName(CNAME)이 딱 맞는다(db·redis처럼 IP였다면 EndpointSlice). 대시보드
변경보다 나은 점: 매니페스트에 남아 재현 가능하고, 롤백이 도커 cloudflared
start 한 줄이며, 다른 머신에서 같은 절차를 돌려도 대시보드를 몰라도 된다.
</details>

## 2026-09-04

### 1. 서버 `.env` 키를 관리자 IAM 키로 쓰지 않고 `arda-server` 유저를 따로 만든 이유는?

<details><summary>답 확인</summary>

권한은 합집합이라 admin 유저에 축소 정책을 "추가"해도 여전히 전체 권한이다.
서버에 들어가는 키는 **서버가 뚫렸을 때 잃는 범위**를 정의한다 — admin 키면
계정 전체(개인 리소스·IAM 조작 포함), `arda-server` 키면 Arda 버킷·큐·SES
발송뿐. 최소 권한 원칙은 "동작하냐"가 아니라 **사고 시 폭발 반경**의 문제다.
같은 이유로 루트는 MFA만 걸고 보관, 콘솔 작업은 admin IAM 유저, 팀원은
ViewOnlyAccess 그룹(이력서 객체 다운로드 불가)으로 3단 분리했다.
</details>

### 2. compose가 `DB_PASSWORD`를 `backend/.env`(env_file)에서 못 읽는 이유는? mova 사고와 뭐가 같고 뭐가 달랐나?

<details><summary>답 확인</summary>

`env_file:`은 **컨테이너 안 환경변수**를 넣는 것이고, compose 파일 자체의
`${VAR}` 치환은 **compose를 실행하는 셸/프로젝트 루트 `.env`**에서만 온다 —
전혀 다른 두 단계다. 그래서 `ln -s backend/.env .env`가 필요했다. mova의
`--env-file suvisdev/.env` 누락 사고와 같은 계열이지만, mova는 빈 문자열로
**조용히** db가 재생성돼 502가 났고, Arda는 `${DB_PASSWORD:?set in .env}`
가드 덕에 **기동 자체가 시끄럽게 실패**한다. 치환 실패를 침묵 대신 오류로
만드는 `:?` 한 글자가 사고를 장애에서 즉발 진단으로 바꾼다.
</details>

### 3. 새 DB인데 왜 `alembic upgrade`를 안 돌리고 create_all + stamp로 갔나?

<details><summary>답 확인</summary>

운영 이미지는 `uv sync --no-dev`라 alembic이 아예 없다(런타임 의존이 아니라는
팀 설계). Arda는 **새 DB는 앱 기동 시 create_all이 세우고, 기존 DB의 변경만
alembic이 맡는** 이원 구조다. 단 create_all은 테이블만 만들지 트리거·권한·
컬럼 변경(0006~0008)은 못 만들므로, 그 DDL만 손 SQL로 적용하고
`alembic_version`에 stamp를 남겼다 — 팀이 09-01 운영 전환 때 쓴 방식 그대로.
stamp는 "이 상태다"라는 선언이라 실측과 다르면 차이가 영구히 숨는다는 점이
핵심 위험이다(팀도 실측 먼저 하고 stamp했다).
</details>

### 4. CD를 GitHub Actions push 방식이 아니라 서버 폴링(pull) 방식으로 만든 이유는?

<details><summary>답 확인</summary>

push 방식은 GitHub 러너가 서버에 들어와야 해서 ① SSH 22를 넓은 IP 대역에
열거나 ② SSM/OIDC IAM 배선이 필요하다. 폴링은 서버가 밖으로 fetch만 하므로
**인바운드 구멍 0, 시크릿 0, GitHub 설정 0**이고, 2분 지연은 이 규모에서
무의미하다. 스크립트는 fetch→`merge --ff-only`→build→up→health 순서인데,
build와 up을 나눈 건 빌드가 깨져도 돌던 컨테이너를 죽이지 않기 위함(팀
07-deploy의 실전 교훈). 첫 자동 실행이 서버 트리의 sed 잔재 때문에 ff-merge
거부로 멈춘 것도 배웠다 — CD가 있는 서버의 작업 트리는 항상 깨끗해야 한다.
</details>

### 5. Vercel 환경변수에서 세 번 막혔다. 각각의 원인은?

<details><summary>답 확인</summary>

① `VITE_` 접두사는 빌드 시 번들에 박히는 **공개 값**인데 Secret 타입과
의미 충돌이라 저장이 거부됐다(경고가 곧 차단 조건). ② Secret→Config 전환은
불가(Secret은 write-only)라 삭제 후 재생성해야 했다. ③ "already exists for
preview" — 앞 시도가 Preview 스코프에만 저장됐는데 목록 필터가 Production
이라 눈에 안 보였던 것. 마지막으로 환경변수는 **빌드 시점에 박히므로**
저장만으론 무효고 재배포(캐시 미사용)까지 해야 번들이 바뀐다 — 번들 파일명
해시가 같으면 반영 안 된 것이라는 판별법도 얻었다.
</details>

### 6. Team-Seuk/Arda를 바로 삭제하면 안 됐던 이유와, 삭제 가능해진 조건은?

<details><summary>답 확인</summary>

실측 결과 "새" org(Seuk-Team)가 하루 뒤처진 복사본이었고 팀은 계속 옛 org에
커밋 중이었다(오늘 블록체인 커밋 포함). 즉 삭제하면 최신 코드 유실 + CD·
Vercel 즉사. 순서를 바꿔 **동기화 먼저**(모든 브랜치 push + main은 보호 토글
해제 후 머지 커밋 푸시로 PR #2 반영) → 서버 remote 전환·CD 재검증 → Vercel
연결 확인, 그 뒤에야 삭제가 안전해진다. 저장소 이전의 일반 원칙: **소비자
(배포·CI·팀원 클론)를 전부 새 주소로 돌린 것을 검증한 뒤에 원본을 지운다.**
</details>

### 7. GPU 인스턴스를 24시간 켜두면 안 되는 근거를 숫자로 대면?

<details><summary>답 확인</summary>

기간 53일 ≈ 1,272h. g4dn.xlarge 서울 온디맨드 ~$0.65/h → 상시 가동 ~$820로
예산($400)의 2배. 백엔드 고정비 ~$50을 빼면 GPU 몫은 ~$350 = **~540h,
하루 평균 ~10h**가 상한이다. 그래서 "쓸 때만 켜기"가 운영 전제고, 사람의
기억 대신 CloudWatch 유휴 자동 중지 알람 + Budgets 50/80/100% 경보를
안전장치로 건다. 쿼터 신청값 4도 근거가 있다 — G 계열 최소 단위(g4dn.xlarge)
가 4 vCPU라 4면 정확히 1대, 작게 부를수록 자동 승인이 잘 된다.
</details>

## 2026-09-03

### 0. '식객' 무관 픽의 근본 원인은? hub 스키마를 안 바꾸고 어떻게 고쳤나?

<details><summary>답 확인</summary>

"클래식"이 시대 어휘 매핑으로 `year_max=1999`가 됐는데, **RAG 시맨틱 히트는
hub_knowledge에 연도 메타데이터가 없어 연도 하드 필터를 못 지킨다** — tail로
유입된 2003·2007년작(클래식·식객)을 LoRA가 픽했다. 수정은 hub 확장 대신
**히트의 movie_id를 movies.release_year로 재검증**(`filter_movie_ids_by_year`):
연도 조건이 있을 때만 발동, 미상(0)은 탈락. 배포 후 같은 질의가 그린 마일·
파이트 클럽·포레스트 검프로 바뀌었고 로그에 `RAG 연도 필터 8→3편`이 찍혔다.
교훈: 메타데이터가 없는 검색 경로에 하드 필터가 걸리면, 필터는 **원본
테이블 재검증**으로 강제할 수 있다.
</details>

### 0-b. 분류기 속도 개선에서 "병렬화" 대신 "결정론 지름길"을 고른 이유는?

<details><summary>답 확인</summary>

분류기 Gemini 호출(2.06s)이 병목이었는데, 분류∥(의도 추출→RAG) 투기적
병렬화는 비추천 질의에서도 Gemini 호출이 나가 쿼터를 낭비하고 "general은
추천 파이프라인을 안 탄다"는 불변식을 흔든다. 대신 "추천"·"뭐 있" 어휘가
있고 예매·평가 어휘가 없는 명백한 추천 질의만 LLM 없이 recommend로 확정
(기존 불만·메타 가드와 같은 결정론 패턴) — 분류 구간 2.06s→0ms, 쿼터도
절약, 모호한 질의는 여전히 LLM이 판정한다. 싸고 안전한 수단부터.
</details>

### 0-c. "안녕"이 500으로 터진 원인과 수정 원칙은?

<details><summary>답 확인</summary>

general 트랙은 Gemini(Mycroft)가 유일한 응답 경로인데, 쿼터 429가
HubRagError로 올라와 아무도 안 잡아서 500이 됐다(평가 하네스가 발견 —
하네스의 가치 실증). 수정: `_reply_general`에서 포착해 "잠시 후 다시"
정직 안내를 200으로 반환(대화 기록은 유지). 원칙: 추천 트랙의 폴백
체인처럼, 외부 LLM 장애는 5xx가 아니라 **정직한 강등**으로 흡수한다.
</details>

### 1. zero-rec 재실측을 컨테이너 로그가 아니라 DB로 한 이유는? 어떻게 측정했나?

<details><summary>답 확인</summary>

컨테이너가 전날 밤 배포로 재생성돼 로그 창이 거의 비어 있었다. 대신 전 기간이
쌓여 있는 `chat`(채팅 의도 로그) 테이블과 `picks`(chat_id FK) 테이블을
LEFT JOIN — "추천 계열 intent인데 picks가 없는 chat"이 zero-rec이다.
booking·general·evaluate는 픽이 없는 게 정상이라 제외해야 한다.
</details>

### 2. 재실측 결과 zero-rec 7건(13%)의 공통점은? 이 결과가 말해주는 것은?

<details><summary>답 확인</summary>

7건 전부 **이미 수정된 버그의 수정 전 발생분**(필러 4·언어 허용목록 1·구버전
후보조립 1) + 맥락 없는 후속발화 1. 즉 신규 실패 유형이 0 — 기존 zero-rec
유형은 소진됐고, 다음 품질 타깃은 zero-rec이 아니라 **무관 픽(관련성)**으로
이동했다("클래식 명작…"에 요리 영화 '식객' 픽). 오타 질의도 여전히 0건이라
엔티티 매칭 보류 근거도 재확인됐다.
</details>

### 3. "교사 데이터셋에서 스킵된 질의(형사물 등)"가 실서비스에서는 정상 동작했다. 이 차이가 왜 생기나?

<details><summary>답 확인</summary>

교사 데이터셋 스킵은 "Gemini 교사가 낸 픽이 태그 후보와 불일치(no grounded
picks)"라는 **생성 파이프라인의 그라운딩 실패**이지, 서비스의 후보 조립
실패가 아니다. 실서비스는 태그 검색(형사 태그 113건)으로 후보를 잘 만들고
LoRA가 그중에서 고르기만 하면 되므로 정상 동작한다. 스킵 수 ≠ 실사용 품질.
</details>

### 4. Arda 콘텐츠를 개인 지킬에 올렸다가 되돌렸다. 어떤 원칙 충돌이 있었고 최종 배치 기준은?

<details><summary>답 확인</summary>

팀 README는 "각자 개인 레포에 넣어라"(포트폴리오 통일 규칙)였지만, 본인
방침은 "개인 사이트엔 개인 프로젝트만". 사용자 방침이 우선 — 개인
지킬(jk)에서 revert하고 팀 문서 사이트(ats.suvisdev.cloud)의 about에
아키텍처·ERD·실서비스 화면을 반영했다. 방침은 양쪽 CLAUDE.md에 명문화.
</details>

### 5. 회귀 하네스의 판정을 "결정론 규칙만"으로 제한한 이유는?

<details><summary>답 확인</summary>

recs 유무·연도 하드 조건·금지 픽만 자동 판정한다. "픽이 얼마나 좋은가"
같은 주관 판정을 자동화하면(예: LLM 심판) 하네스 자체가 흔들리는 기준이
되고 비용도 든다. 결정론 규칙은 거짓 경보가 없어 **수정·재학습·배포마다
부담 없이 돌릴 수 있고**, 관련성 같은 soft 품질은 결과 목록을 사람이
훑는 것으로 보완한다. 실제로 첫 실행에서 하드 룰(HTTP 500)로 숨은 버그를
잡았다 — "안녕" 429→500.
</details>

### 6. 유럽 도시 키워드(paris·london…)를 "파리·런던"이 아니라 전부 "유럽" 라벨로 합친 이유는?

<details><summary>답 확인</summary>

태그 매칭이 `tags.label ILIKE %질의 토큰%`이라, 라벨은 **사용자가 실제로
치는 어휘 단위**여야 걸린다. 실측 질의는 "유럽 배경 로맨스"처럼 권역
표현이고 "파리 영화"는 관측되지 않았다 — 파리 라벨을 만들면 유럽 질의에
안 걸린다. 반대로 뉴욕은 질의에 그대로 등장해 도시 라벨을 유지했다.
사전 설계의 기준은 데이터 분류학이 아니라 **질의 어휘 실측**이다.
</details>

### 7. 재학습을 "매 변경마다"가 아니라 "배치 큐"로 바꾼 근거는? 이번 태그 확장은 왜 재학습 없이 효과가 났나?

<details><summary>답 확인</summary>

모델의 일은 "후보 중 고르기"(형식·선택 습관)이고 지식은 DB에 있다. 태그
확장은 **서빙 시점의 후보 조립**을 바꾸므로 즉시 효과가 난다 — 실제로
유럽·뉴욕 픽이 재학습 없이 교정됐다. 재학습 트리거는 ① 출력 계약 변경
② 생성 단계의 체계적 실패 ③ 데이터셋 유의미 증분뿐이고, 그 전까지 상류
변경을 큐에 쌓았다가 한 사이클(재생성→학습→GGUF→reload)로 몰아서 한다.
9/1~9/2 연속 학습은 베이스 교체라는 예외였다.
</details>

### 8. 가중치는 파일에 "어떻게" 기록되나? 어댑터가 22MB뿐인 이유는?

<details><summary>답 확인</summary>

가중치 파일(safetensors)은 "이름표 붙은 숫자 배열(텐서)"의 나열이다 —
목차(이름→모양·타입·위치) 뒤에 원시 숫자가 바이너리로 이어진다. 산수로
검증 가능: 어댑터 553만 개 × 4B(F32) ≈ 22MB, 베이스 24억 개 × 2B(fp16)
≈ 9GB, Q5 GGUF는 개당 약 5비트 ≈ 1.7GB. LoRA는 원본 24억 개를 안 건드리고
각 층 옆의 작은 보정 행렬 쌍(A: 16×2560, B: 640×16)만 학습·기록해서 작다.
개별 숫자엔 의미가 없고 습관은 전체 조합에 분산돼 있다 — 그래서 지식은
DB에 두는 구조가 유지보수에 유리하다.
</details>

### 9. 서브도메인으로 나누면 앱마다 다른 AWS 계정을 쓸 수 있나? 무엇이 묶이고 무엇이 독립인가?

<details><summary>답 확인</summary>

가능하다 — **도메인(DNS)과 클라우드 계정은 독립**이다. Cloudflare 존의
레코드가 서브도메인마다 서로 다른 곳(다른 Vercel 프로젝트, 다른 계정의
EC2)을 가리키면 되고, TLS는 각 호스트 서비스가 발급한다. 반면 묶이는
것은 **오리진 단위 브라우저 저장소** — localStorage의 JWT는 서브도메인
간 공유되지 않아 로그인 세션이 도메인별로 갈라진다. 백엔드 분리는
별개 문제로, 현 모듈러 모놀리스(users·Hub 공유)에선 YAGNI.
</details>

### 10. 배포했는데 효과가 없었다(분류기 지름길 1차 배포). 원인과 재발 방지 수칙은?

<details><summary>답 확인</summary>

커밋에 `apps/ontology` 스테이징을 빠뜨려 **변경이 커밋에 없는 채로**
파생 빌드가 나갔다 — git log는 최신인데 파일은 구버전인 상태. 발견은
"컨테이너 안 코드를 직접 grep"으로 했고(`docker exec grep -c 심볼`),
이후 배포 검증 수칙: 배포 후 재현 테스트에서 효과가 안 보이면 로그 추측
전에 **배포물에 변경이 실재하는지**부터 확인한다. 다중 디렉터리 변경은
`git status`로 스테이징 전수 확인.
</details>

### 11. 오후에 배포한 서브도메인 리라이트를 저녁에 되돌렸다. 무엇이 판단을 바꿨나?

<details><summary>답 확인</summary>

"기술적으로 되니까"와 "필요하니까"는 다르다. 개인 포트폴리오 앱에 별도
배포·별도 앱 계획이 없으면 서브도메인 서빙의 실익은 주소 모양뿐인데,
비용은 셋이나 실재했다 — localStorage JWT라 세션이 origin별로 분리되고,
백엔드 OAuth 복귀가 `FRONTEND_URL` 단일값이라 서브도메인 로그인이 apex로
새며, 같은 페이지가 두 URL로 열린다. 반면 팀 프로젝트는 배포 주체·AWS
계정이 다르니 다른 서버를 가리켜야 해서 서브도메인이 필수다. 결론은 "팀만
이사, 개인은 원복". 짧은 주소가 정말 필요하면 301 리다이렉트로 충분하다.
</details>

### 12. 계획서는 "소셜 콘솔에 서브도메인 콜백 추가"라 했는데 왜 틀렸나? 진짜 갭은?

<details><summary>답 확인</summary>

프로바이더에 등록된 redirect URI는 **백엔드** 주소(`api.suvisdev.cloud/...
callback`)라 프론트 도메인이 바뀌어도 변하지 않는다 — 콘솔 작업은 불필요.
진짜 갭은 백엔드가 로그인 완료 후 사용자를 돌려보내는 주소가 환경 변수
하나(`FRONTEND_URL`)로 고정된 것. 고치려면 프론트가 origin을 넘기고 백엔드가
화이트리스트 대조 후 state에 저장했다가 콜백 때 그 origin으로 보내야 한다.
교훈: 문서의 체크리스트를 그대로 믿지 말고 **실제 리다이렉트 체인을 코드로
따라가** 어디가 호스트에 묶여 있는지 확인할 것.
</details>

### 13. PROGRESS를 1396줄에서 178줄로 줄이면서 "완료 항목"을 통째로 지우지 않고 한 줄 인덱스로 남긴 이유는?

<details><summary>답 확인</summary>

CLAUDE.md 규칙이 "완료 항목은 상세 대신 WORK_LOG 날짜만 남긴다"이고, 재개용
문서의 역할은 "어디를 보면 되는지"를 알려주는 것이다. 상세 서술은 워크로그와
중복이라 삭제 대상이지만, 날짜+제목 한 줄은 중복이 아니라 **포인터**다.
백로그 쪽은 워크로그와 항목별로 대조해 실제 완결 근거(예: 재임베딩은 08-26
실행·09-01 2,972/2,972 확인)를 찾은 것만 뺐다 — "완결처럼 보이는" 항목을
근거 없이 지우면 재개 문서가 거짓말을 한다.
</details>

### 14. 옛 브랜치 12개 중 1개만 살렸다. "합칠 수 있는 건 다 합쳐 달라"는 요청에 왜 그렇게 답했나?

<details><summary>답 확인</summary>

세 가지 근거를 대조했다. ① `git rev-list main..branch`로 main에 없는 커밋
수, ② `git merge-tree`로 충돌 여부, ③ 구 저장소 `gh pr list --head`로 PR
이력. 4개는 main에 전부 포함(삭제만), 8개는 전부 100~300커밋 뒤처져 충돌.
그 8개 중 5개는 팀이 PR을 닫은 것이라 지금 합치면 팀 결정을 뒤집는 셈이고,
프론트 브랜치는 main의 09-02 모바일 개편이 대체했다. 살릴 만한 건 한 줄
(`create_schedule_proposal` 테스트 누락)뿐이라 rebase 후 PR #1로 올렸다.
"합칠 수 있는가"는 기술적 충돌만이 아니라 **팀이 이미 내린 판단**까지 포함한다.
</details>

### 15. Vercel 프론트를 새 주소로 띄웠더니 화면은 뜨는데 로그인이 안 된다. 어디가 문제이고 GitHub 연결과 무슨 관계인가?

<details><summary>답 확인</summary>

CORS다. 백엔드 `CORS_ORIGINS`에 옛 프론트 주소만 있어 새 origin의 preflight가
400(허용 헤더 없음)으로 떨어진다 — curl로 옛 origin은 200, 새 origin은 400을
직접 대조했다. GitHub 연결은 "코드를 어디서 가져와 빌드하느냐"이고 CORS는
"빌드된 화면이 백엔드와 통신할 수 있느냐"라 별개다. 정적 프론트는 잘 떴고,
데이터 호출만 브라우저가 막는다. 해결은 백엔드 허용 목록 수정(5분)이지만
그 서버 접근자가 한 명뿐이라 사람 문제가 병목이다.
</details>

### 16. "AWS 계정을 따로 만들자"에서 "개인 백엔드를 노트북으로 내리자"까지 결정이 세 번 바뀌었다. 각 전환의 사실 근거는?

<details><summary>답 확인</summary>

① 별도 계정 → 같은 명의라 프리티어 불가(사용자 실측). ② 같은 계정에 별도
EC2 → 기존 EC2가 m7i-flex.large(8GB, 4GB 여유)라 "동거"가 낫다고 제안했으나
③ 현금이 아니라 **신규 크레딧**으로 내고 있다는 정정 → 크레딧은 잔고라
서버가 클수록 빨리 바닥나므로, 팀 프로젝트에만 크레딧을 쓰려면 개인은
내리는 게 맞다(사용자 결정). 매 단계 내 가정(현금 과금)이 틀렸을 때 바로
계산을 다시 했다는 점이 핵심이다.
</details>

### 17. EC2→노트북 컷오버에서 새 터널을 안 만들고 어떻게 옮겼나? 그리고 왜 1분간 502가 났나?

<details><summary>답 확인</summary>

로컬 `.env`에 EC2와 **같은 `TUNNEL_TOKEN`**이 있었다. 같은 토큰으로 띄우면
같은 터널의 두 번째 replica가 되어 DNS·터널 변경 없이 EC2 replica를 끄는
것만으로 컷오버된다. 502는 터널의 공개 호스트 원본이 대시보드에서
`http://nginx:80`으로 잡혀 있었는데 노트북엔 nginx가 안 떠 있어서
(`lookup nginx ... server misbehaving`). Cloudflare가 신규 커넥터를 우선해
8/8건이 노트북으로 왔다. 즉시 replica 정지로 복구 → 로컬 nginx 기동 →
재합류. 교훈: remote-managed 터널의 원본 주소는 코드에 없다 — replica
추가 전에 그 서비스명이 새 호스트에서도 해석되는지 확인할 것.
</details>

### 18. 로컬 DB에 영화가 47편뿐이었다. TMDB 수집분은 어디 갔고, 복원 후 무엇으로 검증했나?

<details><summary>답 확인</summary>

47편은 노트북 개발용 DB(프로덕션 데이터가 들어온 적 없음)였고 수집분
3,410편은 EC2에 있었다. `pg_dumpall`(92MB)로 받아 로컬 DB를 드롭 후 복원,
검증은 movies/users/reviews/chat/picks 건수를 EC2와 1:1 대조(3,410/9/258/
414/668), hub_knowledge 2,963, alembic 리비전, pgvector 확장 존재까지.
"role already exists" 오류 하나는 무해로 판정. 복원 전 로컬 DB도 백업했다.
</details>

## 2026-09-02

### 5. lora-server를 llama.cpp GGUF로 바꿨더니 왜 3배 가까이 빨라졌나?

<details><summary>답 확인</summary>

LLM 생성은 토큰마다 전체 가중치를 읽는 **메모리 대역폭 병목**이다.
Q5_K_M 양자화로 가중치가 fp16 4.8GB → 1.7GB(약 1/3)가 되니 토큰당 읽기량이
그만큼 줄어 디코드가 26 → 83tok/s. 추가로 llama.cpp는 단일 요청 추론 전용
커널이라 transformers의 범용 오버헤드가 없다. 품질은 "후보 중 고르기"라는
제약 과제라 Q5에서 손실이 사실상 없었다(픽이 fp16과 동일).
</details>

### 6. serve_gguf.py를 "파사드"로 만든 이유는? 무엇이 안 바뀌었나?

<details><summary>답 확인</summary>

EC2 orchestrator와의 계약(X-Lora-Token 헤더, /generate·/health·/reload,
{"prompt"}→{"text"})을 유지하면 **백엔드·EC2 배포·폴백 체인 변경이 0건**이
된다. 파사드가 llama-server를 자식 프로세스로 관리하고 OpenAI 형식으로 변환
프록시한다. 롤백도 systemd ExecStart 한 줄 복구로 끝난다.
</details>

### 7. GGUF 전환 후에도 E2E는 6.8초였다. 시간이 어디로 갔고, 다음 병목은?

<details><summary>답 확인</summary>

분해 실측: 분류기 Gemini 2.06s + 의도 추출 Gemini 0.91s + 임베딩 0.39s +
DB 0.04s + LoRA 생성 2.41s. 생성이 6초→2.4초로 줄면서 병목이 **분류기 LLM
호출**로 이동했다. 다음 레버는 분류기와 (의도 추출→RAG) 체인의 투기적
병렬화(예상 ~4.5s) — 트레이드오프는 비추천 질의에서의 Gemini 쿼터 낭비.
</details>

### 8. "좀비 영화 추천해줘"가 "비 영화"로 검색되던 버그 — 정규식의 어느 한 글자가 문제였나?

<details><summary>답 확인</summary>

문두 담화어 제거 정규식 `^(오늘|지금|좀|...)\s*`의 **`\s*`(공백 0개 허용)**.
"좀비"의 "좀"이 담화어로 매칭돼 "비 영화"(rain)로 변질 — RAG·태그가 전부
오염됐다. `\s+`(공백 필수)로 고쳐 "좀 추천해줘"류만 제거되게 했다.
9/1 트레이스의 "비와 당신의 이야기" 미스터리도 이걸로 설명됐다.
</details>

### 9. 재학습은 언제 해야 하나? 이번(65→92건)은 세 트리거 중 무엇이었나?

<details><summary>답 확인</summary>

트리거 3개: ① 출력 스키마(계약)가 바뀔 때 ② 로그에 체계적 실패 패턴이
쌓일 때 ③ 데이터셋이 의미 있게 커질 때. 이번은 ③ — 태그 백필+필러 수정으로
스킵 49→17건이 풀려 65→92건. 카탈로그 증감·프롬프트 입력 수정·파이프라인
로직 수정은 재학습 사유가 아니다(지식은 DB에, 모델은 형식·선택만).
어댑터는 캐시고 **영속 자산은 데이터셋 생성 파이프라인**이다.
</details>

### 10. 학습 직후 서버를 켰더니 생성이 31초로 열화됐다. 원인과 재발 방지 수칙은?

<details><summary>답 확인</summary>

학습 프로세스의 VRAM이 지연 반환되는 동안 서버가 로드되면서 WDDM 공유
메모리로 스필 — 이후 추론이 계속 느리다. 수칙: 학습 후 stop →
`nvidia-smi`로 VRAM 하강 확인 → start. GGUF 전환으로 서빙 VRAM이
2.7GB로 줄어 이 문제 자체의 여지도 축소됐다.
</details>

### 11. 에디터 리뷰 41건 정비 때 정식 CLI를 재사용한 이유와, 그 CLI가 자동으로 해주는 3가지는?

<details><summary>답 확인</summary>

일회성 SQL을 다시 짜면 9/1 배치와 로직이 어긋날 수 있다. 정식
`backfill_review_sentiment_cli.py`는 ① sentiment_label/score 기록
② rating이 NULL이면 감정→자동별점 변환(`sentiment_to_rating`: 긍정
2.5+score×2.5, 부정 2.5−score×2.0, 0.5 단위 반올림) ③ 해당 영화
평균 평점 재계산(`_update_movie_rating`)까지 한 경로로 처리한다.
프로덕션 접속은 SSH 터널(15432)로 해결했다.
</details>

### 12. TMDB 404 영화(id 2769) 삭제 전에 무엇을 확인했고, 왜 안전했나?

<details><summary>답 확인</summary>

의존 데이터 사전 조회 — picks·reviews·watchlist·rankings 전부 0건(유저
데이터 없음), tags 2·characters 7뿐. FK가 전부 `ondelete=CASCADE`라
DELETE 한 건으로 정리되고 유저 손실이 없음을 확인한 뒤 삭제했다.
삭제 전 확인 없는 DELETE는 금지.
</details>

---

<!-- 새 날짜 섹션은 이 줄 위, 기존 최신 날짜 위에 추가 -->
