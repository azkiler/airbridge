#!/usr/bin/env python3
"""AirBridge - Receptor AirPlay para Windows 11.

Uso:
    python run.py                # app normal
    python run.py --demo         # recorre la interfaz sin motor ni iPhone
    python run.py --autostart    # lo usa el inicio automatico de Windows
    python run.py --no-engine    # abre la interfaz sin arrancar el receptor
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))


def main() -> int:
    parser = argparse.ArgumentParser(description="AirBridge - receptor AirPlay")
    parser.add_argument("--demo", action="store_true", help="modo demostracion (sin motor real)")
    parser.add_argument("--autostart", action="store_true", help="arranque automatico de Windows")
    parser.add_argument("--no-engine", action="store_true", help="no iniciar el receptor al abrir")
    args = parser.parse_args()

    # Escalado DPI correcto en Windows 11 (monitores mixtos 100%/150%/200%).
    os.environ.setdefault("QT_ENABLE_HIGHDPI_SCALING", "1")
    os.environ.setdefault("QT_QPA_PLATFORM", "windows" if sys.platform.startswith("win") else os.environ.get("QT_QPA_PLATFORM", ""))
    if not os.environ.get("QT_QPA_PLATFORM"):
        os.environ.pop("QT_QPA_PLATFORM", None)

    from PySide6.QtCore import Qt, QTimer
    from PySide6.QtGui import QIcon
    from PySide6.QtNetwork import QLocalServer, QLocalSocket
    from PySide6.QtWidgets import QApplication

    QApplication.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
    app = QApplication(sys.argv)
    app.setApplicationName("AirBridge")
    app.setOrganizationName("AirBridge")
    app.setApplicationVersion("1.0.0")

    # --- Una sola instancia -------------------------------------------
    key = "airbridge-single-instance"
    probe = QLocalSocket()
    probe.connectToServer(key)
    if probe.waitForConnected(300):
        probe.write(b"show")
        probe.flush()
        probe.waitForBytesWritten(300)
        return 0
    QLocalServer.removeServer(key)
    server = QLocalServer()
    server.listen(key)

    from airbridge.config import Config
    from airbridge.core.engine import EngineController
    from airbridge.ui import theme as T
    from airbridge.ui.main_window import MainWindow

    cfg = Config.load()
    if args.no_engine:
        cfg.start_engine_on_launch = False

    app.setStyleSheet(T.qss(cfg.ui_scale))
    app.setFont(_pick_font(app))

    engine = EngineController(cfg, demo=args.demo)
    win = MainWindow(cfg, engine, demo=args.demo)

    def on_new_connection() -> None:
        conn = server.nextPendingConnection()
        if conn is not None:
            conn.waitForReadyRead(200)
            conn.readAll()
            win.showNormal()
            win.raise_()
            win.activateWindow()
            conn.disconnectFromServer()

    server.newConnection.connect(on_new_connection)
    win.show()
    QTimer.singleShot(200, win.raise_)
    return app.exec()


def _pick_font(app):
    from PySide6.QtGui import QFont, QFontDatabase
    families = set(QFontDatabase.families())
    for name in ("Segoe UI Variable Text", "Segoe UI", "Inter", "Noto Sans", "DejaVu Sans"):
        if name in families:
            f = QFont(name, 10)
            f.setHintingPreference(QFont.PreferFullHinting)
            return f
    return app.font()


if __name__ == "__main__":
    raise SystemExit(main())
