#!/usr/bin/env bash
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INSTALL_DIR="${HOME}/.local/bin"
APP_NAME="opencode_go_float_widget.py"
DESKTOP_FILE="opencode-go-float-widget.desktop"
ENV_DIR="${HOME}/.config/environment.d"
ENV_FILE="${ENV_DIR}/99-opencode-go-float-widget.conf"
AUTOSTART_DIR="${HOME}/.config/autostart"

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
mkdir -p "${ENV_DIR}"
chmod 700 "${ENV_DIR}"

if [[ -f "${ENV_FILE}" ]]; then
    echo "    Existing config found at ${ENV_FILE}"
    read -r -p "    Overwrite? [y/N]: " answer
    if [[ "${answer}" != "y" && "${answer}" != "Y" ]]; then
        echo "    Keeping existing config."
    else
        prompt_required "OpenCode Workspace ID (e.g. wrk_01KXNRH9RH9JS746CTPEV1R7NA)" WORKSPACE_ID
        prompt_secret "OpenCode auth cookie (e.g. auth=Fe26.2**...)" AUTH_COOKIE
        cat > "${ENV_FILE}" <<EOF
OPENCODE_WORKSPACE_ID=${WORKSPACE_ID}
OPENCODE_AUTH=${AUTH_COOKIE}
EOF
        chmod 600 "${ENV_FILE}"
        echo "    Config updated."
    fi
else
    prompt_required "OpenCode Workspace ID (e.g. wrk_01KXNRH9RH9JS746CTPEV1R7NA)" WORKSPACE_ID
    prompt_secret "OpenCode auth cookie (e.g. auth=Fe26.2**...)" AUTH_COOKIE
    cat > "${ENV_FILE}" <<EOF
OPENCODE_WORKSPACE_ID=${WORKSPACE_ID}
OPENCODE_AUTH=${AUTH_COOKIE}
EOF
    chmod 600 "${ENV_FILE}"
    echo "    Config created."
fi

echo "==> Installing ${APP_NAME} to ${INSTALL_DIR}"
mkdir -p "${INSTALL_DIR}"
cp "${REPO_DIR}/${APP_NAME}" "${INSTALL_DIR}/${APP_NAME}"
chmod +x "${INSTALL_DIR}/${APP_NAME}"

echo "==> Installing autostart .desktop entry"
mkdir -p "${AUTOSTART_DIR}"
cat > "${AUTOSTART_DIR}/${DESKTOP_FILE}" <<EOF
[Desktop Entry]
Type=Application
Name=OpenCode Go Usage Float
Comment=Floating OpenCode Go usage widget
Exec=bash -c 'export OPENCODE_WORKSPACE_ID=\$(grep "^OPENCODE_WORKSPACE_ID=" ${ENV_FILE} 2>/dev/null | cut -d= -f2-); export OPENCODE_AUTH=\$(grep "^OPENCODE_AUTH=" ${ENV_FILE} 2>/dev/null | cut -d= -f2-); exec ${INSTALL_DIR}/${APP_NAME}'
Terminal=false
X-GNOME-Autostart-enabled=true
EOF
chmod 644 "${AUTOSTART_DIR}/${DESKTOP_FILE}"

echo "==> Done"
echo "    Run now: ${INSTALL_DIR}/${APP_NAME}"
echo "    It will also start automatically on your next login."
