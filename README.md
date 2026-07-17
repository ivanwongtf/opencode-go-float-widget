# OpenCode Go Float Widget

A small, floating desktop widget that shows your **OpenCode Go** usage percentages — rolling, weekly, and monthly — in a semi-transparent, always-on-top window at the bottom-right of your screen.

<img width="410" height="71" alt="image" src="https://github.com/user-attachments/assets/cccfca42-ae2f-42e2-868a-8fee0c6c7093" />


## Features

- **Always on top**, undecorated, skip taskbar/pager
- **Auto-refresh** every 60 seconds
- **Color-coded badges**: green < 50%, amber 50–80%, red ≥ 80%
- **Draggable** with left-click
- **Right-click menu**: Refresh / Open Go Page / Quit
- **Tooltip** with reset times
- **Login prompt** on missing / expired auth (throttled to once every 10 minutes)

## Requirements

- Python 3.9+

### Linux

- Linux with X11
- GTK 3
- PyGObject

### macOS

- macOS 11+
- PySide6

## Install

### 1. Clone

```bash
git clone https://github.com/sebastian93921/opencode-go-float-widget.git
cd opencode-go-float-widget
```

### 2. Install dependencies

#### Linux

On Debian / Ubuntu / Kali:

```bash
sudo apt update
sudo apt install python3-gi python3-gi-cairo gir1.2-gtk-3.0
```

Or with pip:

```bash
pip install -r requirements.txt
```

#### macOS

```bash
pip install -r requirements_mac.txt
```

### 3. Run the installer

The installer will prompt for your OpenCode **Workspace ID** and **auth cookie**, save them securely, and set up autostart.

#### Linux

```bash
./install_linux.sh
```

#### macOS

```bash
./install_mac.sh
```

### 4. Run manually

If you did not enable autostart, or want to run without installing:

#### Linux

```bash
export OPENCODE_WORKSPACE_ID='wrk_...'
export OPENCODE_AUTH='auth=Fe26.2**...'
./opencode_go_float_widget.py
```

#### macOS

```bash
export OPENCODE_WORKSPACE_ID='wrk_...'
export OPENCODE_AUTH='auth=Fe26.2**...'
./opencode_go_float_widget_mac.py
```

## Autostart on login

Both installers set up autostart automatically:

- **Linux**: creates `~/.config/autostart/opencode-go-float-widget.desktop` and reads credentials from `~/.config/environment.d/99-opencode-go-float-widget.conf`.
- **macOS**: creates a LaunchAgent at `~/Library/LaunchAgents/com.opencode.go-float-widget.plist` and reads credentials from `~/.config/opencode-go-float-widget/env` via a wrapper script.

To update credentials later, just re-run the installer.

## Configuration

| Variable | Description | Default |
|----------|-------------|---------|
| `OPENCODE_WORKSPACE_ID` | OpenCode workspace ID | *(required)* |
| `OPENCODE_AUTH` | Full `auth=…` cookie value | *(required)* |
| `OPENCODE_REFRESH_SECONDS` | Refresh interval in seconds | `60` |

## Uninstall

### Linux

```bash
rm ~/.config/autostart/opencode-go-float-widget.desktop
rm ~/.config/environment.d/99-opencode-go-float-widget.conf
rm -rf ~/.local/state/opencode-go-usage-indicator
rm ~/.local/bin/opencode_go_float_widget.py
```

### macOS

```bash
launchctl bootout gui/$(id -u) ~/Library/LaunchAgents/com.opencode.go-float-widget.plist
rm ~/Library/LaunchAgents/com.opencode.go-float-widget.plist
rm -rf ~/.config/opencode-go-float-widget
rm -rf ~/Library/Application\ Support/opencode-go-usage-indicator
rm -rf ~/Library/Logs/opencode-go-float-widget.log
rm ~/.local/bin/opencode_go_float_widget_mac.py
rm ~/.local/bin/core.py
rm ~/.local/bin/opencode-go-float-widget.wrapper.sh
```

## License

MIT
