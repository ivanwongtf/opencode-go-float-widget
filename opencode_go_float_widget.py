#!/usr/bin/env python3
"""Floating desktop widget for OpenCode Go usage.

Displays rolling / weekly / monthly usage percentages in a small,
semi-transparent, always-on-top window at the bottom-right of the screen.

Requirements:
    - Python 3 + PyGObject (GTK 3)
    - OPENCODE_AUTH environment variable set to the full cookie fragment
      (e.g. ``auth=Fe26.2**...``)

Usage:
    export OPENCODE_AUTH='auth=Fe26.2**...'
    ./opencode_go_float_widget.py
"""

# ── Imports ────────────────────────────────────────────────────────────────

import json
import os
import re
import subprocess
import time
import urllib.error
import urllib.request
from pathlib import Path

import gi

gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
from gi.repository import Gdk, GLib, Gtk  # noqa: E402

# ── Constants ──────────────────────────────────────────────────────────────

BASE_URL = "https://opencode.ai/workspace"

AUTH_ENV_VAR = "OPENCODE_AUTH"
WORKSPACE_ENV_VAR = "OPENCODE_WORKSPACE_ID"

def _go_url():
    """Build the Go page URL from the environment."""
    workspace_id = os.environ.get(WORKSPACE_ENV_VAR)
    if not workspace_id:
        raise ValueError(f"{WORKSPACE_ENV_VAR} environment variable not set")
    return f"{BASE_URL}/{workspace_id}/go"
REFRESH_INTERVAL_SECONDS = int(os.environ.get("OPENCODE_REFRESH_SECONDS", "60"))
THROTTLE_COOLDOWN_SECONDS = 600  # 10 minutes
STATE_DIR = Path.home() / ".local" / "state" / "opencode-go-usage-indicator"
STATE_FILE = STATE_DIR / "last_browser_prompt_epoch"

USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)
REQUEST_TIMEOUT = 15

# Margin from screen/workarea edge when positioning at bottom-right
EDGE_MARGIN_PX = 0

# Color thresholds:  pct < 50 → green,  50 ≤ pct < 80 → amber,  pct ≥ 80 → red
GREEN_BG = "#2E7D32"
AMBER_BG = "#F9A825"
RED_BG = "#C62828"

WINDOW_LABELS = {
    "rolling": "Rolling",
    "weekly": "Weekly",
    "monthly": "Monthly",
}

# ── CSS ────────────────────────────────────────────────────────────────────

CSS = b"""
#go-float-window {
    background-color: transparent;
}
#go-float-frame {
    background-color: alpha(#1a1a1e, 0.88);
    border: 1px solid alpha(#ffffff, 0.12);
    border-radius: 10px;
    padding: 0px;
}
#go-title {
    color: #e0e0e0;
    font-size: 10.5px;
    font-weight: 600;
    letter-spacing: 0.5px;
    padding: 0 0 3px 0;
}
#go-row-label {
    color: #9e9e9e;
    font-size: 10px;
    font-weight: 500;
    min-width: 46px;
}
.go-badge {
    font-size: 10.5px;
    font-weight: 700;
    padding: 1px 7px;
    border-radius: 4px;
    min-width: 42px;
}
.go-badge-green { background-color: @green_bg; color: #ffffff; }
.go-badge-amber { background-color: @amber_bg; color: #111111; }
.go-badge-red   { background-color: @red_bg;   color: #ffffff; }
.go-badge-grey  { background-color: #444444;    color: #aaaaaa; }
#go-error-label {
    color: #ef5350;
    font-size: 10px;
    font-weight: 600;
    padding-top: 4px;
}
#go-status-line {
    color: #777777;
    font-size: 9px;
    padding-top: 2px;
}
"""

# ── HTTP / parsing helpers ─────────────────────────────────────────────────


def color_class_for(pct):
    """Return a CSS class name suffix for the usage *pct*."""
    if pct < 50:
        return "green"
    if pct < 80:
        return "amber"
    return "red"


def fetch():
    """Fetch the Go page HTML.

    Raises:
        ValueError:  If OPENCODE_WORKSPACE_ID or OPENCODE_AUTH is unset.
        urllib.error.URLError:  Network-level failure.
        urllib.error.HTTPError:  Non-2xx response.
    """
    workspace_id = os.environ.get(WORKSPACE_ENV_VAR)
    if not workspace_id:
        raise ValueError(f"{WORKSPACE_ENV_VAR} environment variable not set")
    auth_cookie = os.environ.get(AUTH_ENV_VAR)
    if not auth_cookie:
        raise ValueError(f"{AUTH_ENV_VAR} environment variable not set")

    req = urllib.request.Request(
        _go_url(),
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


def _js_obj_to_dict(js_str):
    """Convert a flat JS object literal to a Python dict."""
    s = js_str.strip()
    s = s.replace("!0", "true").replace("!1", "false")
    s = re.sub(r"(\b\w+)(?=\s*:)", r'"\1"', s)
    return json.loads(s)


def parse(html):
    """Extract rolling/weekly/monthly usage dicts from SSR HTML.

    Each dict: status (str), resetInSec (int), usagePercent (int).
    Raises ValueError / json.JSONDecodeError on failure.
    """
    keys = {
        "rolling": r"rollingUsage:\$\w+\[\d+\]=",
        "weekly": r"weeklyUsage:\$\w+\[\d+\]=",
        "monthly": r"monthlyUsage:\$\w+\[\d+\]=",
    }
    result = {}
    for name, pattern in keys.items():
        m = re.search(pattern + r"(\{[^}]+\})", html)
        if not m:
            raise ValueError(f"Could not find {name} usage object in HTML")
        data = _js_obj_to_dict(m.group(1))
        result[name] = {
            "status": str(data["status"]),
            "resetInSec": int(data["resetInSec"]),
            "usagePercent": int(data["usagePercent"]),
        }
    return result


def format_reset_time(seconds):
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


def format_tooltip(usage):
    """Multi-line tooltip with reset times."""
    lines = []
    for key, label in WINDOW_LABELS.items():
        item = usage[key]
        pct = item["usagePercent"]
        status = item["status"]
        reset = format_reset_time(item["resetInSec"])
        lines.append(f"{label}: {pct}% ({status}) · reset in {reset}")
    return "\n".join(lines)


def check_auth_failure(html):
    """Return True if html is a login page."""
    has_usage = (
        "rollingUsage:" in html
        and "weeklyUsage:" in html
        and "monthlyUsage:" in html
    )
    if has_usage:
        return False
    return "OpenAuth" in html or "Continue with GitHub" in html


def throttled_browser_prompt():
    """Open Go page in default browser, throttled to once per cooldown."""
    try:
        url = _go_url()
    except ValueError:
        return False
    now = int(time.time())
    if STATE_FILE.exists():
        try:
            last = int(STATE_FILE.read_text().strip())
            if now - last < THROTTLE_COOLDOWN_SECONDS:
                return False
        except (ValueError, OSError):
            pass
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(str(now))
    try:
        subprocess.Popen(
            ["xdg-open", url],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return True
    except FileNotFoundError:
        return False


def open_browser():
    """Open Go page in default browser (unthrottled)."""
    try:
        url = _go_url()
    except ValueError:
        return
    try:
        subprocess.Popen(
            ["xdg-open", url],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except FileNotFoundError:
        pass


# ── Widget ─────────────────────────────────────────────────────────────────


class GoUsageWidget(Gtk.Window):
    """Floating always-on-top widget showing OpenCode Go usage."""

    def __init__(self):
        super().__init__(title="OpenCode Go Usage")
        self.set_name("go-float-window")

        # Window properties: undecorated, always-on-top, skip taskbar/pager
        self.set_decorated(False)
        self.set_keep_above(True)
        self.set_skip_taskbar_hint(True)
        self.set_skip_pager_hint(True)
        self.set_type_hint(Gdk.WindowTypeHint.DOCK)
        self.set_accept_focus(False)
        self.set_resizable(False)
        self.set_app_paintable(True)
        self.set_default_size(400, 60)

        # Event mask for dragging and right-click
        self.add_events(
            Gdk.EventMask.BUTTON_PRESS_MASK
            | Gdk.EventMask.BUTTON_RELEASE_MASK
            | Gdk.EventMask.POINTER_MOTION_MASK
        )

        # Drag state
        self._dragging = False
        self._drag_start_x = 0
        self._drag_start_y = 0
        self._drag_origin_x = 0
        self._drag_origin_y = 0

        # Try RGBA visual for transparency
        self._setup_visual()

        # Apply CSS
        self._apply_css()

        # Build UI
        self._build_ui()

        # Signals
        self.connect("button-press-event", self._on_button_press)
        self.connect("button-release-event", self._on_button_release)
        self.connect("motion-notify-event", self._on_motion)
        self.connect("draw", self._on_draw)
        self.connect("destroy", Gtk.main_quit)

        # Position and show
        self.show_all()
        self._hide_error()
        GLib.idle_add(self._position_bottom_right)

        # Initial fetch
        self._refresh()

        # Auto-refresh
        GLib.timeout_add_seconds(REFRESH_INTERVAL_SECONDS, self._refresh)

    def _setup_visual(self):
        """Enable RGBA visual for compositing transparency."""
        screen = self.get_screen()
        visual = screen.get_rgba_visual()
        if visual is not None:
            self.set_visual(visual)

    def _apply_css(self):
        """Install the widget CSS provider."""
        css_text = CSS
        css_text = css_text.replace(b"@green_bg", GREEN_BG.encode())
        css_text = css_text.replace(b"@amber_bg", AMBER_BG.encode())
        css_text = css_text.replace(b"@red_bg", RED_BG.encode())

        provider = Gtk.CssProvider()
        provider.load_from_data(css_text)
        Gtk.StyleContext.add_provider_for_screen(
            self.get_screen(),
            provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
        )

    def _build_ui(self):
        """Construct the widget content."""
        frame = Gtk.Frame()
        frame.set_name("go-float-frame")
        frame.set_shadow_type(Gtk.ShadowType.NONE)
        self.add(frame)

        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        vbox.set_margin_top(8)
        vbox.set_margin_bottom(8)
        vbox.set_margin_start(14)
        vbox.set_margin_end(14)
        frame.add(vbox)

        title_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        title = Gtk.Label(label="OpenCode Go Usage")
        title.set_name("go-title")
        title.set_halign(Gtk.Align.START)
        title_row.pack_start(title, True, True, 0)

        self.status_label = Gtk.Label(label="refreshing…")
        self.status_label.set_name("go-status-line")
        self.status_label.set_halign(Gtk.Align.END)
        title_row.pack_end(self.status_label, False, False, 0)
        vbox.pack_start(title_row, False, False, 0)

        # Three badges side-by-side in one row
        badge_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=18)
        badge_row.set_halign(Gtk.Align.CENTER)
        self.badges = {}
        for key, label in WINDOW_LABELS.items():
            cell = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
            lbl = Gtk.Label(label=label)
            lbl.set_name("go-row-label")
            cell.pack_start(lbl, False, False, 0)

            badge = Gtk.Label(label="—")
            badge.set_name(f"go-badge-{key}")
            badge.get_style_context().add_class("go-badge")
            badge.get_style_context().add_class("go-badge-grey")
            cell.pack_start(badge, False, False, 0)

            self.badges[key] = badge
            badge_row.pack_start(cell, False, False, 0)

        vbox.pack_start(badge_row, False, False, 0)

        # Error label (hidden initially)
        self.error_label = Gtk.Label()
        self.error_label.set_name("go-error-label")
        self.error_label.set_halign(Gtk.Align.START)
        self.error_label.set_no_show_all(True)
        vbox.pack_start(self.error_label, False, False, 0)

    def _on_draw(self, widget, cr):
        """Draw rounded-rect background for true transparency compositing."""
        alloc = widget.get_allocation()
        w, h = alloc.width, alloc.height

        radius = 10.0
        cr.new_sub_path()
        cr.arc(w - radius, radius, radius, -0.5 * 3.14159, 0)
        cr.arc(w - radius, h - radius, radius, 0, 0.5 * 3.14159)
        cr.arc(radius, h - radius, radius, 0.5 * 3.14159, 3.14159)
        cr.arc(radius, radius, radius, 3.14159, 1.5 * 3.14159)
        cr.close_path()

        cr.set_source_rgba(0.102, 0.102, 0.118, 0.88)
        cr.fill_preserve()

        cr.set_source_rgba(1, 1, 1, 0.12)
        cr.set_line_width(1.0)
        cr.stroke()

        if widget.get_child():
            self.propagate_draw(widget.get_child(), cr)
        return True

    def _position_bottom_right(self):
        """Move the window to the bottom-right of the primary monitor."""
        display = Gdk.Display.get_default()
        win = self.get_window()
        if win:
            monitor = display.get_monitor_at_window(win)
        else:
            monitor = display.get_monitor(0)
        workarea = monitor.get_workarea()

        req = self.get_preferred_size()[1]
        win_w = req.width
        win_h = req.height

        x = workarea.x + workarea.width - win_w - EDGE_MARGIN_PX
        y = workarea.y + workarea.height - win_h - EDGE_MARGIN_PX
        self.move(x, y)
        return False

    # ── Drag handlers ──────────────────────────────────────────────────────

    def _on_button_press(self, widget, event):
        if event.button == 1:
            self._dragging = True
            self._drag_start_x = event.x_root
            self._drag_start_y = event.y_root
            self._drag_origin_x, self._drag_origin_y = self.get_position()
            return True
        if event.button == 3:
            self._show_context_menu(event)
            return True
        return False

    def _on_button_release(self, widget, event):
        if event.button == 1:
            self._dragging = False
            return True
        return False

    def _on_motion(self, widget, event):
        if self._dragging:
            dx = int(event.x_root - self._drag_start_x)
            dy = int(event.y_root - self._drag_start_y)
            self.move(self._drag_origin_x + dx, self._drag_origin_y + dy)
            return True
        return False

    # ── Context menu ───────────────────────────────────────────────────────

    def _show_context_menu(self, event):
        menu = Gtk.Menu()

        item_refresh = Gtk.MenuItem(label="Refresh")
        item_refresh.connect("activate", lambda _: self._refresh())
        menu.append(item_refresh)

        item_open = Gtk.MenuItem(label="Open Go Page")
        item_open.connect("activate", lambda _: open_browser())
        menu.append(item_open)

        menu.append(Gtk.SeparatorMenuItem())

        item_quit = Gtk.MenuItem(label="Quit")
        item_quit.connect("activate", lambda _: Gtk.main_quit())
        menu.append(item_quit)

        menu.show_all()
        menu.popup_at_pointer(event)

    # ── Refresh logic ──────────────────────────────────────────────────────

    def _refresh(self):
        """Fetch + parse + update labels. Runs on every tick."""
        if not os.environ.get(WORKSPACE_ENV_VAR):
            self._show_error(
                "Workspace needed",
                f"Set the {WORKSPACE_ENV_VAR} environment variable to your "
                f"OpenCode workspace ID (e.g. wrk_01KXNRH9RH9JS746CTPEV1R7NA).",
            )
            self._set_all_badges_grey()
            self.status_label.set_text("no workspace")
            return True

        if not os.environ.get(AUTH_ENV_VAR):
            self._show_error(
                "Login needed",
                f"Set the {AUTH_ENV_VAR} environment variable to your "
                f"OpenCode auth cookie (e.g. auth=Fe26.2**...)",
            )
            self._set_all_badges_grey()
            self.status_label.set_text("no auth")
            throttled_browser_prompt()
            return True

        try:
            html = fetch()
        except urllib.error.URLError:
            self._show_error("offline", f"Could not reach {_go_url()}")
            self.status_label.set_text("offline")
            return True
        except (OSError, ValueError):
            self._show_error("offline", f"Could not reach {_go_url()}")
            self.status_label.set_text("error")
            return True

        if check_auth_failure(html):
            self._show_error(
                "Auth needed",
                "Authentication expired. Right-click → Open Go Page "
                "to re-login, then update the environment variable.",
            )
            self._set_all_badges_grey()
            self.status_label.set_text("auth expired")
            throttled_browser_prompt()
            return True

        try:
            usage = parse(html)
        except (ValueError, json.JSONDecodeError, KeyError):
            self._show_error("parse error", "Could not parse usage data")
            self.status_label.set_text("parse error")
            return True

        self._hide_error()
        for key in ("rolling", "weekly", "monthly"):
            pct = usage[key]["usagePercent"]
            self._update_badge(key, pct)

        self.set_tooltip_text(format_tooltip(usage))
        self.status_label.set_text(f"updated {time.strftime('%H:%M:%S')}")
        return True

    def _update_badge(self, key, pct):
        """Update a single badge label + CSS class."""
        badge = self.badges[key]
        badge.set_text(f"{pct}%")
        ctx = badge.get_style_context()
        for cls in (
            "go-badge-green",
            "go-badge-amber",
            "go-badge-red",
            "go-badge-grey",
        ):
            ctx.remove_class(cls)
        ctx.add_class(f"go-badge-{color_class_for(pct)}")

    def _set_all_badges_grey(self):
        for key in self.badges:
            badge = self.badges[key]
            badge.set_text("—")
            ctx = badge.get_style_context()
            for cls in ("go-badge-green", "go-badge-amber", "go-badge-red"):
                ctx.remove_class(cls)
            ctx.add_class("go-badge-grey")

    def _show_error(self, text, tooltip=""):
        self.error_label.set_text(text)
        self.error_label.show()
        if tooltip:
            self.set_tooltip_text(tooltip)

    def _hide_error(self):
        self.error_label.hide()
        self.set_tooltip_text("")


# ── Entry point ────────────────────────────────────────────────────────────


def main():
    GoUsageWidget()
    Gtk.main()


if __name__ == "__main__":
    main()
