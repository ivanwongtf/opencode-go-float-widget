#!/usr/bin/env bash
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INSTALL_DIR="${HOME}/.local/bin"
APP_NAME="opencode_go_float_widget.py"
DESKTOP_FILE="opencode-go-float-widget.desktop"
ENV_FILE="99-opencode-go-float-widget.conf"

echo "==> Installing ${APP_NAME} to ${INSTALL_DIR}"
mkdir -p "${INSTALL_DIR}"
cp "${REPO_DIR}/${APP_NAME}" "${INSTALL_DIR}/${APP_NAME}"
chmod +x "${INSTALL_DIR}/${APP_NAME}"

echo "==> Installing autostart .desktop entry"
mkdir -p "${HOME}/.config/autostart"
cp "${REPO_DIR}/${DESKTOP_FILE}" "${HOME}/.config/autostart/${DESKTOP_FILE}"
chmod 600 "${HOME}/.config/autostart/${DESKTOP_FILE}"

echo "==> Checking auth cookie configuration"
if [[ -f "${HOME}/.config/environment.d/${ENV_FILE}" ]]; then
    echo "    Auth config already exists at ~/.config/environment.d/${ENV_FILE}"
else
    echo "    Please create ~/.config/environment.d/${ENV_FILE} with:"
    echo "        OPENCODE_AUTH=auth=Fe26.2**..."
fi

echo "==> Done"
echo "    Run now: ${INSTALL_DIR}/${APP_NAME}"
echo "    It will also start automatically on your next login."
