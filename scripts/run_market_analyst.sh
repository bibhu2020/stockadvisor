#!/usr/bin/env bash
set -e
cd "$(dirname "$0")/.."
python3 agents/market_analyst/run_market_analyst.py manual
