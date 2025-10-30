from __future__ import annotations

import sys
from typing import Optional, Tuple

from PySide6.QtCore import Qt
from PySide6.QtGui import QClipboard
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QFileDialog,
    QMessageBox,
    QPushButton,
    QRadioButton,
    QStatusBar,
    QTextEdit,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from .atr import parse_atr, to_hex, build_simple_atr
from .pcsc import list_readers, connect_and_get_atr
from .atr_db import KNOWN_ATRS
from .apdu import parse_apdu_script, send_apdus


class ATRStudioWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Atr Zoe Utility")
        self.resize(980, 600)

        container = QWidget(self)
        layout = QGridLayout(container)
        layout.setColumnStretch(0, 1)
        layout.setColumnStretch(1, 1)

        self.atr_group = self._build_atr_group()
        self.custom_group = self._build_customize_group()

        layout.addWidget(self.atr_group, 0, 0)
        layout.addWidget(self.custom_group, 0, 1)
        self.setCentralWidget(container)

        self.status = QStatusBar()
        self.setStatusBar(self.status)

        # Initial refresh
        self._refresh_readers()

    # ----- UI builders -----
    def _build_atr_group(self) -> QGroupBox:
        g = QGroupBox("ATR")
        grid = QGridLayout(g)

        # Row 0: reader + type + refresh
        grid.addWidget(QLabel("Reader"), 0, 0)
        self.reader_combo = QComboBox()
        grid.addWidget(self.reader_combo, 0, 1)

        grid.addWidget(QLabel("Java Card Type"), 0, 2)
        self.card_type_combo = QComboBox()
        self.card_type_combo.addItems(["Generic", "JCOP", "Other"])
        grid.addWidget(self.card_type_combo, 0, 3)

        self.refresh_btn = QPushButton("REFRESH")
        self.refresh_btn.clicked.connect(self._refresh_readers)
        grid.addWidget(self.refresh_btn, 0, 4)

        # Row 1: read button
        self.read_btn = QPushButton("READ ATR")
        self.read_btn.clicked.connect(self._read_atr)
        grid.addWidget(self.read_btn, 1, 0, 1, 5, alignment=Qt.AlignLeft)

        # Row 2: ATR display
        grid.addWidget(QLabel("ATR"), 2, 0)
        self.atr_text = QTextEdit()
        self.atr_text.setReadOnly(True)
        self.atr_text.setFixedHeight(70)
        grid.addWidget(self.atr_text, 2, 1, 1, 4)

        # Row 3+: parse tree
        self.parse_tree = QTreeWidget()
        self.parse_tree.setHeaderLabels(["Field", "Value"])
        grid.addWidget(self.parse_tree, 3, 0, 1, 5)

        return g

    def _build_customize_group(self) -> QGroupBox:
        g = QGroupBox("Customize ATR")
        v = QVBoxLayout(g)

        choose_row = QHBoxLayout()
        choose_row.addWidget(QLabel("Choose ATR"))
        self.db_select = QComboBox()
        self.db_select.addItem("Select ATR")
        for atr_hex, desc in KNOWN_ATRS.items():
            self.db_select.addItem(f"{desc}", atr_hex)
        choose_row.addWidget(self.db_select)
        v.addLayout(choose_row)

        radio_row = QHBoxLayout()
        self.default_radio = QRadioButton("Default ATR")
        self.default_radio.setChecked(True)
        self.custom_radio = QRadioButton("Custom ATR")
        radio_row.addWidget(self.default_radio)
        radio_row.addWidget(self.custom_radio)
        v.addLayout(radio_row)

        custom_row = QHBoxLayout()
        custom_row.addWidget(QLabel("Custom hex"))
        self.custom_hex = QLineEdit()
        self.custom_hex.setPlaceholderText("e.g. 3B 00")
        custom_row.addWidget(self.custom_hex)
        v.addLayout(custom_row)

        # Script loader
        script_row = QHBoxLayout()
        script_row.addWidget(QLabel("APDU Script"))
        self.script_path = QLineEdit()
        self.script_path.setPlaceholderText("Load a .apdu script to program the card")
        load_btn = QPushButton("Load...")
        load_btn.clicked.connect(self._load_script)
        script_row.addWidget(self.script_path)
        script_row.addWidget(load_btn)
        v.addLayout(script_row)

        self.script_preview = QTextEdit()
        self.script_preview.setReadOnly(True)
        self.script_preview.setPlaceholderText("Script preview")
        self.script_preview.setFixedHeight(120)
        v.addWidget(self.script_preview)

        # Controls
        control_row = QHBoxLayout()
        self.copy_btn = QPushButton("COPY ATR")
        self.copy_btn.clicked.connect(self._copy_atr)
        self.send_btn = QPushButton("SEND TO CARD")
        self.send_btn.clicked.connect(self._send_to_card)
        control_row.addWidget(self.copy_btn)
        control_row.addWidget(self.send_btn)
        v.addLayout(control_row)

        # Ready indicators
        self.reader_ready_label = QLabel("READER: UNKNOWN")
        self.card_ready_label = QLabel("INSERTED CARD: UNKNOWN")
        v.addWidget(self.reader_ready_label)
        v.addWidget(self.card_ready_label)

        return g

    # ----- Actions -----
    def _refresh_readers(self) -> None:
        self.reader_combo.clear()
        readers = list_readers()
        if readers:
            self.reader_combo.addItems(readers)
            self.reader_ready_label.setText("READER: READY")
        else:
            self.reader_combo.addItem("No readers found")
            self.reader_ready_label.setText("READER: NOT FOUND")
        self.status.showMessage("Readers refreshed", 3000)

    def _read_atr(self) -> None:
        try:
            reader_index = self.reader_combo.currentIndex()
            reader_name, atr_bytes = connect_and_get_atr(reader_index)
        except Exception as exc:
            QMessageBox.critical(self, "Read ATR", f"Failed to read ATR: {exc}")
            self.card_ready_label.setText("INSERTED CARD: NOT READY")
            return

        self.card_ready_label.setText("INSERTED CARD: READY")
        atr_hex = to_hex(atr_bytes)
        self.atr_text.setPlainText(atr_hex)
        self.status.showMessage(f"Connected to {reader_name}", 5000)

        # Update parse tree
        self._populate_parse_tree(atr_bytes)

        # Keep selection in chooser in sync
        self.db_select.setCurrentIndex(0)
        self.default_radio.setChecked(True)

    def _populate_parse_tree(self, atr_bytes: bytes) -> None:
        self.parse_tree.clear()
        res = parse_atr(atr_bytes)
        items = []
        items.append(QTreeWidgetItem(["TS", f"0x{res.ts:02X}"]))
        items.append(QTreeWidgetItem(["T0", f"0x{res.t0:02X}"]))
        items.append(QTreeWidgetItem(["Historical bytes (K)", str(res.k)]))
        items.append(QTreeWidgetItem(["Protocols", ", ".join([f"T={p}" for p in res.protocols])]))
        items.append(QTreeWidgetItem(["Historical", res.historical_bytes.hex(" ").upper()]))
        if res.tck is not None:
            items.append(QTreeWidgetItem(["TCK", f"0x{res.tck:02X} (computed 0x{res.computed_tck:02X}) -> {'OK' if res.tck_valid else 'BAD'}"]))
        for group in res.interface_bytes:
            for key, val in group.items():
                items.append(QTreeWidgetItem([key, f"0x{val:02X}"]))
        self.parse_tree.addTopLevelItems(items)
        self.parse_tree.expandAll()

    def _copy_atr(self) -> None:
        atr_hex = self._current_output_atr_hex()
        if atr_hex is None:
            QMessageBox.information(self, "Copy ATR", "No ATR available to copy.")
            return
        QApplication.clipboard().setText(atr_hex, QClipboard.Clipboard)
        self.status.showMessage("ATR copied to clipboard", 3000)

    def _send_to_card(self) -> None:
        atr_hex = self._current_output_atr_hex()
        if not atr_hex:
            QMessageBox.warning(self, "Send to Card", "No ATR selected.")
            return
        try:
            atr_bytes = bytes.fromhex(atr_hex.replace(" ", "").replace("-", ""))
        except Exception:
            QMessageBox.warning(self, "Send to Card", "Selected ATR is not valid hex.")
            return

        script_text = self.script_preview.toPlainText().strip()
        if not script_text:
            # Try to auto-load the bundled example
            try:
                from importlib.resources import files

                example_path = files("atr_utility").joinpath("example_script.apdu")
                script_text = example_path.read_text(encoding="utf-8")
                display_path = str(example_path)
            except Exception:
                # Fallback for PyInstaller one-file/runtime
                try:
                    import os
                    from pathlib import Path
                    base_dir = getattr(sys, "_MEIPASS", Path(__file__).resolve().parent)  # type: ignore[attr-defined]
                    fallback = Path(base_dir) / "atr_utility" / "example_script.apdu"
                    script_text = fallback.read_text(encoding="utf-8")
                    display_path = str(fallback)
                except Exception:
                    QMessageBox.information(
                        self,
                        "Send to Card",
                        "Load an APDU script first (see README for variables).",
                    )
                    return
            self.script_path.setText(display_path)
            self.script_preview.setPlainText(script_text)

        try:
            apdus = parse_apdu_script(script_text, atr_bytes)
            if not apdus:
                QMessageBox.information(self, "Send to Card", "Script contains no APDUs to send.")
                return
            reader_index = self.reader_combo.currentIndex()
            results = send_apdus(reader_index, apdus)
        except Exception as exc:
            QMessageBox.critical(self, "Send to Card", f"Failed: {exc}")
            return

        # Summarize results
        ok_count = sum(1 for r in results if (r.sw1, r.sw2) == (0x90, 0x00))
        msg = QMessageBox(self)
        msg.setIcon(QMessageBox.Information)
        msg.setWindowTitle("Send to Card")
        msg.setText(f"Sent {len(results)} APDUs, {ok_count} returned 90 00.")
        details_lines = []
        for r in results:
            apdu_hex = r.apdu.hex(" ").upper()
            data_hex = r.data.hex(" ").upper()
            details_lines.append(f"> {apdu_hex}\n< {r.sw1:02X} {r.sw2:02X} {('['+data_hex+']') if data_hex else ''}\n")
        msg.setDetailedText("\n".join(details_lines))
        msg.exec()
        self.status.showMessage("APDU script sent", 4000)

    def _current_output_atr_hex(self) -> Optional[str]:
        # Determine which ATR is selected in the right panel
        if self.default_radio.isChecked():
            text = self.atr_text.toPlainText().strip()
            return text or None
        # Custom
        if self.custom_radio.isChecked():
            hex_text = self.custom_hex.text().strip()
            if hex_text:
                try:
                    build_simple_atr(historical_bytes="")  # sanity import use
                    # Validate hex by attempting parse
                    _ = bytes.fromhex(hex_text.replace(" ", "").replace("-", ""))
                except Exception:
                    QMessageBox.warning(self, "Invalid hex", "Please enter a valid hex string.")
                    return None
                return hex_text.upper()
        # DB selection
        idx = self.db_select.currentIndex()
        if idx > 0:
            return self.db_select.currentData()  # type: ignore[return-value]
        return None

    def _load_script(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(self, "Load APDU Script", "", "APDU Scripts (*.apdu *.txt);;All Files (*)")
        if not file_path:
            return
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
        except Exception as exc:
            QMessageBox.critical(self, "Load Script", f"Failed to read file: {exc}")
            return
        self.script_path.setText(file_path)
        self.script_preview.setPlainText(content)


def main() -> None:
    app = QApplication(sys.argv)

    # Basic dark palette for resemblance with screenshot
    app.setStyle("Fusion")

    w = ATRStudioWindow()
    w.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
