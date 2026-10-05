#!/usr/bin/env bash
# 집컴 올라마 예열기 — 중계기가 노트북을 빼는 순간 집컴 CPU 모델을 미리 올리고,
# 노트북이 2분 넘게 다시 붙어 있으면 내린다. 평소엔 집컴 메모리(8.9GB)를 3GB 가까이 아낀다.
# 상주시키면 배포 때 메모리가 모자라 DB가 죽었고(10-05), 안 올려 두면 첫 요청이 88초 걸렸다(10-05).
MODELS=(exaone3.5:2.4b bge-m3)
OLLAMA=http://127.0.0.1:11434
UNLOAD_AFTER=120   # 노트북이 이만큼(초) 연속으로 붙어 있으면 집컴 모델을 내린다
up_since=0

laptop_state() { curl -s -m 3 "127.0.0.1:8404/;csv" | awk -F, '$1=="ollama" && $2=="laptop"{print $18}'; }
loaded() { curl -s -m 3 "$OLLAMA/api/ps" | grep -q "\"name\":\"$1"; }
load() {
  local s; s=$(date +%s)
  case "$1" in
    bge-m3) curl -s -m 300 "$OLLAMA/api/embed" -d "{\"model\":\"$1\",\"input\":\"\",\"keep_alive\":\"-1m\"}" >/dev/null ;;
    *)      curl -s -m 300 "$OLLAMA/api/generate" -d "{\"model\":\"$1\",\"keep_alive\":\"-1m\"}" >/dev/null ;;
  esac
  echo "$(date +%T) 집컴 $1 예열 끝 ($(( $(date +%s) - s ))초)"
}
unload() { curl -s -m 30 "$OLLAMA/api/generate" -d "{\"model\":\"$1\",\"keep_alive\":0}" >/dev/null; }

while true; do
  st=$(laptop_state)
  now=$(date +%s)
  if [ "$st" = "UP" ]; then
    [ "$up_since" -eq 0 ] && up_since=$now
    if [ $((now - up_since)) -ge "$UNLOAD_AFTER" ]; then
      for m in "${MODELS[@]}"; do
        if loaded "$m"; then unload "$m"; echo "$(date +%T) 노트북 복귀 ${UNLOAD_AFTER}초 — 집컴 $m 내림"; fi
      done
    fi
  elif [ -n "$st" ]; then
    up_since=0
    pids=()
    for m in "${MODELS[@]}"; do
      if ! loaded "$m"; then
        echo "$(date +%T) 노트북 상태 $st — 집컴 $m 예열 시작"
        load "$m" & pids+=($!)
      fi
    done
    [ ${#pids[@]} -gt 0 ] && wait "${pids[@]}"
  fi
  sleep 3
done
