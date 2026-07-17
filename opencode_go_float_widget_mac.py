#!/usr/bin/env python3
# /// script
# requires-python = ">=3.9"
# dependencies = ["PySide6"]
# ///

from __future__ import annotations

import json
import os
import subprocess
import time
import urllib.error
import webbrowser
from pathlib import Path

from PySide6.QtCore import QPoint, Qt, QTimer
from PySide6.QtGui import QAction, QColor, QMouseEvent, QPaintEvent, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QApplication, QHBoxLayout, QLabel, QMenu, QVBoxLayout, QWidget

import core

STATE_DIR = Path.home() / "Library" / "Application Support" / "opencode-go-usage-indicator"
STATE_FILE = STATE_DIR / "last_browser_prompt_epoch"

EDGE_MARGIN_PX = 0

TITLE_STYLE = (
    "color: #e0e0e0; font-size: 10.5px; font-weight: 600;"
    " letter-spacing: 0.5px; padding: 0 0 3px 0;"
)
ROW_LABEL_STYLE = (
    "color: #9e9e9e; font-size: 10px; font-weight: 500; min-width: 46px;"
)
ERROR_STYLE = (
    "color: #ef5350; font-size: 10px; font-weight: 600; padding-top: 4px;"
)
STATUS_STYLE = "color: #777777; font-size: 9px; padding-top: 2px;"

_BADGE_COLORS: dict[str, tuple[str, str]] = {
    "green": (core.GREEN_BG, "#ffffff"),
    "amber": (core.AMBER_BG, "#111111"),
    "red": (core.RED_BG, "#ffffff"),
    "grey": ("#444444", "#aaaaaa"),
}



def _badge_stylesheet(bg: str, fg: str) -> str:
    return (
        "font-size: 10.5px; font-weight: 700; padding: 1px 7px;"
        f" border-radius: 4px; min-width: 42px; background-color: {bg}; color: {fg};"
    )


def throttled_browser_prompt() -> bool:
    now = int(time.time())
    if STATE_FILE.exists():
        try:
            last = int(STATE_FILE.read_text().strip())
            if now - last < core.THROTTLE_COOLDOWN_SECONDS:
                return False
        except (ValueError, OSError):
            pass
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(str(now))
    try:
        subprocess.Popen(
            ["open", core.go_url()],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return True
    except FileNotFoundError:
        webbrowser.open(core.go_url())
        return False


def open_browser() -> None:
    try:
        subprocess.Popen(
            ["open", core.go_url()],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except FileNotFoundError:
        webbrowser.open(core.go_url())




class GoUsageWidget(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("OpenCode Go Usage")
        self.setWindowFlags(
            Qt.FramelessWindowHint
            | Qt.WindowStaysOnTopHint
            | Qt.Tool
            | Qt.WindowDoesNotAcceptFocus
        )
        self.setAttribute(Qt.WA_TranslucentBackground)

        self._dragging = False
        self._drag_start = self._drag_origin = QPoint()

        self.badges: dict[str, QLabel] = {}

        self._build_ui()
        self.adjustSize()
        self._position_bottom_right()
        self._refresh()

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._refresh)
        self._timer.start(core.REFRESH_INTERVAL_SECONDS * 1000)

    def _build_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(14, 8, 14, 8)
        main_layout.setSpacing(4)

        # Title row
        title_row = QHBoxLayout()
        title_row.setSpacing(8)
        title = QLabel("OpenCode Go Usage")
        title.setStyleSheet(TITLE_STYLE)
        title_row.addWidget(title)
        title_row.addStretch()

        self.status_label = QLabel("refreshing…")
        self.status_label.setStyleSheet(STATUS_STYLE)
        title_row.addWidget(self.status_label)
        main_layout.addLayout(title_row)

        # Badge row
        badge_row = QHBoxLayout()
        badge_row.setSpacing(18)
        badge_row.addStretch()
        for key, label in core.WINDOW_LABELS.items():
            cell = QHBoxLayout()
            cell.setSpacing(4)
            lbl = QLabel(label)
            lbl.setStyleSheet(ROW_LABEL_STYLE)
            cell.addWidget(lbl)

            badge = QLabel("—")
            badge.setAlignment(Qt.AlignCenter)
            badge.setStyleSheet(_badge_stylesheet(*_BADGE_COLORS["grey"]))
            cell.addWidget(badge)
            self.badges[key] = badge
            badge_row.addLayout(cell)
        badge_row.addStretch()
        main_layout.addLayout(badge_row)

        # Error label (hidden initially)
        self.error_label = QLabel()
        self.error_label.setStyleSheet(ERROR_STYLE)
        self.error_label.hide()
        main_layout.addWidget(self.error_label)

    def paintEvent(self, _event: QPaintEvent) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        path = QPainterPath()
        rect = self.rect().adjusted(1, 1, -1, -1)
        path.addRoundedRect(rect, 10.0, 10.0)

        painter.fillPath(path, QColor(26, 26, 30, 224))
        pen = QPen(QColor(255, 255, 255, 31))
        pen.setWidthF(1.0)
        painter.setPen(pen)
        painter.drawPath(path)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.LeftButton:
            self._dragging = True
            self._drag_start = event.globalPosition().toPoint()
            self._drag_origin = self.frameGeometry().topLeft()
        elif event.button() == Qt.RightButton:
            self._show_context_menu(event.globalPosition().toPoint())

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self._dragging:
            delta = event.globalPosition().toPoint() - self._drag_start
            self.move(self._drag_origin + delta)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.LeftButton:
            self._dragging = False

    def _show_context_menu(self, pos: QPoint) -> None:
        menu = QMenu(self)

        refresh_action = QAction("Refresh", self)
        refresh_action.triggered.connect(self._refresh)
        menu.addAction(refresh_action)

        open_action = QAction("Open Go Page", self)
        open_action.triggered.connect(open_browser)
        menu.addAction(open_action)

        menu.addSeparator()

        quit_action = QAction("Quit", self)
        quit_action.triggered.connect(self.close)
        menu.addAction(quit_action)

        menu.exec(pos)

    def _position_bottom_right(self) -> None:
        screen = QApplication.primaryScreen().availableGeometry()
        size = self.size()
        x = screen.right() - size.width() - EDGE_MARGIN_PX
        y = screen.bottom() - size.height() - EDGE_MARGIN_PX
        self.move(x, y)

    def _refresh(self) -> None:
        if not os.environ.get(core.WORKSPACE_ENV_VAR):
            self._show_error(
                "Workspace needed",
                f"Set the {core.WORKSPACE_ENV_VAR} environment variable to your "
                f"OpenCode workspace ID (e.g. wrk_01KXNRH9RH9JS746CTPEV1R7NA).",
            )
            self._set_all_badges_grey()
            self.status_label.setText("no workspace")
            return

        if not os.environ.get(core.AUTH_ENV_VAR):
            self._show_error(
                "Login needed",
                f"Set the {core.AUTH_ENV_VAR} environment variable to your "
                f"OpenCode auth cookie (e.g. auth=Fe26.2**...)",
            )
            self._set_all_badges_grey()
            self.status_label.setText("no auth")
            throttled_browser_prompt()
            return

        try:
            html = core.fetch()
        except urllib.error.URLError:
            self._show_error("offline", f"Could not reach {core.go_url()}")
            self.status_label.setText("offline")
            return
        except (OSError, ValueError):
            self._show_error("offline", f"Could not reach {core.go_url()}")
            self.status_label.setText("error")
            return

        if core.check_auth_failure(html):
            self._show_error(
                "Auth needed",
                "Authentication expired. Right-click → Open Go Page "
                "to re-login, then update the environment variable.",
            )
            self._set_all_badges_grey()
            self.status_label.setText("auth expired")
            throttled_browser_prompt()
            return

        try:
            usage = core.parse(html)
        except (ValueError, json.JSONDecodeError, KeyError):
            self._show_error("parse error", "Could not parse usage data")
            self.status_label.setText("parse error")
            return

        self._hide_error()
        for key in ("rolling", "weekly", "monthly"):
            pct = getattr(usage, key).usagePercent
            self._update_badge(key, pct)

        self.setToolTip(core.format_tooltip(usage))
        self.status_label.setText(f"updated {time.strftime('%H:%M:%S')}")

    def _update_badge(self, key: str, pct: int) -> None:
        badge = self.badges[key]
        badge.setText(f"{pct}%")
        badge.setStyleSheet(_badge_stylesheet(*_BADGE_COLORS[core.color_class_for(pct)]))

    def _set_all_badges_grey(self) -> None:
        for badge in self.badges.values():
            badge.setText("—")
            badge.setStyleSheet(_badge_stylesheet(*_BADGE_COLORS["grey"]))

    def _show_error(self, text: str, tooltip: str = "") -> None:
        self.error_label.setText(text)
        self.error_label.show()
        if tooltip:
            self.setToolTip(tooltip)

    def _hide_error(self) -> None:
        self.error_label.hide()
        self.setToolTip("")



def main() -> None:
    app = QApplication([])
    app.setQuitOnLastWindowClosed(True)
    widget = GoUsageWidget()
    widget.show()
    try:
        import objc

        ns_window = objc.objc_object(c_void_p=widget.winId()).window()
        ns_window.setLevel_(25)
        ns_window.setCollectionBehavior_(1 | 16)
    except Exception:
        pass
    app.exec()


if __name__ == "__main__":
    main()
