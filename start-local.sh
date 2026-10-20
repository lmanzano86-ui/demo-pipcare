#!/bin/bash
# Arranca PostgreSQL local (pgserver) y el servidor de desarrollo.
set -e
cd "$(dirname "$0")"
.venv/bin/python scripts/db_start.py > /dev/null 2>&1
echo "PostgreSQL listo."
.venv/bin/python manage.py runserver 127.0.0.1:8000
