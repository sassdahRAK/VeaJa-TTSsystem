import os

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QStackedWidget, QStackedLayout,
    QLabel, QPushButton, QTextEdit, QScrollArea, QFrame, QSizePolicy
)
from PyQt6.QtCore import Qt, QTimer, QPoint
from PyQt6.QtGui import QPixmap, QPainter

from gui._window_shared import ASSETS, _make_square_pixmap  # noqa: F401


class DashboardMixin:
    """Mixin providing Dashboard page methods for MainWindow."""

    # ── Dashboard page ─────────────────────────────────────────────────────────

    def _build_dashboard_page(self) -> QWidget:
        page = QWidget()
        page.setObjectName("contentPage")
        lay = QVBoxLayout(page)
        lay.setContentsMargins(32, 28, 32, 28)
        lay.setSpacing(0)

        title = QLabel("Veaja Feature")
        title.setObjectName("pageTitle")
        lay.addWidget(title)
        lay.addSpacing(4)

        # Tab bar
        tab_bar = QWidget()
        tab_bar.setObjectName("tabBar")
        tb = QHBoxLayout(tab_bar)
        tb.setContentsMargins(0, 0, 0, 0)
        tb.setSpacing(0)

        self._tab_overlay_btn = QPushButton("Overlay")
        self._tab_overlay_btn.setObjectName("tabBtn")
        self._tab_overlay_btn.setCheckable(True)
        self._tab_overlay_btn.setChecked(True)
        self._tab_overlay_btn.setFixedHeight(36)
        self._tab_overlay_btn.clicked.connect(lambda: self._switch_tab(0))

        self._tab_text_btn = QPushButton("Text label")
        self._tab_text_btn.setObjectName("tabBtn")
        self._tab_text_btn.setCheckable(True)
        self._tab_text_btn.setChecked(False)
        self._tab_text_btn.setFixedHeight(36)
        self._tab_text_btn.clicked.connect(lambda: self._switch_tab(1))

        tb.addWidget(self._tab_overlay_btn)
        tb.addWidget(self._tab_text_btn)
        tb.addStretch()
        lay.addWidget(tab_bar)

        # Tab content stack
        self._tab_stack = QStackedWidget()
        self._tab_stack.addWidget(self._build_overlay_tab())  # 0
        self._tab_stack.addWidget(self._build_text_tab())     # 1
        lay.addWidget(self._tab_stack, 1)
        return page

    def _switch_tab(self, idx: int):
        self._tab_stack.setCurrentIndex(idx)
        self._tab_overlay_btn.setChecked(idx == 0)
        self._tab_text_btn.setChecked(idx == 1)

    def _build_overlay_tab(self) -> QWidget:
        frame = QWidget()
        frame.setObjectName("tabPage")
        lay = QVBoxLayout(frame)
        lay.setContentsMargins(0, 18, 0, 0)
        lay.setSpacing(12)

        # ── Bordered card ─────────────────────────────────────────────────
        overlay_box = QWidget()
        overlay_box.setObjectName("overlayBox")
        ob_lay = QVBoxLayout(overlay_box)
        ob_lay.setContentsMargins(0, 0, 0, 0)
        ob_lay.setSpacing(0)

        # Stack: text layer (bottom) + floating pill layer (top)
        stack_host = QWidget()
        stack_host.setObjectName("overlayStack")
        stack_lay = QStackedLayout(stack_host)
        stack_lay.setStackingMode(QStackedLayout.StackingMode.StackAll)
        stack_lay.setContentsMargins(0, 0, 0, 0)

        # ── Layer 0 — scrollable text preview ────────────────────────────
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet("background: transparent;")

        text_inner = QWidget()
        text_inner.setStyleSheet("background: transparent;")
        ti_lay = QVBoxLayout(text_inner)
        ti_lay.setContentsMargins(22, 22, 22, 22)
        ti_lay.setSpacing(0)

        self._overlay_text_view = QLabel(
            "Select text in any window and press  Ctrl+R  to read aloud, or press  Ctrl+C  and the overlay pill will appear automatically. The floating pill tracks each word in real-time so you can follow along without switching windows — no need to swap between apps or lose your place.\n\n"
            "Veaja is a real text-to-speech tool built for everyday use. It works across PDFs, emails, web pages, documents, and apps that have no built-in read-aloud feature — just select text and it reads, no copy-paste required. You get a choice of natural-sounding voices across multiple accents and languages, with speed control so you can slow down to absorb detail or speed up to skim. Every session is saved to your history so you can replay anything you've heard — useful for studying, reviewing notes, or catching up on long content hands-free. Veaja runs quietly in your system tray, ready the moment you need it, without cluttering your screen or interrupting your workflow.\n\n"
            "How Veaja works under the hood: when you select text and trigger a read, Veaja captures the selected content through your system clipboard or accessibility layer and passes it directly to a TTS engine. The engine processes the raw text, applies language detection to pick the right voice model, and streams synthesized audio to your output device in real-time. Word-level timestamps returned by the engine drive the highlight on the floating pill — each word lights up in sync with what is being spoken. The overlay itself is a transparent, always-on-top window that stays anchored to your screen corner and never interferes with clicks or focus in the window beneath it.\n\n"
            "The history system records every reading session — the original text, the voice used, the speed setting, and a timestamp — so you can revisit any session from the history page and replay it exactly as it was. Language detection runs automatically before synthesis so Veaja picks the correct pronunciation rules without you having to change settings manually. Speed adjustment is applied at the synthesis stage, not by resampling audio after the fact, which means faster or slower playback keeps the voice sounding natural rather than robotic or distorted."
        )
        self._overlay_text_view.setObjectName("bodyText")
        self._overlay_text_view.setWordWrap(True)
        self._overlay_text_view.setAlignment(
            Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft
        )
        ti_lay.addWidget(self._overlay_text_view)
        ti_lay.addStretch()
        scroll.setWidget(text_inner)
        stack_lay.addWidget(scroll)

        # ── Layer 1 — floating draggable pill (SVG icon, absolute position) ──
        _PILL_W, _PILL_H = 300, 98          # display size (SVG native: 219×72)

        pill_float = QWidget()
        pill_float.setObjectName("pillFloat")
        pill_float.setStyleSheet("background: transparent;")

        pill = QLabel(pill_float)
        pill.setObjectName("dashboardPill")
        pill.setFixedSize(_PILL_W, _PILL_H)
        pill.setCursor(Qt.CursorShape.OpenHandCursor)
        pill.setStyleSheet("background: transparent;")

        self._dashboard_pill_lbl  = pill
        self._pill_float          = pill_float
        self._pill_drag_start:  QPoint | None = None
        self._pill_drag_origin: QPoint | None = None

        def _pill_press(ev):
            if ev.button() == Qt.MouseButton.LeftButton:
                pill.setCursor(Qt.CursorShape.ClosedHandCursor)
                self._pill_drag_start  = ev.globalPosition().toPoint()
                self._pill_drag_origin = pill.pos()
            ev.accept()

        def _pill_move(ev):
            if self._pill_drag_start is None:
                return
            delta   = ev.globalPosition().toPoint() - self._pill_drag_start
            new_pos = self._pill_drag_origin + delta
            max_x   = pill_float.width()  - pill.width()
            max_y   = pill_float.height() - pill.height()
            pill.move(max(0, min(new_pos.x(), max_x)),
                      max(0, min(new_pos.y(), max_y)))
            ev.accept()

        def _pill_release(ev):
            pill.setCursor(Qt.CursorShape.OpenHandCursor)
            self._pill_drag_start  = None
            self._pill_drag_origin = None
            ev.accept()

        pill.mousePressEvent   = _pill_press
        pill.mouseMoveEvent    = _pill_move
        pill.mouseReleaseEvent = _pill_release

        # Render initial SVG (shape not known yet — default circle)
        QTimer.singleShot(0, self._update_dashboard_pill_icon)

        # Initial position: bottom-left of pill_float
        def _init_pill_pos():
            y = max(0, pill_float.height() - _PILL_H - 18)
            pill.move(18, y)
        QTimer.singleShot(0, _init_pill_pos)

        stack_lay.addWidget(pill_float)
        stack_lay.setCurrentIndex(1)

        ob_lay.addWidget(stack_host, 1)
        lay.addWidget(overlay_box, 1)

        # ── Hint bar (outside card) ───────────────────────────────────────
        hint = QLabel(
            "On window:  select text  and  Press  Ctrl+R  to read\n"
            "or  Ctrl+C  to pop up overlay"
        )
        hint.setObjectName("hintBar")
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(hint)
        return frame

    def _build_text_tab(self) -> QWidget:
        frame = QWidget()
        frame.setObjectName("tabPage")
        lay = QVBoxLayout(frame)
        lay.setContentsMargins(0, 18, 0, 0)
        lay.setSpacing(0)

        # ── Text input box ────────────────────────────────────────────────
        text_box = QWidget()
        text_box.setObjectName("textLabelBox")
        tb_lay = QVBoxLayout(text_box)
        tb_lay.setContentsMargins(0, 0, 0, 0)
        tb_lay.setSpacing(0)

        self._text_edit = QTextEdit()
        self._text_edit.setObjectName("textEdit")
        self._text_edit.setPlaceholderText("Paste or type text here to read aloud…")
        self._text_edit.textChanged.connect(self._on_text_changed)
        tb_lay.addWidget(self._text_edit, 1)

        # ── Footer: counter | Clear — Stop — Read ─────────────────────────
        footer = QWidget()
        footer.setObjectName("textFooter")
        ft_lay = QHBoxLayout(footer)
        ft_lay.setContentsMargins(18, 10, 18, 10)
        ft_lay.setSpacing(10)

        # Word / character counter (left)
        self._text_counter = QLabel("0 words · 0 chars")
        self._text_counter.setObjectName("settingsLabel")
        self._text_counter.setStyleSheet("font-size: 12px;")
        ft_lay.addWidget(self._text_counter)

        ft_lay.addStretch()

        # Clear button
        clear_btn = QPushButton("Clear")
        clear_btn.setObjectName("btnOutline")
        clear_btn.setFixedSize(80, 30)
        clear_btn.setToolTip("Clear text")
        clear_btn.clicked.connect(self._text_edit.clear)
        ft_lay.addWidget(clear_btn)

        # Read / Pause / Resume button
        self._read_btn = QPushButton("Read")
        self._read_btn.setObjectName("btnOutline")
        self._read_btn.setFixedSize(80, 30)
        self._read_btn.clicked.connect(self._on_read_clicked)
        ft_lay.addWidget(self._read_btn)

        tb_lay.addWidget(footer)
        lay.addWidget(text_box, 1)
        return frame

    def _on_text_changed(self):
        text = self._text_edit.toPlainText()
        words = len(text.split()) if text.strip() else 0
        chars = len(text)
        self._text_counter.setText(f"{words} word{'s' if words != 1 else ''} · {chars} char{'s' if chars != 1 else ''}")

    def _update_dashboard_pill_icon(self):
        """Re-render the dashboard pill using the correct overlay SVG (shape + theme)."""
        if not hasattr(self, "_dashboard_pill_lbl"):
            return
        from PyQt6.QtSvg import QSvgRenderer
        from PyQt6.QtWidgets import QApplication

        is_circle = (not hasattr(self, "_shape_circle")) or self._shape_circle.isChecked()
        if is_circle:
            svg_name = "overlay_circle_dark_icon.svg" if self._dark else "overlay_circle_light_icon.svg"
        else:
            svg_name = "overlay_retangle_dark_icon.svg" if self._dark else "overlay_retangle_light_icon.svg"

        svg_path = os.path.join(ASSETS, svg_name)
        if not os.path.exists(svg_path):
            return

        pill = self._dashboard_pill_lbl
        w, h = pill.width(), pill.height()
        app  = QApplication.instance()
        dpr  = app.primaryScreen().devicePixelRatio() if app else 1.0
        px   = QPixmap(int(w * dpr), int(h * dpr))
        px.fill(Qt.GlobalColor.transparent)
        renderer = QSvgRenderer(svg_path)
        painter  = QPainter(px)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        renderer.render(painter)
        painter.end()
        px.setDevicePixelRatio(dpr)
        pill.setPixmap(px)
