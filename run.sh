#!/bin/bash

cd "$(dirname "$0")"

COMMAND="$1"

set -eu

source .venv/bin/activate

exec uvicorn kubediag.main:app --host 0.0.0.0 --port 8000 --proxy-headers --forwarded-allow-ips="10.0.0.0/8"
