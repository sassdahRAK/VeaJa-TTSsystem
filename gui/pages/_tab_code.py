"""gui/pages/_tab_code.py — Code analysis tab for the Dashboard."""

import re
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTextEdit, QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont


class CodeTabMixin:
    """Code tab builder and analysis logic."""

    def _build_code_tab(self) -> QWidget:
        frame = QWidget()
        frame.setObjectName("tabPage")
        lay = QVBoxLayout(frame)
        lay.setContentsMargins(0, 18, 0, 0)
        lay.setSpacing(10)

        # Input
        input_box = QWidget()
        input_box.setObjectName("featureBox")
        ib_lay = QVBoxLayout(input_box)
        ib_lay.setContentsMargins(0, 0, 0, 0)
        ib_lay.setSpacing(0)

        in_hdr = QHBoxLayout()
        in_hdr.setContentsMargins(0, 0, 0, 6)
        in_lbl = QLabel("Paste code")
        in_lbl.setObjectName("featureLabel")
        in_lbl.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        in_hdr.addWidget(in_lbl)
        in_hdr.addStretch()
        clear_btn = QPushButton("Clear")
        clear_btn.setObjectName("btnOutline")
        clear_btn.setFixedSize(80, 28)
        clear_btn.clicked.connect(self._clear_code)
        in_hdr.addWidget(clear_btn)
        ib_lay.addLayout(in_hdr)

        self._code_input = QTextEdit()
        self._code_input.setObjectName("codeEdit")
        self._code_input.setPlaceholderText("Paste your code here…")
        self._code_input.setFixedHeight(150)
        mono = QFont("Consolas", 10)
        mono.setStyleHint(QFont.StyleHint.Monospace)
        self._code_input.setFont(mono)
        ib_lay.addWidget(self._code_input)
        lay.addWidget(input_box)

        # Action row
        action_row = QHBoxLayout()
        action_row.setContentsMargins(0, 0, 0, 0)
        action_row.setSpacing(10)
        action_row.addStretch()
        analyse_btn = QPushButton("Analyse")
        analyse_btn.setObjectName("btnPrimary")
        analyse_btn.setFixedSize(100, 30)
        analyse_btn.clicked.connect(self._run_code_analyse)
        action_row.addWidget(analyse_btn)
        lay.addLayout(action_row)

        # Overview bar
        self._code_summary_lbl = QLabel("")
        self._code_summary_lbl.setObjectName("codeSummaryLbl")
        self._code_summary_lbl.setWordWrap(True)
        self._code_summary_lbl.setVisible(False)
        lay.addWidget(self._code_summary_lbl)

        # Grid
        self._code_grid_lbl = QLabel("Key points  —  click a row to inspect")
        self._code_grid_lbl.setObjectName("featureLabel")
        self._code_grid_lbl.setVisible(False)
        lay.addWidget(self._code_grid_lbl)

        self._code_table = QTableWidget(0, 3)
        self._code_table.setObjectName("summaryGrid")
        self._code_table.setHorizontalHeaderLabels(["#", "Name / Syntax", "Role"])
        self._code_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self._code_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self._code_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self._code_table.verticalHeader().setVisible(False)
        self._code_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._code_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._code_table.setAlternatingRowColors(True)
        self._code_table.setVisible(False)
        self._code_table.cellClicked.connect(self._on_code_row_clicked)
        lay.addWidget(self._code_table, 1)

        # Detail panel
        self._code_detail_panel = QWidget()
        self._code_detail_panel.setObjectName("codeDetailPanel")
        self._code_detail_panel.setVisible(False)
        dp_lay = QVBoxLayout(self._code_detail_panel)
        dp_lay.setContentsMargins(14, 10, 14, 10)
        dp_lay.setSpacing(6)

        dp_hdr = QHBoxLayout()
        self._code_detail_title = QLabel("")
        self._code_detail_title.setObjectName("cardTitle")
        dp_hdr.addWidget(self._code_detail_title)
        dp_hdr.addStretch()
        close_btn = QPushButton("✕")
        close_btn.setObjectName("btnOutline")
        close_btn.setFixedSize(28, 28)
        close_btn.clicked.connect(lambda: self._code_detail_panel.setVisible(False))
        dp_hdr.addWidget(close_btn)
        dp_lay.addLayout(dp_hdr)

        self._code_detail_body = QLabel("")
        self._code_detail_body.setObjectName("cardBody")
        self._code_detail_body.setWordWrap(True)
        self._code_detail_body.setTextFormat(Qt.TextFormat.RichText)
        dp_lay.addWidget(self._code_detail_body)
        lay.addWidget(self._code_detail_panel)
        return frame

    def _clear_code(self):
        self._code_input.clear()
        self._code_table.setRowCount(0)
        self._code_table.setVisible(False)
        self._code_grid_lbl.setVisible(False)
        self._code_summary_lbl.setVisible(False)
        self._code_detail_panel.setVisible(False)

    def _run_code_analyse(self):
        code = self._code_input.toPlainText().strip()
        if not code:
            return
        items   = self._extract_code_items(code)
        overall = self._overall_code_summary(code, items)
        self._code_summary_lbl.setText(f"<b>Overview:</b> {overall}")
        self._code_summary_lbl.setVisible(True)
        self._code_table.setRowCount(0)
        for i, item in enumerate(items, start=1):
            row = self._code_table.rowCount()
            self._code_table.insertRow(row)
            self._code_table.setItem(row, 0, QTableWidgetItem(str(i)))
            self._code_table.setItem(row, 1, QTableWidgetItem(item["name"]))
            self._code_table.setItem(row, 2, QTableWidgetItem(item["role"]))
            for col in range(3):
                it = self._code_table.item(row, col)
                if it:
                    it.setTextAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        self._code_table.resizeRowsToContents()
        self._code_table.setVisible(True)
        self._code_grid_lbl.setVisible(True)
        self._code_detail_panel.setVisible(False)
        self._code_items = items

    def _on_code_row_clicked(self, row: int, _col: int):
        if not hasattr(self, "_code_items") or row >= len(self._code_items):
            return
        item = self._code_items[row]
        self._code_detail_title.setText(item["name"])
        self._code_detail_body.setText(
            f"<b>Syntax:</b> <code>{item.get('syntax','—')}</code><br><br>"
            f"<b>How it works:</b> {item.get('how','—')}<br><br>"
            f"<b>Purpose:</b> {item.get('purpose','—')}<br><br>"
            f"<b>Usage example:</b><br><code>{item.get('usage','—')}</code>"
        )
        self._code_detail_panel.setVisible(True)

    def _extract_code_items(self, code: str) -> list[dict]:
        items: list[dict] = []
        for line in code.splitlines():
            s = line.strip()
            m = re.match(r'^(?:from\s+(\S+)\s+)?import\s+(.+)', s)
            if m:
                module = m.group(1) or ""
                names  = m.group(2).split(",")[0].strip().split(" as ")[0].strip()
                items.append({"name": names, "role": f"import from {module}" if module else "import",
                              "syntax": s, "how": "Loads an external module or symbol.",
                              "purpose": f"Makes '{names}' available.", "usage": s})
                continue
            m = re.match(r'^class\s+(\w+)\s*(?:\(([^)]*)\))?:', s)
            if m:
                cname, bases = m.group(1), m.group(2) or "object"
                items.append({"name": cname, "role": f"class  (inherits: {bases})",
                              "syntax": f"class {cname}({bases}):",
                              "how": "Defines a blueprint for creating objects.",
                              "purpose": f"Encapsulates data and behaviour as '{cname}'.",
                              "usage": f"obj = {cname}()"})
                continue
            m = re.match(r'^(?:async\s+)?def\s+(\w+)\s*\(([^)]*)\)', s)
            if m:
                fname, params = m.group(1), m.group(2).strip()
                kind = "method" if params.startswith("self") else "function"
                items.append({"name": fname, "role": kind,
                              "syntax": f"def {fname}({params}):",
                              "how": f"Callable block invoked as {fname}(…).",
                              "purpose": f"Performs a specific task.", "usage": f"{fname}({params})"})
                continue
            m = re.match(r'^([A-Z_][A-Z0-9_]{2,})\s*=\s*(.+)', s)
            if m:
                vname, val = m.group(1), m.group(2)[:60]
                items.append({"name": vname, "role": "constant / config",
                              "syntax": f"{vname} = {val}",
                              "how": "Module-level name bound to a fixed value.",
                              "purpose": f"Stores '{val}' for reuse.", "usage": vname})
        return items[:30]

    def _overall_code_summary(self, code: str, items: list[dict]) -> str:
        n_lines   = len([l for l in code.splitlines() if l.strip()])
        classes   = [i for i in items if "class"    in i["role"]]
        functions = [i for i in items if i["role"]  in ("function", "method")]
        imports   = [i for i in items if "import"   in i["role"]]
        constants = [i for i in items if "constant" in i["role"]]
        parts = [f"{n_lines} lines"]
        if classes:
            parts.append(f"{len(classes)} class{'es' if len(classes)>1 else ''} "
                         f"({', '.join(c['name'] for c in classes[:3])})")
        if functions:
            parts.append(f"{len(functions)} function/method{'s' if len(functions)>1 else ''}")
        if imports:
            parts.append(f"{len(imports)} import{'s' if len(imports)>1 else ''}")
        if constants:
            parts.append(f"{len(constants)} constant{'s' if len(constants)>1 else ''}")
        return "  ·  ".join(parts) + "."
