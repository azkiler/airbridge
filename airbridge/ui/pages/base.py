"""Base comun de las paginas (scroll + refresco al entrar)."""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QScrollArea, QVBoxLayout, QWidget

from ..widgets import label


class Page(QScrollArea):
    key = ""
    title = ""

    def __init__(self, app, parent=None) -> None:
        super().__init__(parent)
        self.app = app
        self.setWidgetResizable(True)
        self.setFrameShape(QScrollArea.NoFrame)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.container = QWidget()
        self.lay = QVBoxLayout(self.container)
        self.lay.setContentsMargins(28, 24, 28, 28)
        self.lay.setSpacing(16)
        self.setWidget(self.container)
        self.build()
        self.lay.addStretch(1)

    def build(self) -> None:  # pragma: no cover - override
        raise NotImplementedError

    def on_show(self) -> None:
        """Se llama cada vez que la pagina entra en pantalla."""

    def on_hide(self) -> None:
        """Se llama al salir de la pagina."""

    def refresh(self) -> None:
        """Se llama cuando cambia el estado del motor."""

    def update_stats(self, s: dict) -> None:
        """Estadisticas periodicas del motor."""

    # helpers ----------------------------------------------------------
    def header(self, kicker: str, title: str, subtitle: str = "") -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(5)
        lay.addWidget(label(kicker.upper(), "kicker"))
        lay.addWidget(label(title, "h1"))
        if subtitle:
            lay.addWidget(label(subtitle, "dim", wrap=True))
        return lay.parentWidget()
