#!/usr/bin/env bash
# Adds YAPAY VOLB to the application menu. Pass --autostart to also start it at login.
set -euo pipefail
DIR="$(cd "$(dirname "$0")/.." && pwd)"
ENTRY="[Desktop Entry]
Type=Application
Name=YAPAY VOLB
Comment=Personal AI desktop assistant
Exec=$DIR/run.sh
Icon=$DIR/ui/assets/volb_icon.svg
Terminal=false
Categories=Utility;
StartupWMClass=yapay-volb"
mkdir -p ~/.local/share/applications
echo "$ENTRY" > ~/.local/share/applications/yapay-volb.desktop
echo "✓ ~/.local/share/applications/yapay-volb.desktop"
if [[ "${1:-}" == "--autostart" ]]; then
  mkdir -p ~/.config/autostart
  echo "$ENTRY" > ~/.config/autostart/yapay-volb.desktop
  echo "✓ ~/.config/autostart/yapay-volb.desktop"
fi
