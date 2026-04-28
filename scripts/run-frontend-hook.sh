#!/usr/bin/env bash
set -eu

script_name="${1:?usage: scripts/run-frontend-hook.sh <npm-script> [--check-git-diff]}"
shift

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
frontend_dir="$repo_root/frontend"

run_with_local_npm() {
    cd "$frontend_dir"

    if [ ! -f node_modules/.package-lock.json ] || [ package-lock.json -nt node_modules/.package-lock.json ]; then
        npm ci
    fi

    npm run "$script_name"
}

run_with_docker() {
    docker run --rm \
        -v "$frontend_dir:/workspace/frontend" \
        -v horarios-frontend-node-modules:/workspace/frontend/node_modules \
        -w /workspace/frontend \
        node:25-alpine \
        sh -lc \
        'if [ ! -f node_modules/.package-lock.json ] || [ package-lock.json -nt node_modules/.package-lock.json ]; then npm ci; fi; npm run "$1"' \
        sh "$script_name"
}

if command -v npm >/dev/null 2>&1; then
    run_with_local_npm
elif command -v docker >/dev/null 2>&1; then
    run_with_docker
else
    echo "npm was not found, and Docker is not available as a fallback." >&2
    echo "Install Node.js/npm or Docker to run frontend pre-commit hooks." >&2
    exit 127
fi

if [ "${1:-}" = "--check-git-diff" ]; then
    git -C "$repo_root" diff --exit-code --quiet -- frontend
fi
