#!/usr/bin/env bash
set -e
cd "$(dirname "$0")/.."
python3 agents/paper_trader/run_paper_trader.py manual
