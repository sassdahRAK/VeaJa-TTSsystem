#!/bin/bash
# Double-click this file (or add to Login Items) to run Veaja without a terminal.
cd "$(dirname "$0")"

# Force Qt to use XCB (X11/XWayland) on Linux so transparency, always-on-top,
# and window positioning work correctly (native Wayland plugin lacks these).
if [ "$(uname)" = "Linux" ]; then
    export QT_QPA_PLATFORM="${QT_QPA_PLATFORM:-xcb}"
fi

exec /usr/local/bin/python3 main.py
