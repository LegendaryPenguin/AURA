#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
PYTHON_BIN="${PYTHON_BIN:-${ROOT_DIR}/.venv/bin/python}"
if [[ ! -x "${PYTHON_BIN}" ]]; then
  PYTHON_BIN="python3"
fi
NPM_BIN="${NPM_BIN:-npm}"

if ! command -v "${PYTHON_BIN}" >/dev/null 2>&1; then
  echo "Python interpreter not found: ${PYTHON_BIN}" >&2
  exit 1
fi

if ! command -v "${NPM_BIN}" >/dev/null 2>&1; then
  echo "npm not found in PATH." >&2
  exit 1
fi

echo "Running Python unit tests"
if [[ -d "${ROOT_DIR}/tests/unit" ]] && compgen -G "${ROOT_DIR}/tests/unit/**/*.py" >/dev/null; then
  "${PYTHON_BIN}" -m pytest "${ROOT_DIR}/tests/unit/" -v
else
  echo "Skipping Python unit tests (no test files found in tests/unit/)."
fi

echo "Running contract tests"
"${PYTHON_BIN}" -m pytest "${ROOT_DIR}/tests/contract/" -v

echo "Running integration tests"
"${PYTHON_BIN}" -m pytest "${ROOT_DIR}/tests/integration/" -v

echo "Running client vitest suite"
"${NPM_BIN}" --prefix "${ROOT_DIR}/client" run test

echo "All test suites passed."
