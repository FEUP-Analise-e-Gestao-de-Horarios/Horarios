#!/bin/sh
set -e

# Ensure database directories exist
mkdir -p "$(dirname "$0")/../databases/projects"

python manage.py migrate --noinput

exec "$@"
