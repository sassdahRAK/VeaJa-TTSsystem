"""gui/pages/_tab_summary.py — Summary tab for the Dashboard."""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTextEdit, QStackedWidget, QTableWidget, QTableWidgetItem,
    QHeaderView, QAbstractItemView, QScrollArea, QFrame
)
from gui._window_shared import scaled  # noqa: F401
from PyQt6.QtCore import Qt

# ── Profession presets ────────────────────────────────────────────────────────
# (label, icon, prompt_hint, ideal_keys, fallback_keys)
# ideal_keys: field-specific APIs — if missing, show notice
# fallback_keys: general AIs — if missing too, tab is fully locked
_PROFESSIONS = [
    ("General",     "📄",
     "Summarise clearly for a general audience.",
     [], []),
    ("Doctor",      "🩺",
     "Summarise with clinical accuracy. Use medical terminology. Highlight diagnoses, treatments, and key findings.",
     ["api_key_azure_health", "api_key_medpalm", "api_key_nuance_dax", "api_key_aws_healthlake"],
     ["api_key_openai", "api_key_gemini", "api_key_claude"]),
    ("Lawyer",      "⚖️",
     "Summarise with legal precision. Identify key clauses, obligations, risks, and legal implications.",
     ["api_key_harvey", "api_key_casetext", "api_key_lexis"],
     ["api_key_openai", "api_key_gemini", "api_key_claude"]),
    ("IT Engineer", "💻",
     "Summarise with technical depth. Focus on architecture, algorithms, APIs, and implementation details.",
     ["api_key_copilot", "api_key_codewhisperer"],
     ["api_key_openai", "api_key_gemini", "api_key_claude", "api_key_mistral"]),
    ("Educator",    "🎓",
     "Summarise in a clear, structured way suitable for teaching. Break into key concepts and learning points.",
     ["api_key_semantic_scholar", "api_key_wolfram"],
     ["api_key_openai", "api_key_gemini", "api_key_claude"]),
    ("Architect",   "🏛️",
     "Summarise focusing on design principles, structural elements, spatial relationships, and materials.",
     ["api_key_autodesk", "api_key_speckle"],
     ["api_key_openai", "api_key_gemini", "api_key_claude"]),
    ("Scientist",   "🔬",
     "Summarise with scientific rigour. Highlight methodology, findings, data, and conclusions.",
     ["api_key_semantic_scholar", "api_key_elsevier"],
     ["api_key_openai", "api_key_gemini", "api_key_claude"]),
    ("Finance",     "📈",
     "Summarise focusing on financial metrics, risks, returns, and market implications.",
     ["api_key_bloomberg", "api_key_alpaca"],
     ["api_key_openai", "api_key_gemini", "api_key_claude"]),
    ("Marketing",   "📣",
     "Summarise highlighting key messages, target audience, value propositions, and calls to action.",
     ["api_key_jasper", "api_key_copyai"],
     ["api_key_openai", "api_key_gemini", "api_key_claude"]),
    ("Student",     "📚",
     "Summarise in simple, easy-to-understand language. Highlight the most important points for study.",
     ["api_key_semantic_scholar", "api_key_wolfram"],
     ["api_key_openai", "api_key_gemini", "api_key_claude"]),
    ("Artist",      "🎨",
     "Summarise focusing on creative concepts, style, themes, and artistic intent.",
     ["api_key_adobe_firefly", "api_key_midjourney"],
     ["api_key_openai", "api_key_gemini", "api_key_claude"]),
    ("Electronics", "⚡",
     "Summarise focusing on circuit design, components, specifications, and technical parameters.",
     ["api_key_edgeimpulse", "api_key_aws_iot"],
     ["api_key_openai", "api_key_gemini", "api_key_claude"]),
    ("Network",     "🌐",
     "Summarise focusing on network topology, protocols, subnets, security policies, and device configurations.",
     ["api_key_aws_iot"],
     ["api_key_openai", "api_key_gemini", "api_key_claude"]),
    ("OS Engineer", "🖥️",
     "Summarise focusing on kernel internals, system calls, memory management, scheduling, and OS architecture.",
     ["api_key_copilot", "api_key_codewhisperer"],
     ["api_key_openai", "api_key_gemini", "api_key_claude"]),
    ("Cyber",       "🔐",
     "Summarise focusing on vulnerabilities, attack vectors, CVEs, mitigation strategies, and security frameworks (NIST, OWASP).",
     ["api_key_copilot"],
     ["api_key_openai", "api_key_gemini", "api_key_claude"]),
    ("AI Engineer", "🤖",
     "Summarise focusing on model architecture, training methodology, datasets, evaluation metrics, and deployment considerations.",
     ["api_key_openai", "api_key_gemini", "api_key_claude"],
     ["api_key_mistral", "api_key_cohere"]),
    ("Drone",       "🚁",
     "Summarise focusing on flight dynamics, autopilot systems, sensors, regulations, and mission planning.",
     ["api_key_edgeimpulse"],
     ["api_key_openai", "api_key_gemini", "api_key_claude"]),
    ("Robotic",     "🦾",
     "Summarise focusing on kinematics, actuators, sensors, ROS architecture, control loops, and embedded systems.",
     ["api_key_edgeimpulse", "api_key_aws_iot"],
     ["api_key_openai", "api_key_gemini", "api_key_claude"]),
]


class SummaryTabMixin:
    """Summary tab builder and summarise logic."""

    def _build_summary_tab(self) -> QWidget:
        # Outer frame — fills the tab stack slot
        frame = QWidget()
        frame.setObjectName("tabPage")
        outer_lay = QVBoxLayout(frame)
        outer_lay.setContentsMargins(0, 0, 0, 0)
        outer_lay.setSpacing(0)

        # ── Sub-tab bar (Normal / Grid) — sticky, outside scroll ─────────
        sub_bar = QWidget()
        sub_bar.setObjectName("subTabBar")
        # Match the page background so it covers scrolled content cleanly
        sub_bar.setAutoFillBackground(True)
        sb_lay = QHBoxLayout(sub_bar)
        sb_lay.setContentsMargins(0, 8, 0, 0)
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

        # History icon button — right side of the sub-tab bar
        self._sum_history_btn = QPushButton()
        self._sum_history_btn.setObjectName("btnOutline")
        self._sum_history_btn.setFixedSize(32, 30)
        self._sum_history_btn.setToolTip("Summary history")
        self._sum_history_btn.setIcon(self._sum_history_icon())
        from PyQt6.QtCore import QSize
        self._sum_history_btn.setIconSize(QSize(16, 16))
        self._sum_history_btn.clicked.connect(self._show_summary_history)
        sb_lay.addWidget(self._sum_history_btn)

        outer_lay.addWidget(sub_bar)

        # Scroll area wraps ALL content so the page is scrollable
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setObjectName("settingsScroll")
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        inner = QWidget()
        inner.setObjectName("tabPage")
        lay = QVBoxLayout(inner)
        lay.setContentsMargins(0, 10, 0, 18)
        lay.setSpacing(10)

        scroll.setWidget(inner)
        outer_lay.addWidget(scroll, 1)

        # ── Profession selector ───────────────────────────────────────────
        prof_header = QLabel("Add your role or your topic  —  for deeper, field-specific summaries:")
        prof_header.setObjectName("featureLabel")
        prof_header.setStyleSheet("color: #e53935;")
        lay.addWidget(prof_header)

        prof_scroll = QScrollArea()
        prof_scroll.setWidgetResizable(True)
        prof_scroll.setFrameShape(QFrame.Shape.NoFrame)
        prof_scroll.setFixedHeight(52)
        prof_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        prof_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        prof_scroll.setStyleSheet("background: transparent; border: none;")

        prof_inner = QWidget()
        prof_inner.setStyleSheet("background: transparent;")
        prof_row = QHBoxLayout(prof_inner)
        prof_row.setContentsMargins(0, 0, 0, 0)
        prof_row.setSpacing(6)

        self._sum_profession = "General"
        self._sum_prof_btns: list[QPushButton] = []

        for label, icon, _, ideal_keys, fallback_keys in _PROFESSIONS:
            all_keys = ideal_keys + fallback_keys
            locked = bool(all_keys) and not self._prof_has_key(all_keys)
            display = f"{icon}  {label}"
            btn = QPushButton(display)
            btn.setObjectName("profBtn")
            btn.setCheckable(True)
            btn.setChecked(label == "General")
            btn.setFixedHeight(34)
            btn.adjustSize()
            if locked:
                btn.setIcon(self._sum_lock_icon())
                from PyQt6.QtCore import QSize
                btn.setIconSize(QSize(12, 12))
                btn.setToolTip(f"Add a relevant API key to unlock {label} mode")
            btn.clicked.connect(lambda _=False, l=label, ik=ideal_keys, fk=fallback_keys:
                                self._select_profession(l, ik, fk))
            prof_row.addWidget(btn)
            self._sum_prof_btns.append(btn)

        prof_row.addStretch()
        prof_scroll.setWidget(prof_inner)
        lay.addWidget(prof_scroll)

        # ── Field API notice banner ───────────────────────────────────────
        self._sum_notice = QWidget()
        self._sum_notice.setObjectName("sumNoticeBox")
        self._sum_notice.setVisible(False)
        notice_lay = QHBoxLayout(self._sum_notice)
        notice_lay.setContentsMargins(12, 8, 12, 8)
        notice_lay.setSpacing(10)

        self._sum_notice_icon = QLabel("ℹ️")
        self._sum_notice_icon.setStyleSheet("font-size: 16px; background: transparent;")
        notice_lay.addWidget(self._sum_notice_icon, 0, Qt.AlignmentFlag.AlignVCenter)

        notice_text_col = QVBoxLayout()
        notice_text_col.setSpacing(2)
        notice_text_col.setContentsMargins(0, 0, 0, 0)

        self._sum_notice_lbl = QLabel("")
        self._sum_notice_lbl.setObjectName("cardBody")
        self._sum_notice_lbl.setWordWrap(True)
        self._sum_notice_lbl.setStyleSheet("font-size: 12px;")
        notice_text_col.addWidget(self._sum_notice_lbl)

        notice_btn_row = QHBoxLayout()
        notice_btn_row.setSpacing(8)
        notice_btn_row.setContentsMargins(0, 4, 0, 0)

        self._sum_notice_api_btn = QPushButton("Go to My API Key →")
        self._sum_notice_api_btn.setObjectName("btnPrimary")
        self._sum_notice_api_btn.setFixedHeight(28)
        self._sum_notice_api_btn.clicked.connect(lambda: self._navigate(8))
        notice_btn_row.addWidget(self._sum_notice_api_btn)

        self._sum_notice_link_btn = QPushButton("Get recommended API ↗")
        self._sum_notice_link_btn.setObjectName("btnOutline")
        self._sum_notice_link_btn.setFixedHeight(28)
        self._sum_notice_link_btn.clicked.connect(self._sum_open_recommended_link)
        notice_btn_row.addWidget(self._sum_notice_link_btn)

        notice_btn_row.addStretch()
        notice_text_col.addLayout(notice_btn_row)
        notice_lay.addLayout(notice_text_col, 1)

        lay.addWidget(self._sum_notice)

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
        self._summary_input.setFixedHeight(120)
        ib_lay.addWidget(self._summary_input)

        # Attachment toolbar
        attach_row = QHBoxLayout()
        attach_row.setContentsMargins(0, 6, 0, 0)
        attach_row.setSpacing(8)

        attach_lbl = QLabel("Attach:")
        attach_lbl.setObjectName("featureLabel")
        attach_lbl.setStyleSheet("font-size: 11px;")
        attach_row.addWidget(attach_lbl)

        for svg_body, tip, slot in [
            # File — document icon
            ('<path d="M4 2h8l4 4v14H4V2z" stroke="{c}" stroke-width="1.4" fill="none" stroke-linejoin="round"/>'
             '<path d="M12 2v4h4" stroke="{c}" stroke-width="1.4" fill="none"/>',
             "File (txt/pdf/docx)", self._sum_attach_file),
            # Folder
            ('<path d="M2 6h7l2-2h9v14H2V6z" stroke="{c}" stroke-width="1.4" fill="none" stroke-linejoin="round"/>',
             "Folder", self._sum_attach_folder),
            # Link / chain
            ('<path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71" '
             'stroke="{c}" stroke-width="1.5" fill="none" stroke-linecap="round"/>'
             '<path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71" '
             'stroke="{c}" stroke-width="1.5" fill="none" stroke-linecap="round"/>',
             "Git repo URL", self._sum_attach_git),
            # Globe / web
            ('<circle cx="12" cy="12" r="9" stroke="{c}" stroke-width="1.4" fill="none"/>'
             '<path d="M12 3 C9 7 9 17 12 21 M12 3 C15 7 15 17 12 21" stroke="{c}" stroke-width="1.2" fill="none"/>'
             '<path d="M3 12 H21" stroke="{c}" stroke-width="1.2"/>',
             "Web link", self._sum_attach_link),
            # Image / picture
            ('<rect x="3" y="3" width="18" height="18" rx="2" stroke="{c}" stroke-width="1.4" fill="none"/>'
             '<circle cx="8.5" cy="8.5" r="1.5" fill="{c}"/>'
             '<path d="M21 15 l-5-5-4 4-2-2-7 7" stroke="{c}" stroke-width="1.3" fill="none" stroke-linejoin="round"/>',
             "Image", self._sum_attach_image),
        ]:
            btn = QPushButton()
            btn.setObjectName("btnOutline")
            btn.setFixedSize(32, 28)
            btn.setToolTip(tip)
            btn.setIcon(self._sum_svg_icon(svg_body, 16))
            from PyQt6.QtCore import QSize
            btn.setIconSize(QSize(16, 16))
            btn.clicked.connect(slot)
            attach_row.addWidget(btn)

        # Clear + Summarise on the same row as Attach, pushed right
        attach_row.addStretch()
        clear_btn = QPushButton("Clear")
        clear_btn.setObjectName("btnOutline")
        clear_btn.setFixedSize(80, 28)
        clear_btn.clicked.connect(self._clear_summary)
        attach_row.addWidget(clear_btn)

        summarise_btn = QPushButton("Summarise")
        summarise_btn.setObjectName("btnPrimary")
        summarise_btn.setFixedSize(100, 28)
        summarise_btn.clicked.connect(self._run_summary)
        attach_row.addWidget(summarise_btn)

        ib_lay.addLayout(attach_row)

        # Attached items list
        self._sum_attachments: list[str] = []
        self._sum_attach_lbl = QLabel("")
        self._sum_attach_lbl.setObjectName("settingsLabel")
        self._sum_attach_lbl.setWordWrap(True)
        self._sum_attach_lbl.setStyleSheet("font-size: 10px; padding-top: 4px;")
        self._sum_attach_lbl.setVisible(False)
        ib_lay.addWidget(self._sum_attach_lbl)

        lay.addWidget(input_box)

        # ── Output stack ──────────────────────────────────────────────────
        self._summary_output_stack = QStackedWidget()
        self._summary_output_stack.setMinimumHeight(150)

        # Normal output
        normal_out_box = QWidget()
        normal_out_box.setObjectName("featureBox")
        no_lay = QVBoxLayout(normal_out_box)
        no_lay.setContentsMargins(0, 0, 0, 0)
        no_lay.setSpacing(6)

        sum_hdr = QHBoxLayout()
        sum_hdr.setContentsMargins(0, 0, 0, 0)
        sum_lbl = QLabel("Summary")
        sum_lbl.setObjectName("featureLabel")
        sum_hdr.addWidget(sum_lbl)
        no_lay.addLayout(sum_hdr)

        self._summary_normal_out = QTextEdit()
        self._summary_normal_out.setObjectName("featureEditReadOnly")
        self._summary_normal_out.setReadOnly(True)
        self._summary_normal_out.setPlaceholderText("Summary will appear here…")
        self._summary_normal_out.setMinimumHeight(160)
        no_lay.addWidget(self._summary_normal_out)

        # Read button — below the output box
        read_row = QHBoxLayout()
        read_row.setContentsMargins(0, 4, 0, 0)
        read_row.addStretch()
        self._sum_read_btn = QPushButton("▶  Read")
        self._sum_read_btn.setObjectName("btnOutline")
        self._sum_read_btn.setFixedSize(90, 30)
        self._sum_read_btn.clicked.connect(self._read_summary)
        read_row.addWidget(self._sum_read_btn)
        no_lay.addLayout(read_row)
        self._summary_output_stack.addWidget(normal_out_box)

        # Grid output — nested expandable rows with follow-up Q&A
        grid_out_box = QWidget()
        grid_out_box.setObjectName("featureBox")
        go_lay = QVBoxLayout(grid_out_box)
        go_lay.setContentsMargins(0, 0, 0, 0)
        go_lay.setSpacing(6)

        grid_hdr = QHBoxLayout()
        grid_hdr.setContentsMargins(0, 0, 0, 0)
        grid_hdr.addWidget(QLabel("Key points  —  click a row to expand / ask follow-up",
                                  objectName="featureLabel"))
        go_lay.addLayout(grid_hdr)

        # Scrollable container for nested grid rows
        self._grid_rows_widget = QWidget()
        self._grid_rows_widget.setObjectName("tabPage")
        self._grid_rows_lay = QVBoxLayout(self._grid_rows_widget)
        self._grid_rows_lay.setContentsMargins(0, 0, 0, 0)
        self._grid_rows_lay.setSpacing(4)
        self._grid_rows_lay.addStretch()

        go_lay.addWidget(self._grid_rows_widget, 1)
        self._summary_output_stack.addWidget(grid_out_box)

        # ── Follow-up question bar (shown below both outputs) ─────────────
        self._sum_followup_box = QWidget()
        self._sum_followup_box.setObjectName("featureBox")
        self._sum_followup_box.setVisible(False)
        fq_lay = QVBoxLayout(self._sum_followup_box)
        fq_lay.setContentsMargins(0, 8, 0, 0)
        fq_lay.setSpacing(6)

        fq_lbl = QLabel("Ask a follow-up question about the summary:")
        fq_lbl.setObjectName("featureLabel")
        fq_lay.addWidget(fq_lbl)

        fq_input_row = QHBoxLayout()
        fq_input_row.setSpacing(8)
        self._sum_followup_input = QTextEdit()
        self._sum_followup_input.setObjectName("featureEdit")
        self._sum_followup_input.setPlaceholderText("e.g. What are the risks? Can you explain point 2 in more detail?")
        self._sum_followup_input.setFixedHeight(60)
        fq_input_row.addWidget(self._sum_followup_input, 1)

        ask_btn = QPushButton("Ask")
        ask_btn.setObjectName("btnPrimary")
        ask_btn.setFixedSize(70, 60)
        ask_btn.clicked.connect(self._run_followup_question)
        fq_input_row.addWidget(ask_btn)
        fq_lay.addLayout(fq_input_row)

        self._sum_followup_answer = QTextEdit()
        self._sum_followup_answer.setObjectName("featureEditReadOnly")
        self._sum_followup_answer.setReadOnly(True)
        self._sum_followup_answer.setPlaceholderText("Answer will appear here…")
        self._sum_followup_answer.setMinimumHeight(80)
        self._sum_followup_answer.setVisible(False)
        fq_lay.addWidget(self._sum_followup_answer)

        lay.addWidget(self._summary_output_stack)
        lay.addWidget(self._sum_followup_box)
        lay.addStretch()
        return frame

    # ── Profession selection ──────────────────────────────────────────────────

    def _prof_has_key(self, req_keys: list) -> bool:
        """Return True if any of the required API keys is set."""
        if not req_keys:
            return True
        cached = getattr(self, "_last_profile_cache", {})
        if cached:
            return any(cached.get(k, "").strip() for k in req_keys)
        if hasattr(self, "_api_key_inputs"):
            return any(
                self._api_key_inputs[k].text().strip()
                for k in req_keys if k in self._api_key_inputs
            )
        return False

    def _sum_svg_icon(self, svg_body: str, size: int):
        """Render an inline SVG body as a QIcon, theme-aware."""
        from PyQt6.QtSvg import QSvgRenderer
        from PyQt6.QtGui import QPixmap, QPainter, QIcon, QColor
        from PyQt6.QtWidgets import QApplication
        is_dark = getattr(self, "_dark", False)
        color = "#aaaaaa" if is_dark else "#666666"
        svg = (
            f'<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">'
            f'{svg_body.replace("{c}", color)}'
            f'</svg>'
        ).encode()
        app = QApplication.instance()
        dpr = app.primaryScreen().devicePixelRatio() if app and app.primaryScreen() else 1.0
        phys = int(size * dpr)
        px = QPixmap(phys, phys)
        px.fill(QColor(0, 0, 0, 0))
        renderer = QSvgRenderer(svg)
        p = QPainter(px)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        renderer.render(p)
        p.end()
        px.setDevicePixelRatio(dpr)
        return QIcon(px)

    def _sum_lock_icon(self):
        from PyQt6.QtSvg import QSvgRenderer
        from PyQt6.QtGui import QPixmap, QPainter, QIcon, QColor
        from PyQt6.QtWidgets import QApplication
        is_dark = getattr(self, "_dark", False)
        color = "#aaaaaa" if is_dark else "#888888"
        svg = (
            f'<svg viewBox="0 0 16 16" xmlns="http://www.w3.org/2000/svg" fill="none">'
            f'<rect x="2" y="7.5" width="12" height="7.5" rx="1.8" '
            f'stroke="{color}" stroke-width="1.3"/>'
            f'<path d="M4.5 7.5V5a3.5 3.5 0 0 1 7 0v2.5" '
            f'stroke="{color}" stroke-width="1.3" stroke-linecap="round"/>'
            f'<circle cx="8" cy="11" r="1" fill="{color}"/>'
            f'</svg>'
        ).encode()
        app = QApplication.instance()
        dpr = app.primaryScreen().devicePixelRatio() if app and app.primaryScreen() else 1.0
        phys = int(12 * dpr)
        px = QPixmap(phys, phys)
        px.fill(QColor(0, 0, 0, 0))
        renderer = QSvgRenderer(svg)
        p = QPainter(px)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        renderer.render(p)
        p.end()
        px.setDevicePixelRatio(dpr)
        return QIcon(px)

    def _select_profession(self, label: str, ideal_keys: list = None, fallback_keys: list = None):
        ideal_keys   = ideal_keys   or []
        fallback_keys = fallback_keys or []
        all_keys = ideal_keys + fallback_keys
        # Fully locked — no API key at all
        if all_keys and not self._prof_has_key(all_keys):
            self._navigate(8)
            return
        self._sum_profession = label
        for btn in self._sum_prof_btns:
            parts = btn.text().split("  ", 1)
            btn_label = parts[-1] if len(parts) > 1 else btn.text()
            btn.setChecked(btn_label == label)
        # Show notice if ideal (field-specific) key is missing but fallback exists
        missing_ideal = bool(ideal_keys) and not self._prof_has_key(ideal_keys)
        self._update_sum_notice(label, ideal_keys, missing_ideal)

    # ── Notice banner ─────────────────────────────────────────────────────────

    # Recommended API docs URL per profession
    _PROF_RECOMMENDED_URL = {
        "Doctor":      "https://azure.microsoft.com/en-us/products/bot-services/health-bot",
        "Lawyer":      "https://www.harvey.ai",
        "IT Engineer": "https://platform.openai.com/api-keys",
        "Educator":    "https://api.semanticscholar.org/",
        "Architect":   "https://aps.autodesk.com/",
        "Scientist":   "https://api.semanticscholar.org/",
        "Finance":     "https://www.bloomberg.com/company/press/bloomberggpt-50-billion-parameter-llm-bloomberg/",
        "Marketing":   "https://developers.jasper.ai/",
        "Student":     "https://platform.openai.com/api-keys",
        "Artist":      "https://developer.adobe.com/firefly-api/",
        "Electronics": "https://studio.edgeimpulse.com/",
        "Network":     "https://platform.openai.com/api-keys",
        "OS Engineer": "https://github.com/settings/tokens",
        "Cyber":       "https://github.com/settings/tokens",
        "AI Engineer": "https://platform.openai.com/api-keys",
        "Drone":       "https://studio.edgeimpulse.com/",
        "Robotic":     "https://studio.edgeimpulse.com/",
    }

    _PROF_IDEAL_AI = {
        "Doctor":      "Azure Health Bot or Google MedPaLM 2",
        "Lawyer":      "Harvey AI or Casetext CoCounsel",
        "IT Engineer": "OpenAI GPT-4o or GitHub Copilot",
        "Educator":    "Semantic Scholar API or OpenAI",
        "Architect":   "Autodesk AI (Forma) or OpenAI",
        "Scientist":   "Semantic Scholar or Elsevier TDM",
        "Finance":     "Bloomberg GPT or OpenAI",
        "Marketing":   "Jasper AI or OpenAI",
        "Student":     "OpenAI GPT-4o or Google Gemini",
        "Artist":      "Adobe Firefly or Midjourney",
        "Electronics": "Edge Impulse or OpenAI",
        "Network":     "OpenAI GPT-4o or Gemini",
        "OS Engineer": "GitHub Copilot or OpenAI",
        "Cyber":       "GitHub Copilot or OpenAI",
        "AI Engineer": "OpenAI GPT-4o or Google Gemini",
        "Drone":       "Edge Impulse or OpenAI",
        "Robotic":     "Edge Impulse or OpenAI",
    }

    def _update_sum_notice(self, label: str, ideal_keys: list, show: bool):
        if not hasattr(self, "_sum_notice"):
            return
        if not show or label == "General":
            self._sum_notice.setVisible(False)
            return
        ideal = self._PROF_IDEAL_AI.get(label, "a relevant AI API")
        self._sum_notice_lbl.setText(
            f"For deep {label} summaries, connect {ideal}. "
            f"Without it, Veaja uses basic extraction — results will be less accurate and less detailed."
        )
        self._sum_notice_recommended_url = self._PROF_RECOMMENDED_URL.get(
            label, "https://platform.openai.com/api-keys"
        )
        self._sum_notice.setVisible(True)

    def _sum_open_recommended_link(self):
        from PyQt6.QtGui import QDesktopServices
        from PyQt6.QtCore import QUrl
        url = getattr(self, "_sum_notice_recommended_url", "https://platform.openai.com/api-keys")
        QDesktopServices.openUrl(QUrl(url))

    def refresh_profession_locks(self):
        """Rebuild profession buttons to reflect current API key state."""
        for btn, (label, icon, _, ideal_keys, fallback_keys) in zip(self._sum_prof_btns, _PROFESSIONS):
            all_keys = ideal_keys + fallback_keys
            locked = bool(all_keys) and not self._prof_has_key(all_keys)
            if locked:
                btn.setIcon(self._sum_lock_icon())
                from PyQt6.QtCore import QSize
                btn.setIconSize(QSize(12, 12))
                btn.setToolTip(f"Add a relevant API key to unlock {label} mode")
            else:
                from PyQt6.QtGui import QIcon
                btn.setIcon(QIcon())
                btn.setToolTip("")
            btn.setObjectName("profBtn")
            btn.style().unpolish(btn)
            btn.style().polish(btn)

        # Re-evaluate notice for the currently selected profession
        current = getattr(self, "_sum_profession", "General")
        for label, _, _, ideal_keys, fallback_keys in _PROFESSIONS:
            if label == current:
                missing_ideal = bool(ideal_keys) and not self._prof_has_key(ideal_keys)
                self._update_sum_notice(label, ideal_keys, missing_ideal)
                break

    def _get_profession_hint(self) -> str:
        for label, _, hint, _, _ in _PROFESSIONS:
            if label == getattr(self, "_sum_profession", "General"):
                return hint
        return ""

    # ── Summary logic ─────────────────────────────────────────────────────────

    def _switch_summary_mode(self, idx: int):
        self._sum_normal_btn.setChecked(idx == 0)
        self._sum_grid_btn.setChecked(idx == 1)
        self._summary_output_stack.setCurrentIndex(idx)

    def _clear_summary(self):
        self._summary_input.clear()
        self._summary_normal_out.clear()
        # Clear nested grid rows
        if hasattr(self, "_grid_rows_lay"):
            while self._grid_rows_lay.count() > 1:  # keep the stretch
                item = self._grid_rows_lay.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()
        if hasattr(self, "_sum_followup_box"):
            self._sum_followup_box.setVisible(False)
            self._sum_followup_input.clear()
            self._sum_followup_answer.clear()
            self._sum_followup_answer.setVisible(False)
        self._sum_attachments.clear()
        if hasattr(self, "_sum_attach_lbl"):
            self._sum_attach_lbl.setVisible(False)

    # ── Attachment handlers ───────────────────────────────────────────────────

    def _sum_update_attach_label(self):
        if self._sum_attachments:
            items = "  ·  ".join(
                a if len(a) <= 50 else "…" + a[-47:]
                for a in self._sum_attachments
            )
            self._sum_attach_lbl.setText(f"📎 {items}")
            self._sum_attach_lbl.setVisible(True)
        else:
            self._sum_attach_lbl.setVisible(False)

    def _sum_attach_file(self):
        from PyQt6.QtWidgets import QFileDialog
        paths, _ = QFileDialog.getOpenFileNames(
            None, "Attach file(s)", "",
            "Documents (*.txt *.pdf *.docx *.md *.csv *.json *.xml *.html *.py *.js *.ts)"
        )
        for p in paths:
            if p not in self._sum_attachments:
                self._sum_attachments.append(p)
                # Auto-load text files into the input box
                try:
                    with open(p, encoding="utf-8", errors="ignore") as f:
                        content = f.read(8000)
                    existing = self._summary_input.toPlainText()
                    sep = "\n\n---\n" if existing.strip() else ""
                    self._summary_input.setPlainText(existing + sep + content)
                except Exception:
                    pass
        self._sum_update_attach_label()

    def _sum_attach_folder(self):
        from PyQt6.QtWidgets import QFileDialog
        path = QFileDialog.getExistingDirectory(None, "Attach folder")
        if path and path not in self._sum_attachments:
            self._sum_attachments.append(path + "/")
            self._sum_update_attach_label()

    def _sum_attach_git(self):
        from PyQt6.QtWidgets import QInputDialog
        url, ok = QInputDialog.getText(None, "Git Repository URL",
                                       "Enter GitHub / GitLab repo URL:")
        if ok and url.strip():
            url = url.strip()
            if url not in self._sum_attachments:
                self._sum_attachments.append(url)
            # Append URL as context to the input
            existing = self._summary_input.toPlainText()
            sep = "\n\n---\n" if existing.strip() else ""
            self._summary_input.setPlainText(
                existing + sep + f"[Git repo: {url}]"
            )
            self._sum_update_attach_label()

    def _sum_attach_link(self):
        from PyQt6.QtWidgets import QInputDialog
        url, ok = QInputDialog.getText(None, "Web Link", "Enter URL:")
        if ok and url.strip():
            url = url.strip()
            if url not in self._sum_attachments:
                self._sum_attachments.append(url)
            existing = self._summary_input.toPlainText()
            sep = "\n\n---\n" if existing.strip() else ""
            self._summary_input.setPlainText(
                existing + sep + f"[Link: {url}]"
            )
            self._sum_update_attach_label()

    def _sum_attach_image(self):
        from PyQt6.QtWidgets import QFileDialog
        path, _ = QFileDialog.getOpenFileName(
            None, "Attach image", "",
            "Images (*.jpg *.jpeg *.png *.webp *.bmp *.gif *.tiff)"
        )
        if path and path not in self._sum_attachments:
            self._sum_attachments.append(path)
            existing = self._summary_input.toPlainText()
            sep = "\n\n---\n" if existing.strip() else ""
            self._summary_input.setPlainText(
                existing + sep + f"[Image: {path}]"
            )
            self._sum_update_attach_label()

    def _run_summary(self):
        text = self._summary_input.toPlainText().strip()
        if not text:
            return

        profession = getattr(self, "_sum_profession", "General")
        sentences = [s.strip() for s in text.replace("\n", " ").split(".") if s.strip()]

        # Normal text
        normal_result = ". ".join(sentences[:3])
        if normal_result and not normal_result.endswith("."):
            normal_result += "."
        if profession != "General":
            normal_result = f"[{profession} perspective]\n\n{normal_result}"
        self._summary_normal_out.setPlainText(normal_result)
        # Save to history
        if not hasattr(self, "_sum_history"):
            self._sum_history: list[str] = []
        self._sum_history.insert(0, normal_result)
        self._sum_history = self._sum_history[:20]

        # Nested grid rows
        while self._grid_rows_lay.count() > 1:
            item = self._grid_rows_lay.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        for i, sentence in enumerate(sentences, start=1):
            point = f"{profession} · {i}" if profession != "General" else f"Point {i}"
            row_widget = _ExpandableRow(point, sentence + ".", i, self)
            self._grid_rows_lay.insertWidget(self._grid_rows_lay.count() - 1, row_widget)

        # Show follow-up bar
        self._sum_followup_box.setVisible(True)
        self._sum_followup_answer.setVisible(False)

    def _read_summary(self):
        text = self._summary_normal_out.toPlainText().strip()
        if text:
            self.read_requested.emit(text)
        # Save to history
        if text:
            if not hasattr(self, "_sum_history"):
                self._sum_history: list[str] = []
            self._sum_history.insert(0, text)
            self._sum_history = self._sum_history[:20]  # keep last 20

    # ── History icon + panel ──────────────────────────────────────────────────

    def _sum_history_icon(self):
        from PyQt6.QtSvg import QSvgRenderer
        from PyQt6.QtGui import QPixmap, QPainter, QIcon, QColor
        from PyQt6.QtWidgets import QApplication
        is_dark = getattr(self, "_dark", False)
        color = "#aaaaaa" if is_dark else "#666666"
        svg = (
            f'<svg viewBox="0 0 16 16" xmlns="http://www.w3.org/2000/svg" fill="none">'
            f'<circle cx="8" cy="8" r="6" stroke="{color}" stroke-width="1.3"/>'
            f'<path d="M8 5v3.5l2 1.5" stroke="{color}" stroke-width="1.3" '
            f'stroke-linecap="round" stroke-linejoin="round"/>'
            f'<path d="M3 3 Q2 5 3.5 6.5" stroke="{color}" stroke-width="1.2" '
            f'stroke-linecap="round" fill="none"/>'
            f'<polyline points="2,4 3.5,6.5 5,5" stroke="{color}" stroke-width="1.2" '
            f'stroke-linecap="round" stroke-linejoin="round" fill="none"/>'
            f'</svg>'
        ).encode()
        app = QApplication.instance()
        dpr = app.primaryScreen().devicePixelRatio() if app and app.primaryScreen() else 1.0
        phys = int(16 * dpr)
        px = QPixmap(phys, phys)
        px.fill(QColor(0, 0, 0, 0))
        renderer = QSvgRenderer(svg)
        p = QPainter(px)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        renderer.render(p)
        p.end()
        px.setDevicePixelRatio(dpr)
        return QIcon(px)

    def _show_summary_history(self):
        from PyQt6.QtWidgets import QDialog, QVBoxLayout, QListWidget, QListWidgetItem, QPushButton, QLabel
        history = getattr(self, "_sum_history", [])
        dlg = QDialog()
        dlg.setWindowTitle("Summary History")
        dlg.setMinimumSize(480, 360)
        dlg.setModal(True)
        lay = QVBoxLayout(dlg)
        lay.setContentsMargins(16, 16, 16, 16)
        lay.setSpacing(10)

        lbl = QLabel("Recent summaries — click to restore:")
        lbl.setObjectName("settingsLabel")
        lay.addWidget(lbl)

        lst = QListWidget()
        lst.setObjectName("settingsScroll")
        if not history:
            lst.addItem(QListWidgetItem("No history yet — run a summary first."))
        else:
            for i, text in enumerate(history, 1):
                preview = text[:120].replace("\n", " ") + ("…" if len(text) > 120 else "")
                lst.addItem(QListWidgetItem(f"{i}.  {preview}"))
        lay.addWidget(lst, 1)

        btn_row = QHBoxLayout()
        restore_btn = QPushButton("Restore selected")
        restore_btn.setObjectName("btnPrimary")
        restore_btn.setFixedHeight(32)
        close_btn = QPushButton("Close")
        close_btn.setObjectName("btnOutline")
        close_btn.setFixedHeight(32)
        btn_row.addWidget(restore_btn)
        btn_row.addWidget(close_btn)
        lay.addLayout(btn_row)

        def _restore():
            row = lst.currentRow()
            if history and 0 <= row < len(history):
                self._summary_normal_out.setPlainText(history[row])
                dlg.accept()

        restore_btn.clicked.connect(_restore)
        close_btn.clicked.connect(dlg.reject)
        lst.itemDoubleClicked.connect(lambda _: _restore())
        dlg.exec()

    def _run_followup_question(self):
        """Answer a follow-up question about the summary (placeholder until API connected)."""
        question = self._sum_followup_input.toPlainText().strip()
        summary  = self._summary_normal_out.toPlainText().strip()
        if not question:
            return
        answer = (
            f"[Follow-up: {question}]\n\n"
            f"Based on the summary:\n{summary[:200]}{'…' if len(summary) > 200 else ''}\n\n"
            "Connect an AI API key (OpenAI, Gemini, or Claude) in My API Key "
            "to get a real answer to this question."
        )
        self._sum_followup_answer.setPlainText(answer)
        self._sum_followup_answer.setVisible(True)


# ══════════════════════════════════════════════════════════════════════════════
# Expandable grid row with nested follow-up Q&A
# ══════════════════════════════════════════════════════════════════════════════

class _ExpandableRow(QWidget):
    """
    A single key-point row that can be:
      • Collapsed  — shows point label + detail preview
      • Expanded   — shows full detail + nested follow-up Q&A input
    Click the row header to toggle.
    """

    def __init__(self, point: str, detail: str, index: int, mixin, parent=None):
        super().__init__(parent)
        self._expanded = False
        self._mixin    = mixin
        self._detail   = detail
        self._point    = point

        self.setObjectName("expandableRow")
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Header row (always visible, clickable) ────────────────────────
        header = QWidget()
        header.setObjectName("expandableRowHeader")
        header.setCursor(Qt.CursorShape.PointingHandCursor)
        h_lay = QHBoxLayout(header)
        h_lay.setContentsMargins(10, 8, 10, 8)
        h_lay.setSpacing(10)

        self._toggle_lbl = QLabel("▶")
        self._toggle_lbl.setFixedWidth(14)
        self._toggle_lbl.setStyleSheet("color: #888888; font-size: 10px; background: transparent;")
        h_lay.addWidget(self._toggle_lbl)

        point_lbl = QLabel(point)
        point_lbl.setObjectName("cardTitle")
        point_lbl.setFixedWidth(90)
        h_lay.addWidget(point_lbl)

        preview = detail
        self._preview_lbl = QLabel(preview)
        self._preview_lbl.setObjectName("cardBody")
        self._preview_lbl.setStyleSheet("font-size: 12px;")
        self._preview_lbl.setWordWrap(True)
        h_lay.addWidget(self._preview_lbl, 1)

        root.addWidget(header)

        # ── Expanded content (hidden by default) ──────────────────────────
        self._body = QWidget()
        self._body.setObjectName("expandableRowBody")
        self._body.setVisible(False)
        b_lay = QVBoxLayout(self._body)
        b_lay.setContentsMargins(34, 4, 10, 10)
        b_lay.setSpacing(8)

        # Full detail text
        detail_lbl = QLabel(detail)
        detail_lbl.setObjectName("cardBody")
        detail_lbl.setWordWrap(True)
        detail_lbl.setStyleSheet("font-size: 13px;")
        b_lay.addWidget(detail_lbl)

        # Nested follow-up Q&A
        ask_lbl = QLabel("Ask about this point:")
        ask_lbl.setObjectName("featureLabel")
        ask_lbl.setStyleSheet("font-size: 11px;")
        b_lay.addWidget(ask_lbl)

        ask_row = QHBoxLayout()
        ask_row.setSpacing(6)
        self._ask_input = QTextEdit()
        self._ask_input.setObjectName("featureEdit")
        self._ask_input.setPlaceholderText("e.g. Can you explain this further?")
        self._ask_input.setFixedHeight(52)
        ask_row.addWidget(self._ask_input, 1)

        ask_btn = QPushButton("Ask")
        ask_btn.setObjectName("btnPrimary")
        ask_btn.setFixedSize(56, 52)
        ask_btn.clicked.connect(self._ask_nested)
        ask_row.addWidget(ask_btn)
        b_lay.addLayout(ask_row)

        self._answer_lbl = QLabel("")
        self._answer_lbl.setObjectName("cardBody")
        self._answer_lbl.setWordWrap(True)
        self._answer_lbl.setStyleSheet(
            "font-size: 12px; padding: 8px; border-radius: 6px;"
        )
        self._answer_lbl.setVisible(False)
        b_lay.addWidget(self._answer_lbl)

        root.addWidget(self._body)

        # Click anywhere on header to toggle
        header.mousePressEvent = lambda _: self._toggle()

    def _toggle(self):
        self._expanded = not self._expanded
        self._body.setVisible(self._expanded)
        self._toggle_lbl.setText("▼" if self._expanded else "▶")

    def _ask_nested(self):
        question = self._ask_input.toPlainText().strip()
        if not question:
            return
        answer = (
            f"[Q: {question}]\n\n"
            f"Regarding: \"{self._detail[:100]}{'…' if len(self._detail) > 100 else ''}\"\n\n"
            "Connect an AI API key in My API Key to get a real answer."
        )
        self._answer_lbl.setText(answer)
        self._answer_lbl.setVisible(True)
