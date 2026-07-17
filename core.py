from __future__ import annotations

import json
import os
import re
import urllib.request
from dataclasses import dataclass
from typing import Final

BASE_URL: Final[str] = "https://opencode.ai/workspace"

AUTH_ENV_VAR: Final[str] = "OPENCODE_AUTH"
WORKSPACE_ENV_VAR: Final[str] = "OPENCODE_WORKSPACE_ID"
REFRESH_INTERVAL_SECONDS: Final[int] = int(os.environ.get("OPENCODE_REFRESH_SECONDS", "60"))
THROTTLE_COOLDOWN_SECONDS: Final[int] = 600

REQUEST_TIMEOUT: Final[float] = 15.0

USER_AGENT: Final[str] = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)

GREEN_BG: Final[str] = "#2E7D32"
AMBER_BG: Final[str] = "#F9A825"
RED_BG: Final[str] = "#C62828"

WINDOW_LABELS: Final[dict[str, str]] = {
    "rolling": "Rolling",
    "weekly": "Weekly",
    "monthly": "Monthly",
}


@dataclass(frozen=True)
class UsageItem:
    """One usage bucket parsed from the OpenCode Go SSR payload."""

    status: str
    resetInSec: int
    usagePercent: int


@dataclass(frozen=True)
class UsageData:
    """All three usage buckets for a workspace."""

    rolling: UsageItem
    weekly: UsageItem
    monthly: UsageItem


def color_class_for(pct: int) -> str:
    """Return a CSS class suffix for the usage percentage."""
    if pct < 50:
        return "green"
    if pct < 80:
        return "amber"
    return "red"


def _js_obj_to_dict(js_str: str) -> dict[str, object]:
    """Convert a flat JS object literal to a Python dict."""
    s = js_str.strip()
    s = s.replace("!0", "true").replace("!1", "false")
    s = re.sub(r"(\b\w+)(?=\s*:)", r'"\1"', s)
    return json.loads(s)


def _go_url(workspace_id: str) -> str:
    """Build the Go page URL for a workspace."""
    return f"{BASE_URL}/{workspace_id}/go"


def go_url() -> str:
    """Return the Go page URL for the configured workspace.

    Raises:
        ValueError: If OPENCODE_WORKSPACE_ID is unset or empty.
    """
    workspace_id = os.environ.get(WORKSPACE_ENV_VAR)
    if not workspace_id:
        raise ValueError(f"{WORKSPACE_ENV_VAR} environment variable not set")
    return _go_url(workspace_id)


def fetch() -> str:
    """Fetch the Go page HTML.

    Raises:
        ValueError: If OPENCODE_WORKSPACE_ID or OPENCODE_AUTH is unset or empty.
        urllib.error.URLError: On network-level failure.
        urllib.error.HTTPError: If the response is not 2xx.
    """
    workspace_id = os.environ.get(WORKSPACE_ENV_VAR)
    if not workspace_id:
        raise ValueError(f"{WORKSPACE_ENV_VAR} environment variable not set")
    auth_cookie = os.environ.get(AUTH_ENV_VAR)
    if not auth_cookie:
        raise ValueError(f"{AUTH_ENV_VAR} environment variable not set")

    req = urllib.request.Request(
        _go_url(workspace_id),
        headers={
            "Cookie": auth_cookie,
            "User-Agent": USER_AGENT,
            "Accept": (
                "text/html,application/xhtml+xml,"
                "application/xml;q=0.9,*/*;q=0.8"
            ),
            "Accept-Language": "en-US,en;q=0.5",
        },
    )
    with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as resp:
        return resp.read().decode("utf-8")


_USAGE_PATTERNS: Final[dict[str, str]] = {
    "rolling": r"rollingUsage:\$\w+\[\d+\]=",
    "weekly": r"weeklyUsage:\$\w+\[\d+\]=",
    "monthly": r"monthlyUsage:\$\w+\[\d+\]=",
}


def parse(html: str) -> UsageData:
    """Extract rolling/weekly/monthly usage from SSR HTML.

    Raises:
        ValueError: If a usage object is missing or malformed.
        json.JSONDecodeError: If the JS object literal is invalid.
    """
    result: dict[str, UsageItem] = {}
    for name, pattern in _USAGE_PATTERNS.items():
        m = re.search(pattern + r"(\{[^}]+\})", html)
        if not m:
            raise ValueError(f"Could not find {name} usage object in HTML")
        data = _js_obj_to_dict(m.group(1))
        try:
            result[name] = UsageItem(
                status=str(data["status"]),
                resetInSec=int(data["resetInSec"]),
                usagePercent=int(data["usagePercent"]),
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError(f"Invalid {name} usage data") from exc

    return UsageData(
        rolling=result["rolling"],
        weekly=result["weekly"],
        monthly=result["monthly"],
    )


def format_reset_time(seconds: int) -> str:
    """Human-readable ``reset in …`` string."""
    if seconds < 0:
        return "0 minutes"
    if seconds < 60:
        return "less than a minute"
    if seconds < 3600:
        m = seconds // 60
        return f"{m} minute{'s' if m != 1 else ''}"
    total_hours = seconds // 3600
    if total_hours < 24:
        h = total_hours
        m = (seconds % 3600) // 60
        hu = "hour" if h == 1 else "hours"
        mu = "minute" if m == 1 else "minutes"
        return f"{h} {hu} {m} {mu}"
    days = total_hours // 24
    hours = total_hours % 24
    du = "day" if days == 1 else "days"
    hu = "hour" if hours == 1 else "hours"
    return f"{days} {du} {hours} {hu}"


def format_tooltip(usage: UsageData) -> str:
    """Multi-line tooltip with reset times."""
    lines: list[str] = []
    for key, label in WINDOW_LABELS.items():
        item = getattr(usage, key)
        pct = item.usagePercent
        status = item.status
        reset = format_reset_time(item.resetInSec)
        lines.append(f"{label}: {pct}% ({status}) · reset in {reset}")
    return "\n".join(lines)


def check_auth_failure(html: str) -> bool:
    """Return True if html is a login page."""
    has_usage = (
        "rollingUsage:" in html
        and "weeklyUsage:" in html
        and "monthlyUsage:" in html
    )
    if has_usage:
        return False
    return "OpenAuth" in html or "Continue with GitHub" in html
