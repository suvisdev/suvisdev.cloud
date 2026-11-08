#!/usr/bin/env bash
# 길들 서빙 데이터(git 밖 hostPath)를 GitHub Release로 주고받는다 — 무료·비공개(2026-10-02).
# 코드는 main 머지 → CD로 운영에 가지만, apps/gildle/data/는 git에 없어 따로 옮겨야 한다.
#
#   push           개발 머신에서. 서빙 파일을 묶어 Release `gildle-data-YYYYMMDD-HHMM`로 올린다(gh 필요).
#   pull [태그]    운영 러너에서(.github/workflows/gildle-data-sync.yml). 태그를 비우면 최신 gildle-data-*.
#                  체크섬 확인 후 파일마다 rename으로 교체 — 라우터가 파일 mtime을 보고 다시 읽으므로
#                  재시작이 필요 없다. 되돌리려면 이전 태그로 다시 pull.
#
# 생성용 입력(seoul_buildings_osm.json·graph_cache/seoul.graphml 등)은 서빙에 안 쓰여 넣지 않는다.
set -euo pipefail

DATA_DIR="${GILDLE_DATA_DIR:-$(cd "$(dirname "$0")/.." && pwd)/apps/gildle/data}"
REPO="${GILDLE_DATA_REPO:-suvisdev/suvisdev.cloud}"
FILES=(scored_edges.json node_elevation.json shade_scores.json shade_scores_{01..12}.json)
ASSET=gildle-data.tar.gz
TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT

push() {
  local tag
  tag="gildle-data-$(date +%Y%m%d-%H%M)"
  tar -czf "$TMP/$ASSET" -C "$DATA_DIR" "${FILES[@]}"
  (cd "$TMP" && sha256sum "$ASSET" > "$ASSET.sha256")
  gh release create "$tag" "$TMP/$ASSET" "$TMP/$ASSET.sha256" --repo "$REPO" --latest=false \
    --title "길들 데이터 $tag" --notes "apps/gildle/data 서빙 파일 ${#FILES[@]}개. 운영 반영: Actions → gildle-data-sync → Run workflow(태그 $tag)."
  echo "올림: $tag"
}

# 러너엔 gh가 없을 수 있어 curl + GitHub API로 받는다(GH_TOKEN = 워크플로 토큰).
api() { curl -fsSL -H "Authorization: Bearer ${GH_TOKEN:?GH_TOKEN 없음}" -H "X-GitHub-Api-Version: 2022-11-28" "$@"; }

pull() {
  local tag="${1:-}" release
  if [ -z "$tag" ]; then
    tag=$(api "https://api.github.com/repos/$REPO/releases?per_page=50" | python3 -c '
import json, sys
tags = [r["tag_name"] for r in json.load(sys.stdin) if r["tag_name"].startswith("gildle-data-")]
print(max(tags) if tags else "")')
    [ -n "$tag" ] || { echo "gildle-data-* Release가 없음" >&2; exit 1; }
  fi
  release=$(api "https://api.github.com/repos/$REPO/releases/tags/$tag")
  for name in "$ASSET" "$ASSET.sha256"; do
    url=$(python3 -c 'import json,sys; print(next(a["url"] for a in json.loads(sys.argv[1])["assets"] if a["name"]==sys.argv[2]))' "$release" "$name")
    api -H "Accept: application/octet-stream" -o "$TMP/$name" "$url"
  done
  (cd "$TMP" && sha256sum -c "$ASSET.sha256")
  mkdir "$TMP/x" && tar -xzf "$TMP/$ASSET" -C "$TMP/x"
  for f in "${FILES[@]}"; do
    cp "$TMP/x/$f" "$DATA_DIR/.$f.new" && mv -f "$DATA_DIR/.$f.new" "$DATA_DIR/$f"
  done
  echo "교체: $tag → $DATA_DIR (${#FILES[@]}개)"
}

case "${1:-}" in
  push) push ;;
  pull) pull "${2:-}" ;;
  *) echo "사용법: $0 push | pull [태그]" >&2; exit 2 ;;
esac
