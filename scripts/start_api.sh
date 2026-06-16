#!/usr/bin/env bash
set -e
cd "$(dirname "$0")/../api"

# Free port 3000 if already in use
if fuser 3000/tcp &>/dev/null; then
  echo "[API] Port 3000 in use — stopping existing process..."
  fuser -k 3000/tcp
  sleep 1
fi

npm run start:dev
