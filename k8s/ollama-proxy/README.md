# 올라마 중계기 — 노트북 GPU 우선, 꺼지면 집컴 CPU (2026-10-05)

운영(집컴, GTX 1650 SUPER 4GB)의 GPU는 lora-server가 쓰고 있어서 올라마는 CPU 전용이다
(`exaone3.5:2.4b` 4 tok/s 수준 — mova 채팅 판단·이해 단계와 RAG 임베딩이 느린 원인).
노트북(RTX 4060 8GB)이 켜져 있으면 올라마 호출만 노트북 GPU로 보내고, 꺼지면 집컴 CPU로 자동으로 돌아간다.
**DB·API·터널은 계속 집컴 한 곳**이라 데이터가 갈라질 일이 없다. 바뀌는 건 올라마 호출 경로뿐.

```
backend 파드 ── OLLAMA_BASE_URL=http://host.docker.internal:11435
   │
   ▼  (집컴 WSL, docker --network host)
HAProxy :11435 ─┬─ laptop  127.0.0.1:21434 ──(노트북이 연 역방향 SSH 터널)──▶ 노트북 Ollama :11434 (GPU)
                └─ desktop 127.0.0.1:11434  (backup — 노트북이 빠졌을 때만) 집컴 Ollama (CPU)
```

## 실측 (2026-10-05, 집컴에서 같은 요청)

| 경로 | `exaone3.5:2.4b` 생성 | `bge-m3` 임베딩 |
|---|---|---|
| 집컴 CPU (11434) | 5.40초 · 4.2 tok/s | 0.605초 |
| 중계기 → 노트북 GPU | 0.31초 · 120.5 tok/s | 0.227초 |

장애 시험: 터널을 끊는 순간에도 요청 실패 0건(연결 오류 → 즉시 노트북 제외 → 같은 요청을 집컴으로 재시도).
노트북이 응답 없이 멈춘 경우(잠듦·와이파이 끊김 흉내)는 그때 처리 중이던 요청 1건만 실패하고(약 5초), 이후는 집컴.
노트북이 돌아오면 3~4초 안에 다시 노트북으로 간다.

## 구성 파일

| 파일 | 어디에 | 하는 일 |
|---|---|---|
| `haproxy.cfg` | 집컴 `~/ollama-proxy/haproxy.cfg` | 1초 점검 · 연결 오류 시 즉시 제외 · 재시도 · 노트북 제외 시 매달린 연결 끊기 |
| `free_tunnel_port.sh` | 집컴 `~/ollama-proxy/free_tunnel_port.sh` | 노트북이 다시 붙기 전에, 끊긴 옛 세션이 쥔 21434 포트를 놓아 줌(같은 사용자라 sudo 불필요) |
| `ollama-tunnel.service` | 노트북 `~/.config/systemd/user/` | `ssh -N -R 127.0.0.1:21434:127.0.0.1:11434`, `Restart=always` |

## 설치

**집컴** (`suvisdev`, docker 그룹. sudo 불필요):

```bash
mkdir -p ~/ollama-proxy && cp k8s/ollama-proxy/haproxy.cfg k8s/ollama-proxy/free_tunnel_port.sh ~/ollama-proxy/
chmod +x ~/ollama-proxy/free_tunnel_port.sh
docker run -d --name ollama-proxy --restart unless-stopped --network host \
  -v ~/ollama-proxy/haproxy.cfg:/usr/local/etc/haproxy/haproxy.cfg:ro haproxy:3.0-alpine
```

**노트북** (WSL, 집컴에 `~/.ssh/home_desktop` 키로 와이파이 SSH 가능해야 함):

```bash
# 운영이 쓰는 모델을 같은 ID로 맞춘다 (집컴 `ollama list`의 ID와 같아야 함)
ollama pull exaone3.5:2.4b; ollama pull bge-m3; ollama pull nomic-embed-text; ollama pull exaone3.5:7.8b
# 직접 학습한 mova-agent-v9 · mova-understand-v7 은 집컴 올라마 저장소의 blob(sha256 검증)과 Modelfile로 `ollama create`
cp k8s/ollama-proxy/ollama-tunnel.service ~/.config/systemd/user/
systemctl --user daemon-reload && systemctl --user enable --now ollama-tunnel
```

**노트북 윈도우**: WSL이 저절로 켜지지 않으므로 로그온 작업 `WSL 유지 (올라마 터널)`
(`conhost.exe --headless wsl.exe -d Ubuntu --exec /bin/sleep infinity`, 관리자 권한 불필요)을 등록해 뒀다.
노트북 전원 설정은 절전·최대 절전 없음, 덮개 닫아도 동작 없음(10-05 확인).

## 확인

```bash
# 집컴: 지금 어느 쪽이 받는지 (laptop=UP 이면 노트북 GPU)
curl -s "127.0.0.1:8404/;csv" | awk -F, '$1=="ollama" && $2!="BACKEND"{print $2, $18, "처리", $8}'
# 노트북: 터널과 GPU 적재
systemctl --user status ollama-tunnel --no-pager; ollama ps
```

## 끄기 · 되돌리기

- 노트북만 빼기: 노트북에서 `systemctl --user stop ollama-tunnel` → 집컴이 바로 받는다.
- 중계기 자체를 빼기: `backend.yaml`의 `OLLAMA_BASE_URL`을 `:11434`로 되돌려 배포한 뒤 `docker rm -f ollama-proxy`.
  **중계기 컨테이너가 죽으면 올라마 호출 전체가 실패**하므로 순서를 지킨다(배포 먼저, 컨테이너 제거는 나중).

## 주의

- **모델을 바꾸거나 추가하면 양쪽에 같은 ID로.** 노트북에 없는 모델을 요청하면 노트북이 404를 돌려주고, 중계기는 404를
  장애로 보지 않아 집컴으로 넘기지 않는다.
- 노트북 Ollama 0.32.5, 집컴 0.35.0(10-05). 같은 모델 ID라 결과는 같지만, 올릴 땐 노트북도 함께.
- 집컴 IP `172.30.1.21`(공유기 DHCP)이 바뀌면 `ollama-tunnel.service`의 주소를 고친다.
- 노트북 GPU 8GB에 `keep_alive -1m` 모델이 4개(약 6.5GB) 올라간다. `exaone3.5:7.8b`까지 부르면 일부가 내려갔다 올라온다.
- 노트북이 잠들 때 처리 중이던 요청 1건은 실패한다(위 실측). mova는 그 경우 자체 폴백(결정론·Gemini)으로 답한다.
