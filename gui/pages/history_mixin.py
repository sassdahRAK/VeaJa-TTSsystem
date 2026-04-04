import os

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QFrame, QListWidget, QListWidgetItem
)
from PyQt6.QtCore import Qt, QSize

from gui.icon_utils import svg_icon
from gui._window_shared import ASSETS  # noqa: F401


class HistoryMixin:
    """Mixin providing History page methods for MainWindow."""

    # ── History page ───────────────────────────────────────────────────────────

    def _build_history_page(self) -> QWidget:
        page = QWidget()
        page.setObjectName("contentPage")
        lay = QVBoxLayout(page)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        hdr = QWidget()
        hdr.setObjectName("pageHeader")
        h_lay = QHBoxLayout(hdr)
        h_lay.setContentsMargins(32, 28, 32, 20)
        title = QLabel("History recall")
        title.setObjectName("pageTitle")
        h_lay.addWidget(title)
        h_lay.addStretch()
        clear_btn = QPushButton("Clear")
        clear_btn.setObjectName("btnOutline")
        clear_btn.setFixedSize(72, 28)
        clear_btn.clicked.connect(self._clear_history)
        h_lay.addWidget(clear_btn)
        lay.addWidget(hdr)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        self._history_cards_widget = QWidget()
        self._history_cards_layout = QVBoxLayout(self._history_cards_widget)
        self._history_cards_layout.setContentsMargins(32, 0, 32, 32)
        self._history_cards_layout.setSpacing(14)
        self._history_cards_layout.addStretch()

        scroll.setWidget(self._history_cards_widget)
        lay.addWidget(scroll, 1)

        # Hidden QListWidget kept for TourOverlay compat (spotlighting)
        self._history_list = QListWidget()
        self._history_list.setVisible(False)
        self._history_list.itemDoubleClicked.connect(self._on_history_item)
        # Also create prev/old lists for compat
        self._history_prev_list = QListWidget()
        self._history_prev_list.setVisible(False)
        self._history_old_list  = QListWidget()
        self._history_old_list.setVisible(False)
        lay.addWidget(self._history_list)
        lay.addWidget(self._history_prev_list)
        lay.addWidget(self._history_old_list)
        return page

    def _make_history_card(self, section_label: str, short: str,
                           full_text: str) -> QWidget:
        card = QWidget()
        card.setObjectName("historyCard")

        lay = QVBoxLayout(card)
        lay.setContentsMargins(18, 14, 14, 16)
        lay.setSpacing(8)

        # Header row: [label] [stretch] [delete icon button]
        hdr = QHBoxLayout()
        hdr.setSpacing(0)

        lbl = QLabel(section_label)
        lbl.setObjectName("historyCardLabel")
        hdr.addWidget(lbl)
        hdr.addStretch()

        del_btn = QPushButton()
        del_btn.setObjectName("historyDel")
        del_btn.setFixedSize(26, 26)
        del_btn.setFlat(True)
        del_btn.setToolTip("Delete")
        icon_color = "#888888"
        del_icon = svg_icon(os.path.join(ASSETS, "delete_icon.svg"), icon_color, 18)
        if not del_icon.isNull():
            del_btn.setIcon(del_icon)
            del_btn.setIconSize(QSize(18, 18))
        else:
            del_btn.setText("✕")
        del_btn.clicked.connect(lambda: self._delete_history_entry(full_text, card))
        hdr.addWidget(del_btn)

        lay.addLayout(hdr)

        # Body text
        body = QLabel(short)
        body.setObjectName("historyText")
        body.setWordWrap(True)
        lay.addWidget(body)
        return card

    def _delete_history_entry(self, full_text: str, card: QWidget):
        if full_text in self._history:
            idx = self._history.index(full_text)
            self._history.pop(idx)
            self._history_shorts.pop(idx)
        card.setParent(None)
        card.deleteLater()
        self._rebuild_history_lists()

    def _on_history_item(self, item: QListWidgetItem):
        text = item.data(Qt.ItemDataRole.UserRole)
        if text:
            self._text_edit.setPlainText(text)
            self._navigate(0)
            self._switch_tab(1)

    def _add_history(self, text: str):
        if text in self._history:
            return
        short = text[:80] + ("…" if len(text) > 80 else "")
        self._history.insert(0, text)
        self._history_shorts.insert(0, short)
        self._history        = self._history[:20]
        self._history_shorts = self._history_shorts[:20]
        self._rebuild_history_lists()

    def _rebuild_history_lists(self):
        # Clear hidden compat lists
        self._history_list.clear()
        self._history_prev_list.clear()
        self._history_old_list.clear()

        # Clear card widgets (except the stretch at end)
        while self._history_cards_layout.count() > 1:
            item = self._history_cards_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        section_labels = (
            ["Recent"]   * 7  +
            ["Previous"] * 7  +
            ["Old"]      * 6
        )
        for i, (full, short) in enumerate(
            zip(self._history, self._history_shorts)
        ):
            sec = section_labels[i] if i < len(section_labels) else "Old"
            # Card widget
            card = self._make_history_card(sec, short, full)
            self._history_cards_layout.insertWidget(
                self._history_cards_layout.count() - 1, card
            )
            # Hidden list item for TourOverlay compat
            li = QListWidgetItem(short)
            li.setData(Qt.ItemDataRole.UserRole, full)
            if i < 7:
                self._history_list.addItem(li)
            elif i < 14:
                self._history_prev_list.addItem(li)
            else:
                self._history_old_list.addItem(li)

    def _clear_history(self):
        self._history.clear()
        self._history_shorts.clear()
        self._rebuild_history_lists()
