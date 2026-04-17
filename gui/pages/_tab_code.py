"""gui/pages/_tab_code.py — Code analysis tab for the Dashboard (IDE mode)."""

import re
import subprocess
import sys
import tempfile
import os

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTextEdit, QTableWidget, QTableWidgetItem, QHeaderView,
    QAbstractItemView, QScrollArea, QFrame, QComboBox, QSplitter
)
from PyQt6.QtCore import Qt, QTimer, QThread, pyqtSignal, QObject
from PyQt6.QtGui import QFont, QColor


# ── Background runner ─────────────────────────────────────────────────────────

class _RunSignals(QObject):
    finished = pyqtSignal(str, str)   # stdout, stderr


class _RunThread(QThread):
    def __init__(self, code: str, lang: str, signals: _RunSignals):
        super().__init__()
        self._code    = code
        self._lang    = lang
        self._signals = signals

    def run(self):
        stdout, stderr = _execute_code(self._code, self._lang)
        self._signals.finished.emit(stdout, stderr)


def _execute_code(code: str, lang: str) -> tuple[str, str]:
    """Run code locally in a temp file. Returns (stdout, stderr)."""
    try:
        suffix_map = {
            "Python":     ".py",
            "JavaScript": ".js",
            "Bash":       ".sh",
        }
        runner_map = {
            "Python":     [sys.executable],
            "JavaScript": ["node"],
            "Bash":       ["bash"],
        }
        suffix = suffix_map.get(lang, ".py")
        runner = runner_map.get(lang, [sys.executable])

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=suffix, delete=False, encoding="utf-8"
        ) as f:
            f.write(code)
            tmp_path = f.name

        result = subprocess.run(
            runner + [tmp_path],
            capture_output=True, text=True, timeout=10
        )
        return result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return "", "⏱ Execution timed out (10 s limit)."
    except FileNotFoundError as e:
        return "", f"Runtime not found: {e}\nInstall the required interpreter."
    except Exception as e:
        return "", str(e)
    finally:
        try:
            os.unlink(tmp_path)
        except Exception:
            pass


# ── Tab mixin ─────────────────────────────────────────────────────────────────

class CodeTabMixin:
    """Code tab — analysis + local IDE playground per key point."""

    def _build_code_tab(self) -> QWidget:
        frame = QWidget()
        frame.setObjectName("tabPage")
        outer = QVBoxLayout(frame)
        outer.setContentsMargins(0, 18, 0, 0)
        outer.setSpacing(0)

        # Scrollable content
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setObjectName("settingsScroll")
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        inner = QWidget()
        inner.setObjectName("tabPage")
        lay = QVBoxLayout(inner)
        lay.setContentsMargins(0, 0, 0, 18)
        lay.setSpacing(10)

        # ── Input ─────────────────────────────────────────────────────────
        in_hdr = QHBoxLayout()
        in_hdr.setContentsMargins(0, 0, 0, 6)
        in_lbl = QLabel("Paste code")
        in_lbl.setObjectName("featureLabel")
        in_lbl.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        in_hdr.addWidget(in_lbl)
        in_hdr.addStretch()

        # Language selector
        self._code_lang = QComboBox()
        self._code_lang.setObjectName("translateCombo")
        self._code_lang.setFixedHeight(28)
        for lang in ["Python", "JavaScript", "Bash"]:
            self._code_lang.addItem(lang)
        in_hdr.addWidget(self._code_lang)

        clear_btn = QPushButton("Clear")
        clear_btn.setObjectName("btnOutline")
        clear_btn.setFixedSize(70, 28)
        clear_btn.clicked.connect(self._clear_code)
        in_hdr.addWidget(clear_btn)
        lay.addLayout(in_hdr)

        self._code_input = QTextEdit()
        self._code_input.setObjectName("codeEdit")
        self._code_input.setPlaceholderText("Paste your code here…")
        self._code_input.setFixedHeight(160)
        mono = QFont("Consolas", 10)
        mono.setStyleHint(QFont.StyleHint.Monospace)
        self._code_input.setFont(mono)
        lay.addWidget(self._code_input)

        # Action row
        act_row = QHBoxLayout()
        act_row.setContentsMargins(0, 0, 0, 0)
        act_row.setSpacing(10)
        act_row.addStretch()
        analyse_btn = QPushButton("Analyse")
        analyse_btn.setObjectName("btnPrimary")
        analyse_btn.setFixedSize(100, 30)
        analyse_btn.clicked.connect(self._run_code_analyse)
        act_row.addWidget(analyse_btn)
        lay.addLayout(act_row)

        # Overview bar
        self._code_summary_lbl = QLabel("")
        self._code_summary_lbl.setObjectName("codeSummaryLbl")
        self._code_summary_lbl.setWordWrap(True)
        self._code_summary_lbl.setVisible(False)
        lay.addWidget(self._code_summary_lbl)

        # Grid label
        self._code_grid_lbl = QLabel("Key points  —  click ▶ Run to test each snippet locally")
        self._code_grid_lbl.setObjectName("featureLabel")
        self._code_grid_lbl.setVisible(False)
        lay.addWidget(self._code_grid_lbl)

        # Expandable key-point rows container
        self._code_rows_widget = QWidget()
        self._code_rows_widget.setObjectName("tabPage")
        self._code_rows_lay = QVBoxLayout(self._code_rows_widget)
        self._code_rows_lay.setContentsMargins(0, 0, 0, 0)
        self._code_rows_lay.setSpacing(6)
        self._code_rows_lay.addStretch()
        lay.addWidget(self._code_rows_widget)

        lay.addStretch()
        scroll.setWidget(inner)
        outer.addWidget(scroll, 1)
        return frame

    # ── Analysis ──────────────────────────────────────────────────────────────

    def _clear_code(self):
        self._code_input.clear()
        self._code_summary_lbl.setVisible(False)
        self._code_grid_lbl.setVisible(False)
        while self._code_rows_lay.count() > 1:
            item = self._code_rows_lay.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def _run_code_analyse(self):
        code = self._code_input.toPlainText().strip()
        if not code:
            return
        items   = self._extract_code_items(code)
        overall = self._overall_code_summary(code, items)
        self._code_summary_lbl.setText(f"<b>Overview:</b> {overall}")
        self._code_summary_lbl.setVisible(True)

        # Clear old rows
        while self._code_rows_lay.count() > 1:
            item = self._code_rows_lay.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        lang = self._code_lang.currentText()
        for i, item in enumerate(items, start=1):
            row = _CodeKeyPointRow(i, item, lang, self)
            self._code_rows_lay.insertWidget(self._code_rows_lay.count() - 1, row)

        self._code_grid_lbl.setVisible(True)

    def _extract_code_items(self, code: str) -> list[dict]:
        items: list[dict] = []
        for line in code.splitlines():
            s = line.strip()
            m = re.match(r'^(?:from\s+(\S+)\s+)?import\s+(.+)', s)
            if m:
                module = m.group(1) or ""
                names  = m.group(2).split(",")[0].strip().split(" as ")[0].strip()
                items.append({
                    "name": names, "role": f"import from {module}" if module else "import",
                    "syntax": s, "how": "Loads an external module or symbol.",
                    "purpose": f"Makes '{names}' available.", "usage": s,
                    "sample": s,
                })
                continue
            m = re.match(r'^class\s+(\w+)\s*(?:\(([^)]*)\))?:', s)
            if m:
                cname, bases = m.group(1), m.group(2) or "object"
                items.append({
                    "name": cname, "role": f"class  (inherits: {bases})",
                    "syntax": f"class {cname}({bases}):",
                    "how": "Defines a blueprint for creating objects.",
                    "purpose": f"Encapsulates data and behaviour as '{cname}'.",
                    "usage": f"obj = {cname}()",
                    "sample": f"class {cname}({bases}):\n    pass\n\nobj = {cname}()\nprint(obj)",
                })
                continue
            m = re.match(r'^(?:async\s+)?def\s+(\w+)\s*\(([^)]*)\)', s)
            if m:
                fname, params = m.group(1), m.group(2).strip()
                kind = "method" if params.startswith("self") else "function"
                call_params = ", ".join(
                    "None" for p in params.split(",")
                    if p.strip() and p.strip() != "self"
                ) if params else ""
                items.append({
                    "name": fname, "role": kind,
                    "syntax": f"def {fname}({params}):",
                    "how": f"Callable block invoked as {fname}(…).",
                    "purpose": "Performs a specific task.",
                    "usage": f"{fname}({call_params})",
                    "sample": (
                        f"def {fname}({params}):\n"
                        f"    # TODO: implement\n"
                        f"    pass\n\n"
                        f"result = {fname}({call_params})\n"
                        f"print(result)"
                    ),
                })
                continue
            m = re.match(r'^([A-Z_][A-Z0-9_]{2,})\s*=\s*(.+)', s)
            if m:
                vname, val = m.group(1), m.group(2)[:60]
                items.append({
                    "name": vname, "role": "constant / config",
                    "syntax": f"{vname} = {val}",
                    "how": "Module-level name bound to a fixed value.",
                    "purpose": f"Stores '{val}' for reuse.", "usage": vname,
                    "sample": f"{vname} = {val}\nprint({vname})",
                })
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


# ══════════════════════════════════════════════════════════════════════════════
# Expandable key-point row with inline IDE playground
# ══════════════════════════════════════════════════════════════════════════════

class _CodeKeyPointRow(QWidget):
    """
    One key-point row:
      Collapsed  — shows #, name, role, ▶ Run button
      Expanded   — shows explanation + editable code editor + output panel
    Click the header to toggle expand/collapse.
    ▶ Run executes the sample code locally without expanding.
    """

    def __init__(self, index: int, item: dict, lang: str, mixin, parent=None):
        super().__init__(parent)
        self._item     = item
        self._lang     = lang
        self._mixin    = mixin
        self._expanded = False
        self._thread: QThread | None = None

        self.setObjectName("expandableRow")
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Header ────────────────────────────────────────────────────────
        header = QWidget()
        header.setObjectName("expandableRowHeader")
        header.setCursor(Qt.CursorShape.PointingHandCursor)
        h_lay = QHBoxLayout(header)
        h_lay.setContentsMargins(10, 7, 10, 7)
        h_lay.setSpacing(8)

        self._toggle_lbl = QLabel("▶")
        self._toggle_lbl.setFixedWidth(14)
        self._toggle_lbl.setStyleSheet("color: #888; font-size: 10px; background: transparent;")
        h_lay.addWidget(self._toggle_lbl)

        num_lbl = QLabel(str(index))
        num_lbl.setFixedWidth(22)
        num_lbl.setStyleSheet("color: #888; font-size: 11px; background: transparent;")
        h_lay.addWidget(num_lbl)

        name_lbl = QLabel(item["name"])
        name_lbl.setObjectName("cardTitle")
        name_lbl.setFixedWidth(140)
        h_lay.addWidget(name_lbl)

        role_lbl = QLabel(item["role"])
        role_lbl.setObjectName("cardBody")
        role_lbl.setStyleSheet("font-size: 12px;")
        h_lay.addWidget(role_lbl, 1)

        # ▶ Run button — runs without expanding
        self._run_btn = QPushButton("▶  Run")
        self._run_btn.setObjectName("btnPrimary")
        self._run_btn.setFixedSize(70, 26)
        self._run_btn.clicked.connect(self._run_sample)
        h_lay.addWidget(self._run_btn)

        root.addWidget(header)
        header.mousePressEvent = lambda _: self._toggle()

        # ── Expanded body ─────────────────────────────────────────────────
        self._body = QWidget()
        self._body.setObjectName("expandableRowBody")
        self._body.setVisible(False)
        b_lay = QVBoxLayout(self._body)
        b_lay.setContentsMargins(14, 8, 14, 12)
        b_lay.setSpacing(8)

        # Explanation
        explain_lbl = QLabel(
            f"<b>Syntax:</b> <code>{item.get('syntax','—')}</code><br>"
            f"<b>How it works:</b> {item.get('how','—')}<br>"
            f"<b>Purpose:</b> {item.get('purpose','—')}"
        )
        explain_lbl.setObjectName("cardBody")
        explain_lbl.setWordWrap(True)
        explain_lbl.setTextFormat(Qt.TextFormat.RichText)
        explain_lbl.setStyleSheet("font-size: 12px;")
        b_lay.addWidget(explain_lbl)

        # Code editor label row
        editor_hdr = QHBoxLayout()
        editor_hdr.setContentsMargins(0, 4, 0, 0)
        editor_lbl = QLabel("Sample code  —  edit and run:")
        editor_lbl.setObjectName("featureLabel")
        editor_lbl.setStyleSheet("font-size: 11px;")
        editor_hdr.addWidget(editor_lbl)
        editor_hdr.addStretch()

        run_full_btn = QPushButton("▶  Run")
        run_full_btn.setObjectName("btnPrimary")
        run_full_btn.setFixedSize(70, 26)
        run_full_btn.clicked.connect(self._run_sample)
        editor_hdr.addWidget(run_full_btn)

        reset_btn = QPushButton("Reset")
        reset_btn.setObjectName("btnOutline")
        reset_btn.setFixedSize(60, 26)
        reset_btn.clicked.connect(self._reset_sample)
        editor_hdr.addWidget(reset_btn)
        b_lay.addLayout(editor_hdr)

        # Code editor
        self._editor = QTextEdit()
        self._editor.setObjectName("codeEdit")
        self._editor.setFixedHeight(120)
        mono = QFont("Consolas", 10)
        mono.setStyleHint(QFont.StyleHint.Monospace)
        self._editor.setFont(mono)
        self._editor.setPlainText(item.get("sample", item.get("usage", "")))
        b_lay.addWidget(self._editor)

        # Output panel
        out_hdr = QHBoxLayout()
        out_hdr.setContentsMargins(0, 4, 0, 0)
        out_lbl = QLabel("Output:")
        out_lbl.setObjectName("featureLabel")
        out_lbl.setStyleSheet("font-size: 11px;")
        out_hdr.addWidget(out_lbl)
        out_hdr.addStretch()
        self._status_lbl = QLabel("")
        self._status_lbl.setStyleSheet("font-size: 11px; background: transparent;")
        out_hdr.addWidget(self._status_lbl)
        b_lay.addLayout(out_hdr)

        self._output = QTextEdit()
        self._output.setObjectName("codeEdit")
        self._output.setReadOnly(True)
        self._output.setFixedHeight(90)
        self._output.setFont(mono)
        self._output.setPlaceholderText("Run the code to see output here…")
        b_lay.addWidget(self._output)

        root.addWidget(self._body)

    # ── Toggle ────────────────────────────────────────────────────────────────

    def _toggle(self):
        self._expanded = not self._expanded
        self._body.setVisible(self._expanded)
        self._toggle_lbl.setText("▼" if self._expanded else "▶")

    # ── Run ───────────────────────────────────────────────────────────────────

    def _run_sample(self):
        code = self._editor.toPlainText().strip() if self._expanded \
               else self._item.get("sample", self._item.get("usage", ""))
        if not code:
            return

        # Show output panel if collapsed
        if not self._expanded:
            self._toggle()

        self._run_btn.setEnabled(False)
        self._run_btn.setText("…")
        self._status_lbl.setText("Running…")
        self._status_lbl.setStyleSheet("color: #888888; font-size: 11px; background: transparent;")
        self._output.setPlainText("")

        signals = _RunSignals()
        signals.finished.connect(self._on_run_finished)
        self._thread = _RunThread(code, self._lang, signals)
        self._thread.start()

    def _on_run_finished(self, stdout: str, stderr: str):
        self._run_btn.setEnabled(True)
        self._run_btn.setText("▶  Run")

        if stderr and not stdout:
            self._output.setPlainText(stderr)
            self._status_lbl.setText("✗ Error")
            self._status_lbl.setStyleSheet(
                "color: #e53935; font-size: 11px; background: transparent;"
            )
        else:
            combined = stdout
            if stderr:
                combined += f"\n--- stderr ---\n{stderr}"
            self._output.setPlainText(combined or "(no output)")
            self._status_lbl.setText("✓ Done")
            self._status_lbl.setStyleSheet(
                "color: #4caf50; font-size: 11px; background: transparent;"
            )

    def _reset_sample(self):
        self._editor.setPlainText(self._item.get("sample", self._item.get("usage", "")))
        self._output.clear()
        self._status_lbl.setText("")
