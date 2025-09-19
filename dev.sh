#!/bin/bash

set -eu

cd "$(dirname "$0")"

source .venv/bin/activate

if [ -f .env ]; then
	source .env
fi

exec uvicorn --reload kubediag.main:app
