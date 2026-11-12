"""Paleta y estilos de AirBridge.

Regla de color pedida: naranja y violeta se reservan para lo importante.
  * NARANJA  -> accion principal (iniciar, conectar, aplicar, pantalla completa)
  * VIOLETA  -> estado activo / seleccion / anclado / modo musica
  * NEUTROS  -> todo lo demas (navegacion, secundarios, texto)
El fondo es casi negro violeta para que ambos acentos tengan contraste AA.
"""
from __future__ import annotations

# --- Base -------------------------------------------------------------
BG = "#0A0810"
BG_SOFT = "#0F0C17"
SURFACE = "#15111F"
SURFACE_2 = "#1C1729"
SURFACE_3 = "#241E33"
LINE = "#2E2740"
LINE_SOFT = "#241E33"

TEXT = "#F5F2FC"
TEXT_DIM = "#B4ABC9"
TEXT_MUTE = "#7C7492"

# --- Acentos ----------------------------------------------------------
ORANGE = "#FF7A2F"
ORANGE_HOVER = "#FF9354"
ORANGE_PRESS = "#E8641C"
ORANGE_INK = "#1A0E04"          # texto sobre naranja

VIOLET = "#8B5CF6"
VIOLET_DEEP = "#6D28D9"         # fondo de boton violeta con texto blanco (AA)
VIOLET_HOVER = "#7C3AED"
VIOLET_SOFT = "#C4B5FD"

OK = "#3DDC97"
WARN = "#FFC857"
ERR = "#FF6B8A"

RADIUS = 12
RADIUS_SM = 9


def font_stack() -> str:
    return '"Segoe UI Variable Text", "Segoe UI", "Inter", "Noto Sans", "DejaVu Sans", sans-serif'


def contrast_ratio(a: str, b: str) -> float:
    """Ratio de contraste WCAG (para los tests de accesibilidad)."""
    def lum(h: str) -> float:
        h = h.lstrip("#")
        vals = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
        vals = [v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4 for v in vals]
        return 0.2126 * vals[0] + 0.7152 * vals[1] + 0.0722 * vals[2]
    l1, l2 = sorted((lum(a), lum(b)), reverse=True)
    return (l1 + 0.05) / (l2 + 0.05)


def qss(scale: float = 1.0) -> str:
    s = lambda v: f"{round(v * scale)}px"  # noqa: E731
    return f"""
* {{ outline: none; }}

QWidget {{
    background: transparent;
    color: {TEXT};
    font-family: {font_stack()};
    font-size: {s(14)};
}}

QMainWindow, #root {{ background: {BG}; }}

QLabel {{ background: transparent; }}
QLabel[role="h1"] {{ font-size: {s(26)}; font-weight: 700; letter-spacing: -0.4px; }}
QLabel[role="h2"] {{ font-size: {s(18)}; font-weight: 650; }}
QLabel[role="h3"] {{ font-size: {s(15)}; font-weight: 600; }}
QLabel[role="dim"] {{ color: {TEXT_DIM}; }}
QLabel[role="mute"] {{ color: {TEXT_MUTE}; font-size: {s(12.5)}; }}
QLabel[role="kicker"] {{ color: {TEXT_MUTE}; font-size: {s(11.5)}; font-weight: 700; letter-spacing: 1.6px; }}
QLabel[role="value"] {{ font-size: {s(24)}; font-weight: 700; }}
QLabel[role="accent"] {{ color: {VIOLET_SOFT}; font-weight: 600; }}
QLabel[role="warn"] {{ color: {WARN}; }}
QLabel[role="err"] {{ color: {ERR}; }}
QLabel[role="ok"] {{ color: {OK}; }}

QFrame[card="1"] {{
    background: {SURFACE};
    border: 1px solid {LINE_SOFT};
    border-radius: {RADIUS}px;
}}
QFrame[card="2"] {{
    background: {SURFACE_2};
    border: 1px solid {LINE};
    border-radius: {RADIUS}px;
}}
QFrame[sep="1"] {{ background: {LINE_SOFT}; max-height: 1px; border: none; }}

QPushButton {{
    background: {SURFACE_2};
    color: {TEXT};
    border: 1px solid {LINE};
    border-radius: {RADIUS_SM}px;
    padding: {s(9)} {s(16)};
    font-weight: 600;
    text-align: center;
}}
QPushButton:hover {{ background: {SURFACE_3}; border-color: #3A3150; }}
QPushButton:pressed {{ background: #1A1526; }}
QPushButton:disabled {{ color: {TEXT_MUTE}; background: #14111E; border-color: #221C31; }}

QPushButton[accent="ghost"] {{ background: transparent; border: 1px solid transparent; color: {TEXT_DIM}; }}
QPushButton[accent="ghost"]:hover {{ background: {SURFACE_2}; color: {TEXT}; }}

QLineEdit, QPlainTextEdit, QSpinBox {{
    background: {BG_SOFT};
    border: 1px solid {LINE};
    border-radius: {RADIUS_SM}px;
    padding: {s(9)} {s(12)};
    selection-background-color: {VIOLET_DEEP};
    color: {TEXT};
}}
QLineEdit:focus, QPlainTextEdit:focus, QSpinBox:focus {{ border-color: {VIOLET}; }}

QComboBox {{
    background: {BG_SOFT};
    border: 1px solid {LINE};
    border-radius: {RADIUS_SM}px;
    padding: {s(8)} {s(12)};
    min-height: {s(20)};
}}
QComboBox:hover {{ border-color: #3A3150; }}
QComboBox::drop-down {{ border: none; width: {s(22)}; }}
QComboBox::down-arrow {{ image: none; width: 0; height: 0; }}
QComboBox QAbstractItemView {{
    background: {SURFACE_2};
    border: 1px solid {LINE};
    border-radius: {RADIUS_SM}px;
    selection-background-color: {VIOLET_DEEP};
    selection-color: {TEXT};
    padding: {s(4)};
}}

QSlider::groove:horizontal {{ height: {s(6)}; background: {SURFACE_3}; border-radius: 3px; }}
QSlider::sub-page:horizontal {{ background: {VIOLET}; border-radius: 3px; }}
QSlider::handle:horizontal {{
    background: {TEXT}; width: {s(16)}; height: {s(16)};
    margin: {s(-6)} 0; border-radius: 8px;
}}
QSlider::handle:horizontal:hover {{ background: {VIOLET_SOFT}; }}

QScrollBar:vertical {{ background: transparent; width: {s(10)}; margin: 0; }}
QScrollBar::handle:vertical {{ background: #322A46; border-radius: 5px; min-height: {s(36)}; }}
QScrollBar::handle:vertical:hover {{ background: #453A60; }}
QScrollBar::add-line, QScrollBar::sub-line {{ height: 0; width: 0; }}
QScrollBar::add-page, QScrollBar::sub-page {{ background: transparent; }}
QScrollBar:horizontal {{ height: 0; }}

QScrollArea {{ border: none; background: transparent; }}
QToolTip {{
    background: {SURFACE_3}; color: {TEXT};
    border: 1px solid {LINE}; border-radius: 8px; padding: {s(6)} {s(9)};
}}
QPlainTextEdit#log {{
    font-family: "Cascadia Mono", "Consolas", "DejaVu Sans Mono", monospace;
    font-size: {s(12)};
    color: {TEXT_DIM};
    background: #0B0812;
}}
"""
