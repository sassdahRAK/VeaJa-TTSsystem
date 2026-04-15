"""
gui/pages/dashboard_mixin.py — Dashboard Page
==============================================

Provides the Dashboard page UI and logic as a mixin for MainWindow.

Dashboard contains two tabs:
  • Overlay tab  — shows the text loaded from clipboard / selection.
                   Words are highlighted in yellow as the overlay pill reads.
  • Text label   — manual text entry area where the user types or pastes
                   text and clicks Read to begin playback.

The Read button cycles through three states:
  IDLE     → click → SPEAKING  (red button)
  SPEAKING → click → PAUSED    (orange button)
  PAUSED   → click → SPEAKING  (red button)
"""

import os

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QStackedWidget, QStackedLayout,
    QLabel, QPushButton, QTextEdit, QScrollArea, QFrame, QSizePolicy,
    QTableWidget, QTableWidgetItem, QHeaderView, QComboBox, QAbstractItemView,
    QApplication
)
from PyQt6.QtCore import Qt, QTimer, QPoint, QMimeData
from PyQt6.QtGui import QPixmap, QPainter, QDrag, QCursor

from gui._window_shared import ASSETS, _make_square_pixmap  # noqa: F401

# Canonical tab definitions: (label, index)
_TAB_DEFS = [
    ("Overlay",     0),
    ("Text label",  1),
    ("Summary",     2),
    ("Translate",   3),
]
_DEFAULT_TAB_ORDER = [0, 1, 2, 3]


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
        title.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        lay.addWidget(title)
        lay.addSpacing(4)

        # Fade the title out after 3 s using a QTimer + opacity steps
        self._dashboard_title = title
        QTimer.singleShot(3000, self._fade_dashboard_title)

        # Tab bar (drag-reorderable)
        self._tab_bar_widget = _DraggableTabBar(self)
        lay.addWidget(self._tab_bar_widget)

        # Tab content stack — always in canonical order (0-3)
        self._tab_stack = QStackedWidget()
        self._tab_stack.addWidget(self._build_overlay_tab())    # 0
        self._tab_stack.addWidget(self._build_text_tab())       # 1
        self._tab_stack.addWidget(self._build_summary_tab())    # 2
        self._tab_stack.addWidget(self._build_translate_tab())  # 3
        lay.addWidget(self._tab_stack, 1)
        return page

    def _switch_tab(self, canonical_idx: int):
        """Show the tab identified by its canonical index (0-3)."""
        self._tab_stack.setCurrentIndex(canonical_idx)
        self._tab_bar_widget.set_active(canonical_idx)

    def apply_tab_order(self, order: list):
        """Restore a saved tab order (list of canonical indices)."""
        self._tab_bar_widget.apply_order(order)

    def get_tab_order(self) -> list:
        """Return the current tab order as a list of canonical indices."""
        return self._tab_bar_widget.current_order()

    def _on_tab_order_changed(self):
        """Called by _DraggableTabBar after every reorder — persist via signal."""
        order = self.get_tab_order()
        # Emit settings_save_requested so AppController persists it
        self.settings_save_requested.emit({"tab_order": order})

    def _fade_dashboard_title(self):
        """Gradually fade the 'Veaja Feature' title to invisible over ~600 ms."""
        if not hasattr(self, "_dashboard_title"):
            return
        from PyQt6.QtWidgets import QGraphicsOpacityEffect
        effect = QGraphicsOpacityEffect(self._dashboard_title)
        self._dashboard_title.setGraphicsEffect(effect)
        self._dashboard_title_opacity = 1.0
        self._dashboard_title_effect  = effect

        def _step():
            self._dashboard_title_opacity -= 0.08
            if self._dashboard_title_opacity <= 0:
                self._dashboard_title_opacity = 0
                effect.setOpacity(0)
                self._dashboard_title.setVisible(False)
                return
            effect.setOpacity(self._dashboard_title_opacity)
            QTimer.singleShot(30, _step)

        _step()

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

    # ── Summary tab ────────────────────────────────────────────────────────────

    def _build_summary_tab(self) -> QWidget:
        frame = QWidget()
        frame.setObjectName("tabPage")
        lay = QVBoxLayout(frame)
        lay.setContentsMargins(0, 18, 0, 0)
        lay.setSpacing(12)

        # ── Sub-tab bar (Normal / Grid) ───────────────────────────────────
        sub_bar = QWidget()
        sub_bar.setObjectName("subTabBar")
        sb_lay = QHBoxLayout(sub_bar)
        sb_lay.setContentsMargins(0, 0, 0, 0)
        sb_lay.setSpacing(0)

        self._sum_normal_btn = QPushButton("Normal text")
        self._sum_normal_btn.setObjectName("subTabBtn")
        self._sum_normal_btn.setCheckable(True)
        self._sum_normal_btn.setChecked(True)
        self._sum_normal_btn.setFixedHeight(30)
        self._sum_normal_btn.clicked.connect(lambda: self._switch_summary_mode(0))

        self._sum_grid_btn = QPushButton("Grid text")
        self._sum_grid_btn.setObjectName("subTabBtn")
        self._sum_grid_btn.setCheckable(True)
        self._sum_grid_btn.setChecked(False)
        self._sum_grid_btn.setFixedHeight(30)
        self._sum_grid_btn.clicked.connect(lambda: self._switch_summary_mode(1))

        sb_lay.addWidget(self._sum_normal_btn)
        sb_lay.addWidget(self._sum_grid_btn)
        sb_lay.addStretch()
        lay.addWidget(sub_bar)

        # ── Input box ─────────────────────────────────────────────────────
        input_box = QWidget()
        input_box.setObjectName("featureBox")
        ib_lay = QVBoxLayout(input_box)
        ib_lay.setContentsMargins(0, 0, 0, 0)
        ib_lay.setSpacing(0)

        input_label = QLabel("Text to summarise")
        input_label.setObjectName("featureLabel")
        ib_lay.addWidget(input_label)

        self._summary_input = QTextEdit()
        self._summary_input.setObjectName("featureEdit")
        self._summary_input.setPlaceholderText("Paste or type the long content you want to summarise…")
        self._summary_input.setFixedHeight(130)
        ib_lay.addWidget(self._summary_input)
        lay.addWidget(input_box)

        # ── Action row ────────────────────────────────────────────────────
        action_row = QHBoxLayout()
        action_row.setContentsMargins(0, 0, 0, 0)
        action_row.setSpacing(10)
        action_row.addStretch()

        clear_sum_btn = QPushButton("Clear")
        clear_sum_btn.setObjectName("btnOutline")
        clear_sum_btn.setFixedSize(80, 30)
        clear_sum_btn.clicked.connect(self._clear_summary)
        action_row.addWidget(clear_sum_btn)

        summarise_btn = QPushButton("Summarise")
        summarise_btn.setObjectName("btnPrimary")
        summarise_btn.setFixedSize(100, 30)
        summarise_btn.clicked.connect(self._run_summary)
        action_row.addWidget(summarise_btn)
        lay.addLayout(action_row)

        # ── Output stack (normal paragraph / grid table) ──────────────────
        self._summary_output_stack = QStackedWidget()

        # — Normal text output —
        normal_out_box = QWidget()
        normal_out_box.setObjectName("featureBox")
        no_lay = QVBoxLayout(normal_out_box)
        no_lay.setContentsMargins(0, 0, 0, 0)
        no_lay.setSpacing(0)

        normal_out_label = QLabel("Summary")
        normal_out_label.setObjectName("featureLabel")
        no_lay.addWidget(normal_out_label)

        self._summary_normal_out = QTextEdit()
        self._summary_normal_out.setObjectName("featureEditReadOnly")
        self._summary_normal_out.setReadOnly(True)
        self._summary_normal_out.setPlaceholderText("Summary will appear here…")
        no_lay.addWidget(self._summary_normal_out, 1)
        self._summary_output_stack.addWidget(normal_out_box)  # index 0

        # — Grid text output —
        grid_out_box = QWidget()
        grid_out_box.setObjectName("featureBox")
        go_lay = QVBoxLayout(grid_out_box)
        go_lay.setContentsMargins(0, 0, 0, 0)
        go_lay.setSpacing(0)

        grid_out_label = QLabel("Key points")
        grid_out_label.setObjectName("featureLabel")
        go_lay.addWidget(grid_out_label)

        self._summary_grid_out = QTableWidget(0, 2)
        self._summary_grid_out.setObjectName("summaryGrid")
        self._summary_grid_out.setHorizontalHeaderLabels(["Point", "Detail"])
        self._summary_grid_out.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self._summary_grid_out.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self._summary_grid_out.verticalHeader().setVisible(False)
        self._summary_grid_out.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._summary_grid_out.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._summary_grid_out.setAlternatingRowColors(True)
        go_lay.addWidget(self._summary_grid_out, 1)
        self._summary_output_stack.addWidget(grid_out_box)  # index 1

        lay.addWidget(self._summary_output_stack, 1)
        return frame

    def _switch_summary_mode(self, idx: int):
        self._sum_normal_btn.setChecked(idx == 0)
        self._sum_grid_btn.setChecked(idx == 1)
        self._summary_output_stack.setCurrentIndex(idx)

    def _clear_summary(self):
        self._summary_input.clear()
        self._summary_normal_out.clear()
        self._summary_grid_out.setRowCount(0)

    def _run_summary(self):
        """Summarise the input text. Uses a simple extractive approach (no external API)."""
        text = self._summary_input.toPlainText().strip()
        if not text:
            return

        sentences = [s.strip() for s in text.replace("\n", " ").split(".") if s.strip()]

        # ── Normal text: first ~3 sentences as a paragraph ────────────────
        normal_result = ". ".join(sentences[:3])
        if normal_result and not normal_result.endswith("."):
            normal_result += "."
        self._summary_normal_out.setPlainText(normal_result)

        # ── Grid text: each sentence becomes a row ─────────────────────────
        self._summary_grid_out.setRowCount(0)
        for i, sentence in enumerate(sentences[:10], start=1):
            row = self._summary_grid_out.rowCount()
            self._summary_grid_out.insertRow(row)
            point_item = QTableWidgetItem(f"Point {i}")
            detail_item = QTableWidgetItem(sentence + ".")
            point_item.setTextAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
            detail_item.setTextAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
            self._summary_grid_out.setItem(row, 0, point_item)
            self._summary_grid_out.setItem(row, 1, detail_item)
        self._summary_grid_out.resizeRowsToContents()

    # ── Translate tab ──────────────────────────────────────────────────────────

    def _build_translate_tab(self) -> QWidget:
        frame = QWidget()
        frame.setObjectName("tabPage")
        lay = QVBoxLayout(frame)
        lay.setContentsMargins(0, 18, 0, 0)
        lay.setSpacing(12)

        # ── Language selector row ─────────────────────────────────────────
        lang_row = QHBoxLayout()
        lang_row.setContentsMargins(0, 0, 0, 0)
        lang_row.setSpacing(10)

        from_label = QLabel("From")
        from_label.setObjectName("featureLabel")
        from_label.setFixedWidth(36)
        lang_row.addWidget(from_label)

        self._translate_from_combo = QComboBox()
        self._translate_from_combo.setObjectName("translateCombo")
        self._translate_from_combo.setFixedHeight(30)
        for lang in ["Auto detect", "English", "Thai", "French", "Spanish",
                     "German", "Japanese", "Chinese", "Korean", "Arabic"]:
            self._translate_from_combo.addItem(lang)
        lang_row.addWidget(self._translate_from_combo)

        arrow_lbl = QLabel("→")
        arrow_lbl.setObjectName("featureLabel")
        arrow_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lang_row.addWidget(arrow_lbl)

        to_label = QLabel("To")
        to_label.setObjectName("featureLabel")
        to_label.setFixedWidth(20)
        lang_row.addWidget(to_label)

        self._translate_to_combo = QComboBox()
        self._translate_to_combo.setObjectName("translateCombo")
        self._translate_to_combo.setFixedHeight(30)
        for lang in ["English", "Thai", "French", "Spanish",
                     "German", "Japanese", "Chinese", "Korean", "Arabic"]:
            self._translate_to_combo.addItem(lang)
        lang_row.addWidget(self._translate_to_combo)

        lang_row.addStretch()

        translate_btn = QPushButton("Translate")
        translate_btn.setObjectName("btnPrimary")
        translate_btn.setFixedSize(100, 30)
        translate_btn.clicked.connect(self._run_translate)
        lang_row.addWidget(translate_btn)

        lay.addLayout(lang_row)

        # ── Two-panel layout: input | output ──────────────────────────────
        panels = QHBoxLayout()
        panels.setContentsMargins(0, 0, 0, 0)
        panels.setSpacing(14)

        # Input panel
        in_box = QWidget()
        in_box.setObjectName("featureBox")
        in_lay = QVBoxLayout(in_box)
        in_lay.setContentsMargins(0, 0, 0, 0)
        in_lay.setSpacing(0)

        in_header = QHBoxLayout()
        in_header.setContentsMargins(0, 0, 0, 6)
        in_lbl = QLabel("Source text")
        in_lbl.setObjectName("featureLabel")
        in_lbl.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        in_header.addWidget(in_lbl)
        in_header.addStretch()
        clear_tr_btn = QPushButton("Clear")
        clear_tr_btn.setObjectName("btnOutline")
        clear_tr_btn.setFixedSize(80, 28)
        clear_tr_btn.clicked.connect(self._clear_translate)
        in_header.addWidget(clear_tr_btn)
        in_lay.addLayout(in_header)

        self._translate_input = QTextEdit()
        self._translate_input.setObjectName("featureEdit")
        self._translate_input.setPlaceholderText("Paste or type text to translate…")
        in_lay.addWidget(self._translate_input, 1)

        # Character counter
        self._translate_counter = QLabel("0 chars")
        self._translate_counter.setObjectName("settingsLabel")
        self._translate_counter.setStyleSheet("font-size: 11px;")
        self._translate_counter.setAlignment(Qt.AlignmentFlag.AlignRight)
        in_lay.addWidget(self._translate_counter)
        self._translate_input.textChanged.connect(self._on_translate_input_changed)

        panels.addWidget(in_box, 1)

        # Output panel
        out_box = QWidget()
        out_box.setObjectName("featureBox")
        out_lay = QVBoxLayout(out_box)
        out_lay.setContentsMargins(0, 0, 0, 0)
        out_lay.setSpacing(0)

        out_header = QHBoxLayout()
        out_header.setContentsMargins(0, 0, 0, 6)
        out_lbl = QLabel("Translation")
        out_lbl.setObjectName("featureLabel")
        out_lbl.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        out_header.addWidget(out_lbl)
        out_header.addStretch()
        copy_btn = QPushButton("Copy")
        copy_btn.setObjectName("btnOutline")
        copy_btn.setFixedSize(80, 28)
        copy_btn.clicked.connect(self._copy_translation)
        out_header.addWidget(copy_btn)
        out_lay.addLayout(out_header)

        self._translate_output = QTextEdit()
        self._translate_output.setObjectName("featureEditReadOnly")
        self._translate_output.setReadOnly(True)
        self._translate_output.setPlaceholderText("Translation will appear here…")
        out_lay.addWidget(self._translate_output, 1)

        # Placeholder note
        self._translate_note = QLabel("Translation requires an internet connection and API key.")
        self._translate_note.setObjectName("settingsLabel")
        self._translate_note.setStyleSheet("font-size: 11px;")
        self._translate_note.setAlignment(Qt.AlignmentFlag.AlignRight)
        out_lay.addWidget(self._translate_note)

        panels.addWidget(out_box, 1)
        lay.addLayout(panels, 1)
        return frame

    def _on_translate_input_changed(self):
        chars = len(self._translate_input.toPlainText())
        self._translate_counter.setText(f"{chars} char{'s' if chars != 1 else ''}")

    def _clear_translate(self):
        self._translate_input.clear()
        self._translate_output.clear()

    def _copy_translation(self):
        from PyQt6.QtWidgets import QApplication
        text = self._translate_output.toPlainText()
        if text:
            QApplication.clipboard().setText(text)

    def _run_translate(self):
        """Placeholder translation — shows a message until an API is wired up."""
        text = self._translate_input.toPlainText().strip()
        if not text:
            return
        from_lang = self._translate_from_combo.currentText()
        to_lang   = self._translate_to_combo.currentText()
        self._translate_output.setPlainText(
            f"[Translation from {from_lang} → {to_lang}]\n\n"
            "Connect a translation API (e.g. Google Translate, DeepL, or LibreTranslate) "
            "to enable live translation. The input text has been received and is ready to send."
        )


# ══════════════════════════════════════════════════════════════════════════════
# Drag-reorderable tab bar
# ══════════════════════════════════════════════════════════════════════════════

class _DraggableTabBar(QWidget):
    """
    A horizontal tab bar whose buttons can be reordered by dragging.

    • Click  → switch to that tab (calls mixin._switch_tab with canonical idx)
    • Drag   → reorder; a ghost indicator line shows the drop position
    • Order  → persisted via mixin.get_tab_order() / apply_tab_order()
    """

    _DRAG_THRESHOLD = 6   # px before a press becomes a drag

    def __init__(self, mixin, parent=None):
        super().__init__(parent)
        self._mixin   = mixin
        self._order   = list(_DEFAULT_TAB_ORDER)   # canonical indices in display order
        self._active  = 0                          # canonical index of active tab

        # Drag state
        self._drag_btn_idx: int | None = None      # position index being dragged
        self._drag_press_pos: QPoint | None = None
        self._dragging = False
        self._drop_pos: int | None = None          # insertion position indicator

        self.setObjectName("tabBar")
        self.setFixedHeight(36)

        self._layout = QHBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(0)

        self._buttons: list[QPushButton] = []
        self._rebuild_buttons()

    # ── Public API ────────────────────────────────────────────────────────────

    def set_active(self, canonical_idx: int):
        self._active = canonical_idx
        self._refresh_checked()

    def apply_order(self, order: list):
        """Restore a saved order (list of canonical indices)."""
        if (isinstance(order, list)
                and len(order) == len(_DEFAULT_TAB_ORDER)
                and sorted(order) == sorted(_DEFAULT_TAB_ORDER)):
            self._order = list(order)
        self._rebuild_buttons()
        # Show the first tab in the restored order
        if self._order:
            first = self._order[0]
            self._active = first
            self._mixin._tab_stack.setCurrentIndex(first)
            self._refresh_checked()

    def current_order(self) -> list:
        return list(self._order)

    # ── Internal ──────────────────────────────────────────────────────────────

    def _rebuild_buttons(self):
        # Remove ALL items from the layout (buttons + accumulated stretches)
        while self._layout.count():
            item = self._layout.takeAt(0)
            if item.widget():
                item.widget().setParent(None)
        self._buttons.clear()

        for pos, canonical in enumerate(self._order):
            label, _ = _TAB_DEFS[canonical]
            btn = QPushButton(label)
            btn.setObjectName("tabBtn")
            btn.setCheckable(True)
            btn.setFixedHeight(36)
            btn.setCursor(Qt.CursorShape.OpenHandCursor)

            btn.mousePressEvent   = lambda ev, i=pos: self._btn_press(ev, i)
            btn.mouseMoveEvent    = lambda ev, i=pos: self._btn_move(ev, i)
            btn.mouseReleaseEvent = lambda ev, i=pos, c=canonical: self._btn_release(ev, i, c)

            self._layout.addWidget(btn)
            self._buttons.append(btn)

        # Single stretch at the end
        self._layout.addStretch()
        self._refresh_checked()

    def _refresh_checked(self):
        for pos, canonical in enumerate(self._order):
            if pos < len(self._buttons):
                self._buttons[pos].setChecked(canonical == self._active)

    def _btn_press(self, ev, pos: int):
        if ev.button() == Qt.MouseButton.LeftButton:
            self._drag_btn_idx  = pos
            self._drag_press_pos = ev.globalPosition().toPoint()
            self._dragging = False
        ev.accept()

    def _btn_move(self, ev, pos: int):
        if not (ev.buttons() & Qt.MouseButton.LeftButton):
            return
        if self._drag_press_pos is None:
            return

        delta = (ev.globalPosition().toPoint() - self._drag_press_pos).manhattanLength()
        if not self._dragging and delta > self._DRAG_THRESHOLD:
            self._dragging = True
            self._buttons[pos].setCursor(Qt.CursorShape.ClosedHandCursor)

        if self._dragging:
            local_x = self.mapFromGlobal(ev.globalPosition().toPoint()).x()
            self._drop_pos = self._x_to_insert_pos(local_x)
            self.update()
        ev.accept()

    def _btn_release(self, ev, pos: int, canonical: int):
        if ev.button() == Qt.MouseButton.LeftButton:
            was_dragging = self._dragging
            if was_dragging and self._drop_pos is not None:
                self._do_reorder(self._drag_btn_idx, self._drop_pos)
            self._dragging       = False
            self._drop_pos       = None
            self._drag_btn_idx   = None
            self._drag_press_pos = None
            if pos < len(self._buttons):
                self._buttons[pos].setCursor(Qt.CursorShape.OpenHandCursor)
            self.update()
            # Fire the tab switch only on a plain click (no drag occurred)
            if not was_dragging:
                self._mixin._switch_tab(canonical)
        ev.accept()

    def _x_to_insert_pos(self, x: int) -> int:
        """Return the insertion index (0..n) closest to pixel x."""
        n = len(self._buttons)
        for i, btn in enumerate(self._buttons):
            mid = btn.x() + btn.width() // 2
            if x < mid:
                return i
        return n

    def _do_reorder(self, from_pos: int, to_pos: int):
        if from_pos is None:
            return
        # Clamp
        to_pos = max(0, min(to_pos, len(self._order)))
        if from_pos == to_pos or from_pos + 1 == to_pos:
            return
        item = self._order.pop(from_pos)
        # Adjust insertion index after removal
        if to_pos > from_pos:
            to_pos -= 1
        self._order.insert(to_pos, item)
        self._rebuild_buttons()
        # Persist immediately
        self._mixin._on_tab_order_changed()

    # ── Drop indicator painting ────────────────────────────────────────────────

    def paintEvent(self, ev):
        super().paintEvent(ev)
        if not self._dragging or self._drop_pos is None:
            return
        from PyQt6.QtGui import QPainter, QColor, QPen
        painter = QPainter(self)
        pen = QPen(QColor("#ffffff" if self._is_dark() else "#1a1a1a"), 2)
        painter.setPen(pen)
        x = self._insert_x(self._drop_pos)
        painter.drawLine(x, 4, x, self.height() - 4)
        painter.end()

    def _insert_x(self, pos: int) -> int:
        n = len(self._buttons)
        if pos == 0:
            return self._buttons[0].x() if self._buttons else 0
        if pos >= n:
            b = self._buttons[-1]
            return b.x() + b.width()
        return self._buttons[pos].x()

    def _is_dark(self) -> bool:
        return getattr(self._mixin, "_dark", False)
