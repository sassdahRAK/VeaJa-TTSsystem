"""gui/pages/_tab_summary.py — Summary tab for the Dashboard."""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTextEdit, QStackedWidget, QTableWidget, QTableWidgetItem,
    QHeaderView, QAbstractItemView
)
from PyQt6.QtCore import Qt


class SummaryTabMixin:
    """Summary tab builder and summarise logic."""

    def _build_summary_tab(self) -> QWidget:
        frame = QWidget()
        frame.setObjectName("tabPage")
        lay = QVBoxLayout(frame)
        lay.setContentsMargins(0, 18, 0, 0)
        lay.setSpacing(12)

        # Sub-tab bar
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

        # Input
        input_box = QWidget()
        input_box.setObjectName("featureBox")
        ib_lay = QVBoxLayout(input_box)
        ib_lay.setContentsMargins(0, 0, 0, 0)
        ib_lay.setSpacing(0)

        QLabel("Text to summarise", objectName="featureLabel").setParent(input_box)
        input_label = QLabel("Text to summarise")
        input_label.setObjectName("featureLabel")
        ib_lay.addWidget(input_label)

        self._summary_input = QTextEdit()
        self._summary_input.setObjectName("featureEdit")
        self._summary_input.setPlaceholderText("Paste or type the long content you want to summarise…")
        self._summary_input.setFixedHeight(130)
        ib_lay.addWidget(self._summary_input)
        lay.addWidget(input_box)

        # Action row
        action_row = QHBoxLayout()
        action_row.setContentsMargins(0, 0, 0, 0)
        action_row.setSpacing(10)
        action_row.addStretch()

        clear_btn = QPushButton("Clear")
        clear_btn.setObjectName("btnOutline")
        clear_btn.setFixedSize(80, 30)
        clear_btn.clicked.connect(self._clear_summary)
        action_row.addWidget(clear_btn)

        summarise_btn = QPushButton("Summarise")
        summarise_btn.setObjectName("btnPrimary")
        summarise_btn.setFixedSize(100, 30)
        summarise_btn.clicked.connect(self._run_summary)
        action_row.addWidget(summarise_btn)
        lay.addLayout(action_row)

        # Output stack
        self._summary_output_stack = QStackedWidget()

        # Normal output
        normal_out_box = QWidget()
        normal_out_box.setObjectName("featureBox")
        no_lay = QVBoxLayout(normal_out_box)
        no_lay.setContentsMargins(0, 0, 0, 0)
        no_lay.setSpacing(0)
        no_lay.addWidget(QLabel("Summary", objectName="featureLabel"))
        self._summary_normal_out = QTextEdit()
        self._summary_normal_out.setObjectName("featureEditReadOnly")
        self._summary_normal_out.setReadOnly(True)
        self._summary_normal_out.setPlaceholderText("Summary will appear here…")
        no_lay.addWidget(self._summary_normal_out, 1)
        self._summary_output_stack.addWidget(normal_out_box)

        # Grid output
        grid_out_box = QWidget()
        grid_out_box.setObjectName("featureBox")
        go_lay = QVBoxLayout(grid_out_box)
        go_lay.setContentsMargins(0, 0, 0, 0)
        go_lay.setSpacing(0)
        go_lay.addWidget(QLabel("Key points", objectName="featureLabel"))
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
        self._summary_output_stack.addWidget(grid_out_box)

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
        text = self._summary_input.toPlainText().strip()
        if not text:
            return
        sentences = [s.strip() for s in text.replace("\n", " ").split(".") if s.strip()]

        normal_result = ". ".join(sentences[:3])
        if normal_result and not normal_result.endswith("."):
            normal_result += "."
        self._summary_normal_out.setPlainText(normal_result)

        self._summary_grid_out.setRowCount(0)
        for i, sentence in enumerate(sentences[:10], start=1):
            row = self._summary_grid_out.rowCount()
            self._summary_grid_out.insertRow(row)
            p = QTableWidgetItem(f"Point {i}")
            d = QTableWidgetItem(sentence + ".")
            p.setTextAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
            d.setTextAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
            self._summary_grid_out.setItem(row, 0, p)
            self._summary_grid_out.setItem(row, 1, d)
        self._summary_grid_out.resizeRowsToContents()
