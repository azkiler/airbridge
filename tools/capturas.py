#!/usr/bin/env python3
"""Genera capturas de la interfaz sin necesidad de Windows ni iPhone.

    python tools/capturas.py --out docs/capturas

Sirve para revisar el diseno y para la documentacion. Usa el modo demo.
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(ROOT / "docs" / "capturas"))
    args = ap.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    from PySide6.QtCore import QEventLoop, QTimer
    from PySide6.QtGui import QFont, QFontDatabase
    from PySide6.QtWidgets import QApplication

    from airbridge.config import Config
    from airbridge.core.engine import EngineController
    from airbridge.ui import theme as T
    from airbridge.ui.main_window import MainWindow

    app = QApplication(sys.argv)
    families = set(QFontDatabase.families())
    for name in ("Segoe UI Variable Text", "Segoe UI", "Inter", "Noto Sans", "DejaVu Sans"):
        if name in families:
            app.setFont(QFont(name, 10))
            break
    cfg = Config()
    cfg.first_run = False
    cfg.window_geometry = [0, 0, 1240, 820]
    app.setStyleSheet(T.qss(cfg.ui_scale))

    engine = EngineController(cfg, demo=True)
    win = MainWindow(cfg, engine, demo=True)
    win.resize(1240, 820)
    win.show()

    def spin(ms: int) -> None:
        loop = QEventLoop()
        QTimer.singleShot(ms, loop.quit)
        loop.exec()

    spin(5200)  # el modo demo conecta un iPhone simulado

    shots = [
        ("01-inicio", "home"),
        ("02-pantalla", "screen"),
        ("03-musica", "music"),
        ("04-gaming", "gaming"),
        ("05-ajustes", "settings"),
        ("06-ayuda", "help"),
    ]
    for name, key in shots:
        win.goto(key)
        spin(900)
        win.grab().save(str(out / f"{name}.png"))
        print("captura", name)

    # Menu lateral contraido + panel abierto
    win.goto("screen")
    spin(500)
    win.set_sidebar_collapsed(True)
    spin(700)
    win.grab().save(str(out / "07-menu-contraido.png"))
    win.set_sidebar_collapsed(False)
    spin(700)

    win.goto("home")
    spin(600)
    win.toast("iPhone de Alex conectado (demo)", "ok")
    spin(700)
    win.grab().save(str(out / "08-aviso.png"))
    print("listo:", out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
