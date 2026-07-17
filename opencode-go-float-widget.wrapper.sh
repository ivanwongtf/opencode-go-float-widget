#!/usr/bin/env bash
set -euo pipefail

ENV_FILE="${HOME}/.config/opencode-go-float-widget/env"
if [[ -f "${ENV_FILE}" ]]; then
    # shellcheck source=/dev/null
    source "${ENV_FILE}"
fi

exec python3 "${HOME}/.local/bin/opencode_go_float_widget_mac.py"
