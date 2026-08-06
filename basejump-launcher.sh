#!/bin/bash
# Universal Desktop Environment Launcher for Atomic Basejump

# Use python to extract uiTheme from settings.json
THEME=$(python3 -c "
import json, os, pathlib
path = pathlib.Path.home() / '.config' / 'atomicbasejump' / 'settings.json'
try:
    print(json.load(open(path)).get('uiTheme', 'Auto'))
except:
    print('Auto')
")

if [[ "$THEME" == "GNOME" ]]; then
    exec python3 -m basejump.ui_gnome.main "$@"
elif [[ "$THEME" == "KDE" ]]; then
    exec python3 -m basejump.ui_kde.main "$@"
else
    # Auto fallback
    DESKTOP="${XDG_CURRENT_DESKTOP:-}"
    DESKTOP_LOWER=$(echo "$DESKTOP" | tr '[:upper:]' '[:lower:]')

    if [[ "$DESKTOP_LOWER" == *"gnome"* ]] || [[ "$DESKTOP_LOWER" == *"pantheon"* ]] || [[ "$DESKTOP_LOWER" == *"budgie"* ]]; then
        exec python3 -m basejump.ui_gnome.main "$@"
    fi

    exec python3 -m basejump.ui_kde.main "$@"
fi
