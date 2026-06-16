#!/usr/bin/env bash
set -e
cd "$(dirname "$0")/.."
python3 agents/retrospective/run_retrospective.py --triggered-by manual "$@"
