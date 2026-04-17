"""
gui/pages/analyse_mixin.py — Analyse Page
==========================================
Displays usage analytics:
  • App usage bar chart  — how much each feature has been used
  • API credit pie chart — usage vs daily limit per connected API
  • Session stats        — total sessions, words read, time saved

All data is tracked locally in profile.json under "usage_stats".
Charts are drawn with QPainter — no external dependencies.
"""

import math
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QFrame, QSizePolicy
)
from PyQt6.QtCore import Qt, QRectF, QTimer
from PyQt6.QtGui import QPainter, QColor, QPen, QBrush, QFont, QPainterPath

# ── Daily credit limits per API (approximate free-tier / standard limits) ─────
_API_DAILY_LIMITS = {
    "api_key_openai":          {"name": "OpenAI",          "limit": 1_000,   "unit": "req"},
    "api_key_gemini":          {"name": "Gemini",          "limit": 1_500,   "unit": "req"},
    "api_key_claude":          {"name": "Claude",          "limit": 1_000,   "unit": "req"},
    "api_key_aistudio":        {"name": "AI Studio",       "limit": 1_500,   "unit": "req"},
    "api_key_mistral":         {"name": "Mistral",         "limit": 500,     "unit": "req"},
    "api_key_cohere":          {"name": "Cohere",          "limit": 1_000,   "unit": "req"},
    "api_key_deepl":           {"name": "DeepL",           "limit": 500_000, "unit": "chars"},
    "api_key_libretranslate":  {"name": "LibreTranslate",  "limit": 10_000,  "unit": "chars"},
    "api_key_elevenlabs":      {"name": "ElevenLabs",      "limit": 10_000,  "unit": "chars"},
    "api_key_stability":       {"name": "Stability AI",    "limit": 25,      "unit": "img"},
    "api_key_harvey":          {"name": "Harvey AI",       "limit": 100,     "unit": "req"},
    "api_key_azure_health":    {"name": "Azure Health",    "limit": 500,     "unit": "req"},
    "api_key_bloomberg":       {"name": "Bloomberg GPT",   "limit": 100,     "unit": "req"},
    "api_key_semantic_scholar":{"name": "Semantic Scholar","limit": 100,     "unit": "req"},
}

# ── Feature usage keys ────────────────────────────────────────────────────────
_FEATURES = [
    ("Read aloud",  "usage_read",      "#4caf50"),
    ("Summary",     "usage_summary",   "#2196f3"),
    ("Translate",   "usage_translate", "#ff9800"),
    ("Code",        "usage_code",      "#9c27b0"),
    ("Generate",    "usage_generate",  "#e91e63"),
    ("Overlay",     "usage_overlay",   "#00bcd4"),
]

# Palette for pie slices
_PIE_COLORS = [
    "#4caf50", "#2196f3", "#ff9800", "#9c27b0",
    "#e91e63", "#00bcd4", "#ff5722", "#607d8b",
    "#795548", "#cddc39", "#f44336", "#3f51b5",
]


class AnalyseMixin:
    """Mixin providing the Analyse page for MainWindow."""

    def _build_analyse_page(self) -> QWidget:
        page = QWidget()
        page.setObjectName("contentPage")
        lay = QVBoxLayout(page)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        # Top bar
        top = QWidget()
        top.setObjectName("pageTopAction")
        t_lay = QHBoxLayout(top)
        t_lay.setContentsMargins(32, 14, 32, 10)
        title = QLabel("Analyse")
        title.setObjectName("pageTitle")
        t_lay.addWidget(title)
        t_lay.addStretch()
        refresh_btn = QPushButton("Refresh")
        refresh_btn.setObjectName("btnOutline")
        refresh_btn.setFixedSize(90, 32)
        refresh_btn.clicked.connect(self._refresh_analyse)
        t_lay.addWidget(refresh_btn)
        lay.addWidget(top)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setObjectName("settingsScroll")

        sc = QWidget()
        sc_lay = QVBoxLayout(sc)
        sc_lay.setContentsMargins(32, 12, 32, 32)
        sc_lay.setSpacing(24)

        # ── Session stats row ─────────────────────────────────────────────
        stats_row = QHBoxLayout()
        stats_row.setSpacing(16)
        self._stat_cards: list[tuple[QLabel, QLabel]] = []
        for title_text, key, icon in [
            ("Total Sessions",  "usage_sessions",  "📖"),
            ("Words Read",      "usage_words",     "📝"),
            ("Summaries Made",  "usage_summary",   "📋"),
            ("Translations",    "usage_translate", "🌐"),
        ]:
            card = QWidget()
            card.setObjectName("infoCard")
            c_lay = QVBoxLayout(card)
            c_lay.setContentsMargins(16, 12, 16, 12)
            c_lay.setSpacing(4)
            icon_lbl = QLabel(f"{icon}  {title_text}")
            icon_lbl.setObjectName("settingsLabel")
            icon_lbl.setStyleSheet("font-size: 11px;")
            val_lbl = QLabel("0")
            val_lbl.setObjectName("cardTitle")
            val_lbl.setStyleSheet("font-size: 22px; font-weight: 700;")
            c_lay.addWidget(icon_lbl)
            c_lay.addWidget(val_lbl)
            stats_row.addWidget(card, 1)
            self._stat_cards.append((val_lbl, key))
        sc_lay.addLayout(stats_row)

        # ── Feature usage bar chart ───────────────────────────────────────
        bar_lbl = QLabel("Feature Usage")
        bar_lbl.setObjectName("shapeSectionLabel")
        sc_lay.addWidget(bar_lbl)

        self._bar_chart = _BarChartWidget()
        self._bar_chart.setFixedHeight(200)
        sc_lay.addWidget(self._bar_chart)

        # ── API credit usage ──────────────────────────────────────────────
        api_lbl = QLabel("API Credit Usage  (today vs daily limit)")
        api_lbl.setObjectName("shapeSectionLabel")
        sc_lay.addWidget(api_lbl)

        charts_row = QHBoxLayout()
        charts_row.setSpacing(20)

        self._pie_chart = _PieChartWidget()
        self._pie_chart.setFixedSize(220, 220)
        charts_row.addWidget(self._pie_chart)

        # Legend
        self._pie_legend = QWidget()
        self._pie_legend.setObjectName("featureBox")
        legend_lay = QVBoxLayout(self._pie_legend)
        legend_lay.setContentsMargins(0, 0, 0, 0)
        legend_lay.setSpacing(6)
        self._legend_items_lay = legend_lay
        charts_row.addWidget(self._pie_legend, 1)
        sc_lay.addLayout(charts_row)

        # ── API usage bars ────────────────────────────────────────────────
        self._api_bars_widget = QWidget()
        self._api_bars_widget.setObjectName("featureBox")
        self._api_bars_lay = QVBoxLayout(self._api_bars_widget)
        self._api_bars_lay.setContentsMargins(0, 0, 0, 0)
        self._api_bars_lay.setSpacing(10)
        sc_lay.addWidget(self._api_bars_widget)

        sc_lay.addStretch()
        scroll.setWidget(sc)
        lay.addWidget(scroll, 1)

        # Populate on first show
        QTimer.singleShot(0, self._refresh_analyse)
        return page

    # ── Data refresh ──────────────────────────────────────────────────────────

    def _refresh_analyse(self):
        profile = getattr(self, "_last_profile_cache", {})
        stats   = profile.get("usage_stats", {})

        # Stat cards
        for val_lbl, key in self._stat_cards:
            val_lbl.setText(f"{stats.get(key, 0):,}")

        # Bar chart — feature usage
        bar_data = []
        max_val = 1
        for label, key, color in _FEATURES:
            v = stats.get(key, 0)
            bar_data.append((label, v, color))
            max_val = max(max_val, v)
        self._bar_chart.set_data(bar_data, max_val)

        # Pie chart — API usage share
        api_usage = stats.get("api_usage", {})
        connected = [
            (k, info) for k, info in _API_DAILY_LIMITS.items()
            if profile.get(k, "").strip()
        ]

        pie_data = []
        for i, (k, info) in enumerate(connected):
            used  = api_usage.get(k, 0)
            limit = info["limit"]
            pct   = min(used / limit, 1.0) if limit else 0
            color = _PIE_COLORS[i % len(_PIE_COLORS)]
            pie_data.append((info["name"], pct, used, limit, info["unit"], color))

        self._pie_chart.set_data(pie_data)

        # Rebuild legend
        while self._legend_items_lay.count():
            item = self._legend_items_lay.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if not pie_data:
            no_lbl = QLabel("No API keys connected yet.\nAdd keys in My API Key to track usage.")
            no_lbl.setObjectName("settingsLabel")
            no_lbl.setWordWrap(True)
            self._legend_items_lay.addWidget(no_lbl)
        else:
            for name, pct, used, limit, unit, color in pie_data:
                row = QHBoxLayout()
                dot = QLabel("●")
                dot.setStyleSheet(f"color: {color}; font-size: 14px; background: transparent;")
                dot.setFixedWidth(18)
                row.addWidget(dot)
                txt = QLabel(f"{name}  —  {used:,} / {limit:,} {unit}  ({pct*100:.1f}%)")
                txt.setObjectName("cardBody")
                txt.setStyleSheet("font-size: 12px;")
                row.addWidget(txt, 1)
                w = QWidget()
                w.setLayout(row)
                self._legend_items_lay.addWidget(w)

        # Rebuild per-API usage bars
        while self._api_bars_lay.count():
            item = self._api_bars_lay.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        for name, pct, used, limit, unit, color in pie_data:
            self._api_bars_lay.addWidget(
                self._make_api_bar(name, pct, used, limit, unit, color)
            )

    def _make_api_bar(self, name: str, pct: float, used: int,
                      limit: int, unit: str, color: str) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(3)

        hdr = QHBoxLayout()
        name_lbl = QLabel(name)
        name_lbl.setObjectName("cardBody")
        name_lbl.setStyleSheet("font-size: 12px; font-weight: 600;")
        hdr.addWidget(name_lbl)
        hdr.addStretch()
        val_lbl = QLabel(f"{used:,} / {limit:,} {unit}")
        val_lbl.setObjectName("settingsLabel")
        val_lbl.setStyleSheet("font-size: 11px;")
        hdr.addWidget(val_lbl)
        lay.addLayout(hdr)

        bar_bg = QWidget()
        bar_bg.setFixedHeight(8)
        bar_bg.setObjectName("progRest")
        bar_bg.setStyleSheet("border-radius: 4px;")
        bar_lay = QHBoxLayout(bar_bg)
        bar_lay.setContentsMargins(0, 0, 0, 0)
        bar_lay.setSpacing(0)

        fill = QWidget()
        fill.setFixedHeight(8)
        fill.setStyleSheet(f"background: {color}; border-radius: 4px;")
        fill.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        # Width set after layout — use a timer
        bar_lay.addWidget(fill)
        bar_lay.addStretch()
        lay.addWidget(bar_bg)

        # Set fill width proportionally after widget is shown
        def _set_width(f=fill, bg=bar_bg, p=pct):
            w = max(4, int(bg.width() * p))
            f.setFixedWidth(w)
        QTimer.singleShot(50, _set_width)

        return w

    # ── Usage tracking helpers (called by other features) ─────────────────────

    def _track_usage(self, key: str, amount: int = 1):
        """Increment a usage counter in the profile. Call from feature handlers."""
        profile = getattr(self, "_last_profile_cache", {})
        stats = dict(profile.get("usage_stats", {}))
        stats[key] = stats.get(key, 0) + amount
        self.settings_save_requested.emit({"usage_stats": stats})


# ══════════════════════════════════════════════════════════════════════════════
# Chart widgets
# ══════════════════════════════════════════════════════════════════════════════

class _BarChartWidget(QWidget):
    """Simple horizontal bar chart drawn with QPainter."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._data: list[tuple[str, int, str]] = []
        self._max_val = 1
        self.setObjectName("featureBox")

    def set_data(self, data: list, max_val: int):
        self._data    = data
        self._max_val = max(max_val, 1)
        self.update()

    def paintEvent(self, _):
        if not self._data:
            return
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        is_dark = False
        try:
            from PyQt6.QtWidgets import QApplication
            app = QApplication.instance()
            if app:
                is_dark = app.palette().color(app.palette().ColorRole.Window).lightness() < 128
        except Exception:
            pass

        text_color = QColor("#cccccc" if is_dark else "#555555")
        bg_color   = QColor("#333333" if is_dark else "#eeeeee")

        W, H   = self.width(), self.height()
        n      = len(self._data)
        pad_l  = 90
        pad_r  = 50
        pad_t  = 10
        row_h  = (H - pad_t) // n

        font = QFont()
        font.setPointSize(9)
        p.setFont(font)

        for i, (label, val, color) in enumerate(self._data):
            y     = pad_t + i * row_h
            bar_w = int((W - pad_l - pad_r) * val / self._max_val)

            # Background track
            p.setBrush(QBrush(bg_color))
            p.setPen(Qt.PenStyle.NoPen)
            p.drawRoundedRect(QRectF(pad_l, y + 4, W - pad_l - pad_r, row_h - 10), 4, 4)

            # Fill bar
            if bar_w > 0:
                p.setBrush(QBrush(QColor(color)))
                p.drawRoundedRect(QRectF(pad_l, y + 4, bar_w, row_h - 10), 4, 4)

            # Label
            p.setPen(QPen(text_color))
            p.drawText(QRectF(0, y, pad_l - 6, row_h),
                       Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
                       label)

            # Value
            p.drawText(QRectF(pad_l + bar_w + 6, y, pad_r, row_h),
                       Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                       str(val))

        p.end()


class _PieChartWidget(QWidget):
    """Simple pie chart drawn with QPainter."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._data: list[tuple[str, float, int, int, str, str]] = []
        self.setObjectName("featureBox")

    def set_data(self, data: list):
        self._data = data
        self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        W, H   = self.width(), self.height()
        cx, cy = W // 2, H // 2
        r      = min(cx, cy) - 10

        if not self._data:
            p.setPen(QPen(QColor("#888888")))
            p.drawText(QRectF(0, 0, W, H), Qt.AlignmentFlag.AlignCenter,
                       "No API keys\nconnected")
            p.end()
            return

        # Draw slices proportional to usage percentage
        total_pct = sum(d[1] for d in self._data) or 1.0
        angle = 0.0

        for name, pct, used, limit, unit, color in self._data:
            span = (pct / total_pct) * 360.0 if total_pct > 0 else 360.0 / len(self._data)
            p.setBrush(QBrush(QColor(color)))
            p.setPen(Qt.PenStyle.NoPen)
            p.drawPie(QRectF(cx - r, cy - r, r * 2, r * 2),
                      int(angle * 16), int(span * 16))
            angle += span

        # Centre hole (donut)
        p.setBrush(QBrush(self.palette().window()))
        p.setPen(Qt.PenStyle.NoPen)
        inner_r = r * 0.55
        p.drawEllipse(QRectF(cx - inner_r, cy - inner_r, inner_r * 2, inner_r * 2))

        # Centre label
        p.setPen(QPen(QColor("#888888")))
        font = QFont()
        font.setPointSize(8)
        p.setFont(font)
        p.drawText(QRectF(cx - inner_r, cy - inner_r, inner_r * 2, inner_r * 2),
                   Qt.AlignmentFlag.AlignCenter, "API\nUsage")
        p.end()
