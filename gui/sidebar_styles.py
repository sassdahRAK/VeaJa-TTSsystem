# ── Sidebar QSS — LIGHT mode (sidebar is dark) ────────────────────────────────
_SIDEBAR_LIGHT_QSS = """
QWidget {
    background-color: #1a1a1a;
    color: #ffffff;
    font-family: -apple-system, 'Segoe UI', Arial, sans-serif;
}
QLabel  { background: transparent; color: #ffffff; font-size: 13px; }
QFrame  { background: #333333; max-height: 1px; border: none; }
QPushButton {
    background: transparent;
    border: none;
    color: #dddddd;
    font-size: 14px;
    text-align: left;
    padding: 2px 4px;
    border-radius: 4px;
}
QPushButton:hover   { color: #ffffff; background: rgba(255,255,255,0.08); }
/* Nav links: 50% opacity on active page, 100% otherwise */
QPushButton:checked { color: rgba(221,221,221,0.50); background: transparent; }
/* Dashboard — filled when active */
QPushButton#dashBtn {
    background: #ffffff;
    color: #1a1a1a;
    border: 1px solid #cccccc;
    border-radius: 5px;
    font-size: 14px;
    font-weight: 500;
    text-align: center;
    padding: 9px 0;
}
QPushButton#dashBtn:hover   { background: #f0f0f0; }
/* Dashboard — border-only when NOT active */
QPushButton#dashBtn:!checked {
    background: transparent;
    color: #aaaaaa;
    border: 1px solid rgba(255,255,255,0.25);
    font-weight: 400;
}
/* Override the general :checked dimming for dashBtn — keep it opaque when active */
QPushButton#dashBtn:checked { background: #ffffff; color: #1a1a1a; }
QPushButton#themeBtn {
    background: transparent;
    border: none;
    color: #aaaaaa;
    font-size: 17px;
    text-align: center;
    padding: 0;
    border-radius: 4px;
}
QPushButton#themeBtn:hover { background: rgba(255,255,255,0.1); color: #ffffff; }
QLabel#profileName { color: #ffffff; font-size: 15px; font-weight: 600; background: transparent; }
QLabel#helpLabel   { color: #cccccc; font-size: 13px; font-weight: 600; background: transparent; }
QLabel#editIcon    { color: #aaaaaa; font-size: 13px; background: transparent; }
"""

# ── Sidebar QSS — DARK mode (sidebar is light) ────────────────────────────────
_SIDEBAR_DARK_QSS = """
QWidget {
    background-color: #f0f0f0;
    color: #1a1a1a;
    font-family: -apple-system, 'Segoe UI', Arial, sans-serif;
}
QLabel  { background: transparent; color: #1a1a1a; font-size: 13px; }
QFrame  { background: #cccccc; max-height: 1px; border: none; }
QPushButton {
    background: transparent;
    border: none;
    color: #333333;
    font-size: 14px;
    text-align: left;
    padding: 2px 4px;
    border-radius: 4px;
}
QPushButton:hover   { color: #1a1a1a; background: rgba(0,0,0,0.07); }
/* Nav links: 50% opacity on active page, 100% otherwise */
QPushButton:checked { color: rgba(51,51,51,0.50); background: transparent; }
/* Dashboard — filled when active */
QPushButton#dashBtn {
    background: #1a1a1a;
    color: #ffffff;
    border: 1px solid #555555;
    border-radius: 5px;
    font-size: 14px;
    font-weight: 500;
    text-align: center;
    padding: 9px 0;
}
QPushButton#dashBtn:hover   { background: #333333; }
/* Dashboard — border-only when NOT active */
QPushButton#dashBtn:!checked {
    background: transparent;
    color: #888888;
    border: 1px solid rgba(0,0,0,0.20);
    font-weight: 400;
}
/* Override the general :checked dimming for dashBtn — keep it opaque when active */
QPushButton#dashBtn:checked { background: #1a1a1a; color: #ffffff; }
QPushButton#themeBtn {
    background: transparent;
    border: none;
    color: #666666;
    font-size: 17px;
    text-align: center;
    padding: 0;
    border-radius: 4px;
}
QPushButton#themeBtn:hover { background: rgba(0,0,0,0.07); color: #1a1a1a; }
QLabel#profileName { color: #1a1a1a; font-size: 15px; font-weight: 600; background: transparent; }
QLabel#helpLabel   { color: #555555; font-size: 13px; font-weight: 600; background: transparent; }
QLabel#editIcon    { color: #888888; font-size: 13px; background: transparent; }
"""
