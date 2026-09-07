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

1. **1단계 — 앱만 k3s로**: backend·auth만 파드로. db·redis는 기존 도커
   컨테이너 그대로 두고, 클러스터에서 **셀렉터 없는 Service + EndpointSlice**로
   연결한다(ExternalName은 CNAME 방식이라 IP를 못 가리킴). Service 이름을
   `db`/`redis`로 두면 연결 문자열(`@db:5432`, `redis://redis:6379`)이 compose
   시절과 그대로라 앱 수정이 없다:

   ```yaml
   apiVersion: v1
   kind: Service
   metadata: { name: db, namespace: suvisdev }
   spec:
     ports: [{ port: 5432, targetPort: 5432 }]
   ---
   apiVersion: discovery.k8s.io/v1
   kind: EndpointSlice
   metadata:
     name: db-1
     namespace: suvisdev
     labels: { kubernetes.io/service-name: db }
   addressType: IPv4
   ports: [{ port: 5432 }]
   endpoints:
     - addresses: ["10.42.0.1"]   # flannel cni0 = 노드(호스트) 자신
   ```

   전제: 도커 쪽 db가 호스트 포트를 노출하고 있어야 한다(`docker port <db 컨테이너>`
   로 확인, `127.0.0.1:5432` 바인딩이면 파드에서 못 붙으니 `0.0.0.0` 필요 —
   노출 범위는 방화벽으로 제한). 롤백은 cloudflared 대상만 compose nginx로
   되돌리면 끝.
2. **2단계 — redis 이관**: 캐시라 날아가도 안전한 것부터 StatefulSet/PVC 연습.
3. **3단계 — db(pgvector) 판단**: 단일 노드에선 local-path PVC도 결국 같은
   디스크라 실익이 작다. 끝까지 밖에 둬도 무방(상용에서도 흔한 구성).

## 알려진 차이·주의

- **호스트 프로세스 접근**(Ollama :11434 · lora-server :8200 등): 파드의
  `host.docker.internal`이 hostAliases로 `10.42.0.1`(flannel cni0 게이트웨이 =
  이 WSL 호스트)에 매핑돼 있다. 호스트 쪽 프로세스가 0.0.0.0에 바인딩돼
  있어야 한다(Ollama는 `OLLAMA_HOST=0.0.0.0` 확인됨).
- **Secret의 .env 파싱**: `kubectl --from-env-file`은 따옴표를 값에 포함시킨다
  (compose도 동일). 값에 따옴표를 안 쓰는 현 .env 관례를 유지할 것.
- **RAM**: k3s 자체가 상시 ~600MB+를 쓴다(WSL 총 5.8GB). 안 쓸 땐
  `sudo systemctl stop k3s`로 내려도 된다(파드 상태는 재기동 시 복원).
- **⚠️ 노트북 프로덕션은 아직 compose다** — 이 전환은 데스크톱에만 적용된 상태.
  노트북에서 이 변경분을 pull 하면 compose 파일이 사라져 배포가 깨진다.
  노트북은 자체 k3s 컷오버 전까지 현재 커밋에 머물 것.
