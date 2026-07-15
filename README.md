# opencode-go-float-widget

A small, floating GTK3 desktop widget that shows your **OpenCode Go** usage percentages — rolling, weekly, and monthly — in a semi-transparent, always-on-top window at the bottom-right of your screen.
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

- Linux with X11
- Python 3
- GTK 3
- PyGObject

## Install

### 1. Clone

```bash
git clone https://github.com/sebastian93921/opencode-go-float-widget.git
cd opencode-go-float-widget
```

### 2. Install dependencies

On Debian / Ubuntu / Kali:

```bash
sudo apt update
sudo apt install python3-gi python3-gi-cairo gir1.2-gtk-3.0
```

Or with pip:

```bash
pip install -r requirements.txt
```

### 3. Set your OpenCode auth cookie

Get the `auth=Fe26.2**…` cookie value from your browser after logging into OpenCode, then export it:

```bash
export OPENCODE_AUTH='auth=Fe26.2**...'
```

### 4. Run

```bash
./opencode_go_float_widget.py
```

## Autostart on login

```bash
# Copy the .desktop file
cp opencode-go-float-widget.desktop ~/.config/autostart/

# Save your auth cookie securely
mkdir -p ~/.config/environment.d
chmod 700 ~/.config/environment.d
cat > ~/.config/environment.d/99-opencode-go-float-widget.conf <<'EOF'
OPENCODE_AUTH=auth=Fe26.2**...
EOF
chmod 600 ~/.config/environment.d/99-opencode-go-float-widget.conf
```

The `.desktop` file reads the cookie from `~/.config/environment.d/99-opencode-go-float-widget.conf` at startup.

## Configuration

| Variable | Description | Default |
|----------|-------------|---------|
| `OPENCODE_AUTH` | Full `auth=…` cookie value | *(required)* |
| `OPENCODE_WORKSPACE_ID` | OpenCode workspace ID | `wrk_01KRDRXQXY5KDH20YM4A69TD61` |
| `OPENCODE_REFRESH_SECONDS` | Refresh interval in seconds | `60` |

## Uninstall

```bash
rm ~/.config/autostart/opencode-go-float-widget.desktop
rm ~/.config/environment.d/99-opencode-go-float-widget.conf
rm -rf ~/.local/state/opencode-go-usage-indicator
```

## License

MIT
