#!/usr/bin/env bash
# python-dotenv loads root .env automatically
set -e
cd "$(dirname "$0")/.."
python3 agents/scheduler.py
