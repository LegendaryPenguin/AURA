#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
CLIENT_DIR="${ROOT_DIR}/client"
NPM_BIN="${NPM_BIN:-npm}"

if [[ ! -d "${CLIENT_DIR}" ]]; then
  echo "Client directory not found: ${CLIENT_DIR}" >&2
  exit 1
fi

if ! command -v "${NPM_BIN}" >/dev/null 2>&1; then
  echo "npm not found in PATH." >&2
  exit 1
fi

echo "Installing client dependencies in ${CLIENT_DIR}"
"${NPM_BIN}" install --prefix "${CLIENT_DIR}"

echo "Client dependencies installed successfully."
