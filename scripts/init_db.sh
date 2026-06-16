#!/usr/bin/env bash
set -e
cd "$(dirname "$0")/.."
python3 -c "from agents.core.db import init_db; init_db(); print('DB initialized.')"
