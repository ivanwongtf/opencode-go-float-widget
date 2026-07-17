#!/usr/bin/env bash
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INSTALL_DIR="${HOME}/.local/bin"
APP_NAME="opencode_go_float_widget_mac.py"
CORE_NAME="core.py"
WRAPPER="opencode-go-float-widget.wrapper.sh"
PLIST="com.opencode.go-float-widget.plist"
ENV_FILE="${HOME}/.config/opencode-go-float-widget/env"

HOME_ESCAPED="${HOME//\//\\/}"

prompt_required() {
    local prompt_text="$1"
    local var_name="$2"
    local value=""
    while [[ -z "${value}" ]]; do
        read -r -p "${prompt_text}: " value
        if [[ -z "${value}" ]]; then
            echo "    This value is required." >&2
        fi
    done
    printf -v "${var_name}" '%s' "${value}"
}

prompt_secret() {
    local prompt_text="$1"
    local var_name="$2"
    local value=""
    while [[ -z "${value}" ]]; do
        read -r -s -p "${prompt_text}: " value
        echo >&2
        if [[ -z "${value}" ]]; then
            echo "    This value is required." >&2
        fi
    done
    printf -v "${var_name}" '%s' "${value}"
}

echo "==> Configuring OpenCode credentials"
mkdir -p "$(dirname "${ENV_FILE}")"
chmod 700 "$(dirname "${ENV_FILE}")"

if [[ -f "${ENV_FILE}" ]]; then
    echo "    Existing config found at ${ENV_FILE}"
    read -r -p "    Overwrite? [y/N]: " answer
    if [[ "${answer}" != "y" && "${answer}" != "Y" ]]; then
        echo "    Keeping existing config."
    else
        prompt_required "OpenCode Workspace ID (e.g. wrk_01KXNRH9RH9JS746CTPEV1R7NA)" WORKSPACE_ID
        prompt_secret "OpenCode auth cookie (e.g. auth=Fe26.2**...)" AUTH_COOKIE
        cat > "${ENV_FILE}" <<EOF
export OPENCODE_WORKSPACE_ID='${WORKSPACE_ID}'
export OPENCODE_AUTH='${AUTH_COOKIE}'
EOF
        chmod 600 "${ENV_FILE}"
        echo "    Config updated."
    fi
else
    prompt_required "OpenCode Workspace ID (e.g. wrk_01KXNRH9RH9JS746CTPEV1R7NA)" WORKSPACE_ID
    prompt_secret "OpenCode auth cookie (e.g. auth=Fe26.2**...)" AUTH_COOKIE
    cat > "${ENV_FILE}" <<EOF
export OPENCODE_WORKSPACE_ID='${WORKSPACE_ID}'
export OPENCODE_AUTH='${AUTH_COOKIE}'
EOF
    chmod 600 "${ENV_FILE}"
    echo "    Config created."
fi

echo "==> Installing ${APP_NAME} and ${CORE_NAME} to ${INSTALL_DIR}"
mkdir -p "${INSTALL_DIR}"
cp "${REPO_DIR}/${APP_NAME}" "${INSTALL_DIR}/${APP_NAME}"
chmod +x "${INSTALL_DIR}/${APP_NAME}"
cp "${REPO_DIR}/${CORE_NAME}" "${INSTALL_DIR}/${CORE_NAME}"

echo "==> Installing wrapper script"
cp "${REPO_DIR}/${WRAPPER}" "${INSTALL_DIR}/${WRAPPER}"
chmod +x "${INSTALL_DIR}/${WRAPPER}"

echo "==> Installing LaunchAgent"
mkdir -p "${HOME}/Library/LaunchAgents"
sed "s/__HOME__/${HOME_ESCAPED}/g" "${REPO_DIR}/${PLIST}" \
    > "${HOME}/Library/LaunchAgents/${PLIST}"
chmod 644 "${HOME}/Library/LaunchAgents/${PLIST}"

echo "==> Loading LaunchAgent"
if launchctl list "com.opencode.go-float-widget" >/dev/null 2>&1; then
    launchctl bootout "gui/$(id -u)" "${HOME}/Library/LaunchAgents/${PLIST}" || true
fi
launchctl bootstrap "gui/$(id -u)" "${HOME}/Library/LaunchAgents/${PLIST}" || true

echo "==> Done"
echo "    Run now: ${INSTALL_DIR}/${WRAPPER}"
echo "    It will also start automatically on your next login."
