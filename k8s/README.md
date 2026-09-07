# k8s 매니페스트 — 구 docker-compose.yaml 대체 (2026-09-07)

구 `docker-compose.yaml`(nginx·certbot·backend·auth·db·redis·pgadmin·cloudflared·neo4j)을
쿠버네티스 매니페스트로 전환한 것. **데스크톱(로컬 개발)은 이 WSL2에 직접 설치한
k3s를 쓰고, 노트북(프로덕션) 컷오버 때 같은 매니페스트를 재사용한다.**
(Docker Desktop의 Kubernetes 토글은 쓰지 않는다 — 켜지 말 것, RAM만 소모.)

## k3s 설치 (1회)

```bash
# systemd가 PID 1인 WSL2 배포판에서 (이 데스크톱 확인됨)
curl -sfL https://get.k3s.io | sudo sh -s - --write-kubeconfig-mode 644
# kubectl이 k3s를 보게 (셸 프로필에 추가)
echo 'export KUBECONFIG=/etc/rancher/k3s/k3s.yaml' >> ~/.bashrc
```

- Traefik(Ingress)·ServiceLB(LoadBalancer)·local-path(StorageClass) 내장 —
  별도 컨트롤러 설치 없음.
- 제거는 `k3s-uninstall.sh` 하나로 끝(데이터 포함 전부 삭제되니 주의).

## 첫 배포

```bash
# 1. 이미지 빌드 + k3s containerd로 import (k3s는 도커와 이미지 저장소가 분리돼 있다)
docker build -t suvisdev-app:latest ./suvisdev
docker save suvisdev-app:latest | sudo k3s ctr images import -
# 2. 배포 (Secret 생성 + 전체 apply)
./k8s/deploy.sh
# 3. 확인
kubectl -n suvisdev get pods -w
```

이후 코드 변경 배포는 `./k8s/deploy.sh --build` 한 방(빌드→import→apply→rollout).

## compose → k8s 대응표

| 구 compose | k8s | 접근 |
|-----------|-----|------|
| `db` (pgvector) | StatefulSet + PVC(local-path) | `localhost:5432` (ServiceLB) |
| `redis` | Deployment + PVC | `localhost:6379` |
| `backend` | Deployment (initContainer로 db/redis 대기) | `localhost:8000` |
| `auth` | Deployment (같은 이미지, command만 교체) | `localhost:9000` |
| `pgadmin` | Deployment, **기본 꺼짐**(replicas 0) | 켜면 `localhost:5050` |
| `neo4j` | Deployment, **기본 꺼짐** | port-forward 7474/7687 |
| `cloudflared` | Deployment, **기본 꺼짐 — 노트북 전용, 데스크톱에서 켜지 말 것** | — |
| `nginx` + `certbot` | `ingress.yaml` (k3s 내장 Traefik; TLS는 Cloudflare가 종단) | — |
| `env_file: suvisdev/.env` | Secret `suvisdev-env` (deploy.sh가 매번 갱신) | — |
| 바인드 마운트 (datasets·crawled·gildle/data) | hostPath — 노드가 이 WSL이라 저장소 경로 그대로 | — |
| `extra_hosts: host.docker.internal` | hostAliases → `10.42.0.1`(flannel cni0 = 호스트) | — |

꺼진 것 켜기: `kubectl -n suvisdev scale deploy/<이름> --replicas=1`

## 자주 쓰는 명령

```bash
kubectl -n suvisdev get pods                       # 상태
kubectl -n suvisdev logs -f deploy/backend         # 로그 (구 docker logs -f)
kubectl -n suvisdev exec -it deploy/backend -- sh  # 셸 (구 docker exec)
kubectl -n suvisdev rollout restart deploy/backend # 재시작
kubectl -n suvisdev scale deploy/backend --replicas=0  # 내리기(리소스 회수)
sudo k3s ctr images ls | grep suvisdev             # import된 이미지 확인
```

## 구 compose 볼륨의 DB 데이터 이전 (필요할 때만)

구 도커 볼륨(`suvisdevcloud_db_data` 등)은 지우지 않고 남겨뒀다. 데이터가 필요하면:

```bash
# 구 볼륨을 임시 컨테이너로 띄워 덤프
docker run -d --name olddb -v suvisdevcloud_db_data:/var/lib/postgresql/data \
  -e POSTGRES_PASSWORD=unused pgvector/pgvector:pg16
docker exec olddb pg_dumpall -U <POSTGRES_USER> > /tmp/old_db.sql
docker rm -f olddb
# k3s db로 복원
kubectl -n suvisdev exec -i db-0 -- psql -U <POSTGRES_USER> -d postgres < /tmp/old_db.sql
```

## 노트북(프로덕션) k3s 컷오버 — 단계별 계획

데스크톱(개발)은 데이터가 덤프 한 번이면 복구되므로 db·redis를 클러스터 안에
넣었지만, **노트북은 프로덕션 데이터가 살아 있으므로 컴퓨트와 상태를 동시에
옮기지 않는다**:

1. **1단계 — 앱만 k3s로**: backend·auth·cloudflared만 파드로. db·redis는 기존
   도커 컨테이너 그대로 두고, `external-db-redis.yaml`(셀렉터 없는 Service +
   EndpointSlice → `10.42.0.1`)로 연결한다. `deploy.sh --external-db`가 db.yaml·
   redis.yaml 대신 이 파일과 ingress.yaml을 apply한다. Service 이름이 `db`/`redis`라
   연결 문자열이 compose 시절과 같고 앱 수정이 없다(ExternalName은 CNAME 방식이라
   IP를 못 가리켜 못 씀). 절차는 아래 "노트북 1단계 실행 절차".
2. **2단계 — redis 이관**: 캐시라 날아가도 안전한 것부터 StatefulSet/PVC 연습.
3. **3단계 — db(pgvector) 판단**: 단일 노드에선 local-path PVC도 결국 같은
   디스크라 실익이 작다. 끝까지 밖에 둬도 무방(상용에서도 흔한 구성).

### 노트북 1단계 실행 절차 (2026-09-07 컷오버 완료 — 재현·롤백용 기록)

사전 확인된 전제(09-07 실측): systemd PID 1, RAM 15GB, 도커 네이티브(Desktop 아님),
db·redis가 `0.0.0.0:5432/6379`로 노출, lora-server·Ollama가 `0.0.0.0` 바인딩,
`.env`에 따옴표 값 없음, `suvisdev-app:latest` 이미지 빌드돼 있음.

```bash
# 0. (pull 직후) compose 파일 로컬 복구 — 롤백·운영 수단. untracked로 남겨둔다
git show c8e09fa:docker-compose.yaml > docker-compose.yaml

# 1. k3s 설치. --disable servicelb: 호스트 80/443(nginx)·5432/6379(도커)와 포트를
#    다투지 않게 ServiceLB를 끈다. LoadBalancer 타입 Service는 <pending>으로 남지만
#    cloudflared→Traefik→backend가 전부 ClusterIP라 동작엔 무관. LAN 노출도 없어진다.
curl -sfL https://get.k3s.io | sudo sh -s - --write-kubeconfig-mode 644 --disable servicelb
echo 'export KUBECONFIG=/etc/rancher/k3s/k3s.yaml' >> ~/.bashrc && export KUBECONFIG=/etc/rancher/k3s/k3s.yaml
kubectl get nodes   # Ready 확인

# 2. 이미 빌드된 이미지를 k3s containerd로 import (재빌드 불필요)
docker save suvisdev-app:latest | sudo k3s ctr images import -

# 3. 배포 (cloudflared는 replicas 0이라 아직 트래픽 안 받음)
./k8s/deploy.sh --external-db
kubectl -n suvisdev get pods -w      # backend·auth Running + READY 1/1 까지 대기

# 4. 클러스터 안에서 프로덕션 DB로 붙는지 검증 (Traefik ClusterIP + Host 헤더)
TRAEFIK=$(kubectl -n kube-system get svc traefik -o jsonpath='{.spec.clusterIP}')
curl -s -H 'Host: api.suvisdev.cloud' "http://$TRAEFIK/mova/movies?limit=2" | head -c 300
curl -s -H 'Host: api.suvisdev.cloud' "http://$TRAEFIK/.well-known/jwks.json" | head -c 200
```

**5. 트래픽 전환**. 원격 관리형 터널이라 라우트(`api → http://nginx:80`,
`auth → http://auth:9000`, `ssh → ssh://host.docker.internal:22`)는 대시보드에 있고
매니페스트로 못 바꾼다. 대시보드를 건드리는 대신 **클러스터 안에 `nginx`라는
ExternalName Service(`nginx-alias.yaml`)를 두어 Traefik으로 넘긴다** — `auth`는
k8s Service로 그대로 해석되고, `ssh`는 cloudflared.yaml hostAliases가 호스트로
매핑한다(단 이 WSL엔 sshd가 없어 compose 시절부터 죽어 있던 라우트).
`deploy.sh --external-db`가 별칭을 이미 apply했으므로 남은 건 커넥터 교체뿐:

```bash
docker compose --env-file suvisdev/.env stop cloudflared
kubectl -n suvisdev scale deploy/cloudflared --replicas=1
kubectl -n suvisdev logs -f deploy/cloudflared     # "Registered tunnel connection" 4개 확인
curl -s -o /dev/null -w '%{http_code}\n' 'https://api.suvisdev.cloud/mova/movies?limit=1'   # 200
```

실제 09-07 컷오버 때는 별칭을 나중에 만들어 라우트 전환~별칭 apply 사이 약 6분간
api가 502였다(auth는 정상). 지금은 deploy.sh가 별칭을 먼저 만들므로 재발 없음.

**롤백**: `kubectl -n suvisdev scale deploy/cloudflared --replicas=0` →
`docker compose --env-file suvisdev/.env start cloudflared` (도커 backend·auth·nginx가
살아 있어야 함 — 6단계로 내렸다면 `start backend auth nginx` 먼저).

**6. 안정 확인 후 정리**: `docker compose --env-file suvisdev/.env stop backend auth nginx`
(db·redis는 계속 도커. `down`은 쓰지 말 것 — 컨테이너를 지워 롤백이 느려진다).
이후 코드 배포는 `./k8s/deploy.sh --external-db --build`.

## 알려진 차이·주의

- **호스트 프로세스 접근**(Ollama :11434 · lora-server :8200 등): 파드의
  `host.docker.internal`이 hostAliases로 `10.42.0.1`(flannel cni0 게이트웨이 =
  이 WSL 호스트)에 매핑돼 있다. 호스트 쪽 프로세스가 0.0.0.0에 바인딩돼
  있어야 한다(Ollama는 `OLLAMA_HOST=0.0.0.0` 확인됨).
- **Secret의 .env 파싱**: `kubectl --from-env-file`은 따옴표를 값에 포함시킨다
  (compose도 동일). 값에 따옴표를 안 쓰는 현 .env 관례를 유지할 것.
- **RAM**: k3s 자체가 상시 ~600MB+를 쓴다(WSL 총 5.8GB). 안 쓸 땐
  `sudo systemctl stop k3s`로 내려도 된다(파드 상태는 재기동 시 복원).
- **노트북 프로덕션은 09-07부터 k3s 1단계**(backend·auth·cloudflared 파드, db·redis는
  도커 유지). compose 파일은 db·redis 운영과 롤백용으로 노트북에 로컬 복구돼 있다
  (untracked, 커밋에 안 딸려 들어감). 다른 머신에서 pull 뒤 필요하면:

  ```bash
  git show c8e09fa:docker-compose.yaml > docker-compose.yaml
  ```

  자체 k3s 컷오버 날 이 로컬 파일을 지우면 된다.
