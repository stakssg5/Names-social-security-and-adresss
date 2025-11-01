from __future__ import annotations

import random
from typing import List

from PySide6.QtCore import Qt, QTimer, QRect
from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QSizePolicy,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)


SEARCH_PHRASES = [
    "razor grit yard",
    "wall issue ready",
    "fuel luggage ramp",
    "match anchor menu",
    "client float lamp",
    "photo quarter alley",
    "cabin shadow valley",
    "prefer dawn glass",
    "ripple next canyon",
    "monitor pilot tape",
]


def format_count(value: int) -> str:
    return f"{value:,}".replace(",", " ")


class CircleIcon(QWidget):
    def __init__(
        self,
        text: str,
        background: str,
        *,
        size: int = 52,
        text_color: str = "#F8FAFC",
        accent: str | None = None,
    ) -> None:
        super().__init__()
        self._text = text
        self._bg = QColor(background)
        self._fg = QColor(text_color)
        self._accent = QColor(accent) if accent else None
        self._size = size
        self.setFixedSize(size, size)

    def paintEvent(self, event) -> None:  # type: ignore[override]
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        rect = event.rect()
        painter.setBrush(self._bg)
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(rect)

        if self._accent is not None:
            accent_size = max(6, self._size // 6)
            accent_rect = QRect(
                rect.right() - accent_size - 6,
                rect.top() + 6,
                accent_size,
                accent_size,
            )
            painter.setBrush(self._accent)
            painter.drawEllipse(accent_rect)

        painter.setPen(self._fg)
        font = painter.font()
        font.setBold(True)
        font_size = max(10, int(self._size * 0.42))
        if len(self._text) == 2:
            font_size = max(10, int(self._size * 0.33))
        font.setPointSize(font_size)
        painter.setFont(font)
        painter.drawText(rect, Qt.AlignCenter, self._text)


class SearchResultItem(QFrame):
    def __init__(self) -> None:
        super().__init__()
        self.setProperty("cardRole", "result")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(10)

        self.balance_label = QLabel("Balance 0")
        self.balance_label.setObjectName("resultBalance")
        layout.addWidget(self.balance_label)

        self.details_label = QLabel("| Wallet check | demo phrase")
        self.details_label.setObjectName("resultDetails")
        self.details_label.setWordWrap(True)
        layout.addWidget(self.details_label, 1)

    def update_phrase(self, phrase: str) -> None:
        self.details_label.setText(f"| Wallet check | {phrase}")


class ProfitCard(QFrame):
    def __init__(self) -> None:
        super().__init__()
        self.setProperty("cardRole", "profit")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(16)

        self.icon = CircleIcon("B", "#F7931A", accent="#8D6BFF")
        layout.addWidget(self.icon, alignment=Qt.AlignTop)

        text_col = QVBoxLayout()
        text_col.setSpacing(6)

        self.amount_label = QLabel("0,01035 BTC")
        self.amount_label.setObjectName("profitAmount")
        text_col.addWidget(self.amount_label)

        self.usd_label = QLabel("$1120.73")
        self.usd_label.setObjectName("profitUsd")
        text_col.addWidget(self.usd_label)

        self.memo_label = QLabel("pulp parent...")
        self.memo_label.setObjectName("profitMemo")
        text_col.addWidget(self.memo_label)
        text_col.addStretch(1)

        layout.addLayout(text_col, 1)

        self.copy_btn = QPushButton("Copy")
        self.copy_btn.setObjectName("profitCopy")
        layout.addWidget(self.copy_btn, alignment=Qt.AlignTop)

    def update_fields(self, amount: str, usd: str, memo: str) -> None:
        self.amount_label.setText(amount)
        self.usd_label.setText(usd)
        self.memo_label.setText(memo)


class BottomNavItem(QWidget):
    def __init__(self, text: str, label: str, *, highlighted: bool = False) -> None:
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)
        icon_color = "#7C3AED" if highlighted else "#1F273A"
        fg = "#0F172A" if highlighted else "#94A3B8"
        self.icon = CircleIcon(text, icon_color, size=40, text_color=fg)
        layout.addWidget(self.icon, alignment=Qt.AlignHCenter)

        lbl = QLabel(label)
        lbl.setObjectName("navLabel")
        if highlighted:
            lbl.setProperty("state", "active")
        layout.addWidget(lbl, alignment=Qt.AlignHCenter)


class CryptoPRWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Crypto PR+")
        self.resize(430, 880)

        self._timer = QTimer(self)
        self._timer.setInterval(1700)
        self._timer.timeout.connect(self._tick)

        self._is_running = False
        self._checked_wallets = 0

        self._build_ui()
        self._apply_styles()
        self._set_idle_state()

    def _build_ui(self) -> None:
        central = QWidget(self)
        central.setObjectName("central")
        self.setCentralWidget(central)

        layout = QVBoxLayout(central)
        layout.setContentsMargins(32, 36, 32, 28)
        layout.setSpacing(24)

        self.header_label = QLabel("Checked Wallets")
        self.header_label.setObjectName("headerLabel")
        layout.addWidget(self.header_label)

        self.count_label = QLabel("0")
        self.count_label.setObjectName("countLabel")
        layout.addWidget(self.count_label)

        self.section_label = QLabel("Search results")
        self.section_label.setObjectName("sectionLabel")
        layout.addWidget(self.section_label)

        self.cards_stack = QStackedWidget()
        layout.addWidget(self.cards_stack)

        self.search_results_widget = QWidget()
        results_layout = QVBoxLayout(self.search_results_widget)
        results_layout.setContentsMargins(0, 0, 0, 0)
        results_layout.setSpacing(12)
        self.result_items: List[SearchResultItem] = []
        for _ in range(3):
            item = SearchResultItem()
            self.result_items.append(item)
            results_layout.addWidget(item)
        results_layout.addStretch(1)
        self.cards_stack.addWidget(self.search_results_widget)

        self.profits_widget = QWidget()
        profits_layout = QVBoxLayout(self.profits_widget)
        profits_layout.setContentsMargins(0, 0, 0, 0)
        profits_layout.setSpacing(12)
        self.profit_card = ProfitCard()
        profits_layout.addWidget(self.profit_card)
        profits_layout.addStretch(1)
        self.cards_stack.addWidget(self.profits_widget)

        coins_widget = QWidget()
        coins_layout = QGridLayout(coins_widget)
        coins_layout.setContentsMargins(0, 0, 0, 0)
        coins_layout.setHorizontalSpacing(18)
        coins_layout.setVerticalSpacing(14)
        coins = [
            ("B", "#F7931A", "#8D6BFF"),
            ("E", "#4C5BD4", None),
            ("B", "#F0B90B", None),
            ("S", "#14F195", None),
            ("A", "#E84142", None),
            ("L", "#B8C1CC", None),
            ("O", "#FF0420", None),
            ("M", "#8247E5", None),
            ("T", "#0098EA", None),
            ("R", "#FF010A", None),
        ]
        for idx, (text, color, accent) in enumerate(coins):
            icon = CircleIcon(text, color, accent=accent)
            icon.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
            row = idx // 5
            col = idx % 5
            coins_layout.addWidget(icon, row, col, alignment=Qt.AlignCenter)
        layout.addWidget(coins_widget)

        self.start_stop_btn = QPushButton("Start search")
        self.start_stop_btn.setObjectName("primaryButton")
        self.start_stop_btn.clicked.connect(self._toggle_state)
        layout.addWidget(self.start_stop_btn)

        layout.addStretch(1)

        bottom_nav = QWidget()
        bottom_nav.setObjectName("bottomNav")
        nav_layout = QHBoxLayout(bottom_nav)
        nav_layout.setContentsMargins(0, 0, 0, 0)
        nav_layout.setSpacing(18)

        self.nav_profile = BottomNavItem("P", "My profile")
        nav_layout.addWidget(self.nav_profile)

        self.nav_plans = BottomNavItem("$", "Plans")
        nav_layout.addWidget(self.nav_plans)

        self.nav_search = QPushButton()
        self.nav_search.setObjectName("searchFab")
        self.nav_search.setText("")
        nav_layout.addWidget(self.nav_search)

        self.nav_support = BottomNavItem("C", "Support")
        nav_layout.addWidget(self.nav_support)

        self.nav_faq = BottomNavItem("?", "FAQ")
        nav_layout.addWidget(self.nav_faq)

        layout.addWidget(bottom_nav)

    def _apply_styles(self) -> None:
        self.setStyleSheet(
            """
            QWidget#central {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #0d1024, stop:1 #121a3f);
                color: #E2E8F0;
                font-family: 'Segoe UI', 'Helvetica Neue', Arial;
            }
            QLabel#headerLabel {
                font-size: 18px;
                color: #A5B4FC;
            }
            QLabel#countLabel {
                font-size: 58px;
                font-weight: 700;
                color: #7C80FF;
            }
            QLabel#sectionLabel {
                font-size: 20px;
                font-weight: 600;
            }
            QFrame[cardRole="result"] {
                background-color: rgba(255, 255, 255, 0.05);
                border-radius: 18px;
            }
            QLabel#resultBalance {
                color: #9F8CFF;
                font-weight: 600;
            }
            QLabel#resultDetails {
                color: rgba(226, 232, 240, 0.85);
            }
            QFrame[cardRole="profit"] {
                background-color: rgba(255, 255, 255, 0.07);
                border-radius: 20px;
            }
            QLabel#profitAmount {
                font-size: 22px;
                font-weight: 700;
            }
            QLabel#profitUsd {
                color: #4ADE80;
                font-size: 16px;
                font-weight: 600;
            }
            QLabel#profitMemo {
                color: rgba(226, 232, 240, 0.75);
            }
            QPushButton#profitCopy {
                background-color: rgba(255, 255, 255, 0.12);
                color: #E2E8F0;
                border: none;
                padding: 6px 14px;
                border-radius: 12px;
                font-weight: 600;
            }
            QPushButton#profitCopy:hover {
                background-color: rgba(255, 255, 255, 0.2);
            }
            QPushButton#primaryButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #7C3AED, stop:1 #6366F1);
                border-radius: 18px;
                padding: 16px 24px;
                font-size: 18px;
                font-weight: 700;
                color: #F8FAFC;
                border: none;
            }
            QPushButton#primaryButton[state="stop"] {
                background: #F1F5F9;
                color: #111827;
            }
            QWidget#bottomNav {
                background-color: rgba(15, 23, 42, 0.55);
                border-radius: 30px;
                padding: 12px 18px;
            }
            QLabel#navLabel {
                color: #94A3B8;
                font-size: 12px;
            }
            QLabel#navLabel[state="active"] {
                color: #C4C6FF;
            }
            QPushButton#searchFab {
                min-height: 72px;
                min-width: 72px;
                max-height: 72px;
                max-width: 72px;
                border-radius: 36px;
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #8B5CF6, stop:1 #6366F1);
                border: none;
            }
            QPushButton#searchFab::after {
                content: "";
            }
            """
        )

    def _set_idle_state(self) -> None:
        self._timer.stop()
        self._is_running = False
        self._checked_wallets = 3_830_672
        self.count_label.setText(format_count(self._checked_wallets))
        self.section_label.setText("Profits")
        self.cards_stack.setCurrentWidget(self.profits_widget)
        self.start_stop_btn.setText("Start search")
        self.start_stop_btn.setProperty("state", "start")
        self.start_stop_btn.style().unpolish(self.start_stop_btn)
        self.start_stop_btn.style().polish(self.start_stop_btn)
        self.profit_card.update_fields("0,01035 BTC", "$1120.73", "pulp parent...")

    def _start_running(self) -> None:
        self._is_running = True
        self._checked_wallets = 0
        self.count_label.setText(format_count(self._checked_wallets))
        self.section_label.setText("Search results")
        self.cards_stack.setCurrentWidget(self.search_results_widget)
        self.start_stop_btn.setText("Stop")
        self.start_stop_btn.setProperty("state", "stop")
        self.start_stop_btn.style().unpolish(self.start_stop_btn)
        self.start_stop_btn.style().polish(self.start_stop_btn)
        self._update_results()
        self._timer.start()

    def _toggle_state(self) -> None:
        if self._is_running:
            self._set_idle_state()
        else:
            self._start_running()

    def _update_results(self) -> None:
        phrases = random.sample(SEARCH_PHRASES, k=3)
        for widget, phrase in zip(self.result_items, phrases):
            widget.update_phrase(phrase)

    def _tick(self) -> None:
        if not self._is_running:
            return
        increment = random.randint(120, 720)
        self._checked_wallets += increment
        self.count_label.setText(format_count(self._checked_wallets))
        self._update_results()


def main() -> None:
    app = QApplication.instance() or QApplication([])
    window = CryptoPRWindow()
    window.show()
    app.exec()


__all__ = ["CryptoPRWindow", "main"]
