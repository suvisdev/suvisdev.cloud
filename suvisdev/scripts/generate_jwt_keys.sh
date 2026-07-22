#!/usr/bin/env bash
set -euo pipefail

# auth 게이트웨이(apps/auth) 전용 RS256 키페어 생성. 개인키는 절대 backend/다른 앱
# 컨테이너의 .env에 넣지 않는다 — auth 컨테이너의 .env.auth 전용.
KEY_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/scripts/keys"
mkdir -p "$KEY_DIR"

PRIVATE_KEY_PATH="$KEY_DIR/jwt_private.pem"
PUBLIC_KEY_PATH="$KEY_DIR/jwt_public.pem"

openssl genrsa -out "$PRIVATE_KEY_PATH" 2048
openssl rsa -in "$PRIVATE_KEY_PATH" -pubout -out "$PUBLIC_KEY_PATH"

echo "생성 완료: $PRIVATE_KEY_PATH / $PUBLIC_KEY_PATH"
echo "(*.pem은 이미 .gitignore에 걸려 커밋되지 않습니다)"
echo
echo "아래 두 줄을 나눠서 넣으세요:"
echo "  suvisdev/.env.auth (개인키, 커밋 금지)"
echo "    JWT_PRIVATE_KEY_B64=$(base64 -w0 "$PRIVATE_KEY_PATH")"
echo "  suvisdev/.env (공개키 — 다른 앱 컨테이너도 검증에 필요해 공유 env로 둠)"
echo "    JWT_PUBLIC_KEY_B64=$(base64 -w0 "$PUBLIC_KEY_PATH")"
echo "    JWT_KID=auth-$(date +%Y%m%d)"
