#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
CERT_DIR="${ROOT_DIR}/config/ssl"
CERT_FILE="${CERT_DIR}/localhost+ip.pem"
KEY_FILE="${CERT_DIR}/localhost+ip-key.pem"
LOCAL_IP="${AURA_LOCAL_IP:-}"

if ! command -v mkcert >/dev/null 2>&1; then
  echo "mkcert is required but not installed." >&2
  echo "Install mkcert, then re-run this script." >&2
  exit 1
fi

mkdir -p "${CERT_DIR}"

if [[ -z "${LOCAL_IP}" ]]; then
  LOCAL_IP="$(hostname -I 2>/dev/null | awk '{print $1}')"
fi

if [[ -z "${LOCAL_IP}" ]]; then
  echo "Unable to determine local IP. Set AURA_LOCAL_IP and re-run." >&2
  exit 1
fi

echo "Ensuring mkcert local CA is installed"
mkcert -install

echo "Generating TLS certs for localhost and ${LOCAL_IP}"
mkcert -cert-file "${CERT_FILE}" -key-file "${KEY_FILE}" localhost 127.0.0.1 ::1 "${LOCAL_IP}"

echo "SSL cert ready:"
echo "  cert: ${CERT_FILE}"
echo "  key : ${KEY_FILE}"
