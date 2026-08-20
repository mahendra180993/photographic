#!/usr/bin/env bash
# Netlify build: collect static assets and install the proxy function deps.
set -euo pipefail

pip install -r requirements.txt
python manage.py collectstatic --noinput
npm install
