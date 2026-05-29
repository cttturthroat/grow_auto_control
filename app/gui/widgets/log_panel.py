from __future__ import annotations

from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


class LogPanel(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 4, 0, 0)
        layout.setSpacing(4)

        header = QHBoxLayout()
        title = QLabel('Application Logs')
        title.setStyleSheet('font-weight: bold;')
        header.addWidget(title)
        header.addStretch()
        clear_btn = QPushButton('Clear')
        clear_btn.setFixedWidth(60)
        clear_btn.clicked.connect(self._on_clear)  # type: ignore[attr-defined]
        header.addWidget(clear_btn)
        layout.addLayout(header)

        self._text = QPlainTextEdit()
        self._text.setReadOnly(True)
        self._text.setMaximumBlockCount(2000)
        self._text.setStyleSheet(
            'font-family: Consolas, "Courier New", monospace; font-size: 11px;'
        )
        layout.addWidget(self._text)

    def append_message(self, text: str) -> None:
        self._text.appendPlainText(text.rstrip('\n'))

    def _on_clear(self, _checked: bool = False) -> None:
        self._text.clear()
