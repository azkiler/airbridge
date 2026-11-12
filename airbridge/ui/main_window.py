"""Ventana principal de AirBridge.

Barra superior propia, menu lateral contraible, paginas con transicion
animada, avisos deslizantes y anclado real de la ventana en Windows 11.
"""
from __future__ import annotations

import os
import subprocess
import sys

from PySide6.QtCore import QEasingCurve, QPoint, QPropertyAnimation, Qt, QTimer, QUrl
from PySide6.QtGui import QDesktopServices, QFont, QGuiApplication
from PySide6.QtWidgets import (
    QApplication, QFrame, QHBoxLayout, QLabel, QMainWindow, QVBoxLayout, QWidget,
)

from .. import __version__
from ..config import MODE_MUSIC, MODE_SCREEN, Config
from ..core import netinfo
from ..core.engine import READY, STREAMING, EngineController, STATE_LABEL
from ..paths import logs_dir
from ..presets import quality_summary
from ..win import autostart, firewall, winapi
from . import theme as T
from . import widgets as T_W
from .pages.gaming import GamingPage
from .pages.help import HelpPage
from .pages.home import HomePage
from .pages.music import MusicPage
from .pages.screen import ScreenPage
from .pages.settings import SettingsPage
from .widgets import (
    ActionButton, AnimatedStack, Chip, ToastHost, label, row,
)

SIDEBAR_W = 224
TITLE_H = 52
STATUS_H = 34
EDGE = 7


class MainWindow(QMainWindow):
    def __init__(self, cfg: Config, engine: EngineController, demo: bool = False) -> None:
        super().__init__()
        self.cfg = cfg
        self.engine = engine
        self.demo = demo
        self._maximized = False
        self._normal_geom = None

        self.setWindowTitle("AirBridge - Receptor AirPlay")
        self.setMinimumSize(960, 640)
        flags = Qt.Window | Qt.FramelessWindowHint
        if cfg.always_on_top:
            flags |= Qt.WindowStaysOnTopHint
        self.setWindowFlags(flags)
        self.setMouseTracking(True)

        self._build_ui()
        self._wire()
        self.apply_animation_policy()

        geo = cfg.window_geometry
        if geo and geo[2] >= 900 and geo[3] >= 600:
            self.setGeometry(*geo)
        else:
            self.resize(1200, 780)
            self._center()

        self._topmost_timer = QTimer(self)
        self._topmost_timer.setInterval(1200)
        self._topmost_timer.timeout.connect(self._enforce_topmost)
        self._topmost_timer.start()

        QTimer.singleShot(120, self._post_show)

    # ------------------------------------------------------------------
    def _build_ui(self) -> None:
        root = QFrame()
        root.setObjectName("root")
        root.setStyleSheet(f"#root {{ background: {T.BG}; }}")
        self.setCentralWidget(root)
        outer = QVBoxLayout(root)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # --- Barra superior ---------------------------------------------
        bar = QWidget()
        bar.setFixedHeight(TITLE_H)
        bar.setStyleSheet(f"background: {T.BG_SOFT}; border-bottom: 1px solid {T.LINE_SOFT};")
        bl = QHBoxLayout(bar)
        bl.setContentsMargins(18, 0, 12, 0)
        bl.setSpacing(12)

        word = QLabel("AIRBRIDGE")
        f = QFont(word.font()); f.setBold(True); f.setPointSizeF(12.5); f.setLetterSpacing(QFont.AbsoluteSpacing, 2.4)
        word.setFont(f)
        word.setStyleSheet(f"color: {T.TEXT};")
        sub = label("RECEPTOR AIRPLAY", "kicker")
        self.header_chip = Chip("INICIANDO", "neutral")

        self.menu_btn = ActionButton("Menu", "ghost", small=True)
        self.menu_btn.setFixedWidth(78)
        self.menu_btn.clicked.connect(lambda: self.set_sidebar_collapsed(not self.cfg.sidebar_collapsed))
        self.pin_btn = ActionButton("Anclado", "violet" if self.cfg.always_on_top else "neutral", small=True)
        self.pin_btn.setFixedWidth(112)
        self.pin_btn.clicked.connect(self._toggle_pin_window)
        self.min_btn = ActionButton("Minimizar", "ghost", small=True)
        self.min_btn.setFixedWidth(96)
        self.min_btn.clicked.connect(self._minimize)
        self.max_btn = ActionButton("Maximizar", "ghost", small=True)
        self.max_btn.setFixedWidth(96)
        self.max_btn.clicked.connect(self.toggle_maximize)
        self.close_btn = ActionButton("Cerrar", "ghost", small=True)
        self.close_btn.setFixedWidth(76)
        self.close_btn.clicked.connect(self.close)

        bl.addWidget(word)
        bl.addWidget(sub)
        bl.addSpacing(14)
        bl.addWidget(self.header_chip)
        bl.addStretch(1)
        for b in (self.menu_btn, self.pin_btn, self.min_btn, self.max_btn, self.close_btn):
            bl.addWidget(b)
        self.title_bar = bar
        outer.addWidget(bar)

        # --- Cuerpo -------------------------------------------------------
        body = QWidget()
        body.setStyleSheet(f"background: {T.BG};")
        hl = QHBoxLayout(body)
        hl.setContentsMargins(0, 0, 0, 0)
        hl.setSpacing(0)

        self.sidebar = QWidget()
        self.sidebar.setStyleSheet(f"background: {T.BG_SOFT}; border-right: 1px solid {T.LINE_SOFT};")
        self.sidebar.setFixedWidth(0 if self.cfg.sidebar_collapsed else SIDEBAR_W)
        sl = QVBoxLayout(self.sidebar)
        sl.setContentsMargins(12, 18, 12, 14)
        sl.setSpacing(4)
        sl.addWidget(label("NAVEGACION", "kicker"))
        sl.addSpacing(8)

        self.stack = AnimatedStack()
        self.pages: dict[str, object] = {}
        self.nav_buttons: dict[str, object] = {}
        for cls in (HomePage, ScreenPage, MusicPage, GamingPage, SettingsPage, HelpPage):
            page = cls(self)
            self.pages[page.key] = page
            self.stack.addWidget(page)
            nav = T_W.NavButton(page.title)
            nav.clicked.connect(lambda _=False, k=page.key: self.goto(k))
            self.nav_buttons[page.key] = nav
            sl.addWidget(nav)
        sl.addStretch(1)
        self.side_info = label("", "mute", wrap=True)
        sl.addWidget(self.side_info)
        sl.addWidget(label(f"v{__version__}", "mute"))

        hl.addWidget(self.sidebar)
        hl.addWidget(self.stack, 1)
        outer.addWidget(body, 1)

        # --- Barra de estado ------------------------------------------------
        status = QWidget()
        status.setFixedHeight(STATUS_H)
        status.setStyleSheet(f"background: {T.BG_SOFT}; border-top: 1px solid {T.LINE_SOFT};")
        stl = QHBoxLayout(status)
        stl.setContentsMargins(18, 0, 14, 0)
        stl.setSpacing(14)
        self.status_left = label("", "mute")
        self.status_right = label("", "mute")
        self.log_btn = ActionButton("Registro", "ghost", small=True)
        self.log_btn.setFixedWidth(90)
        self.log_btn.clicked.connect(lambda: self.goto("help"))
        stl.addWidget(self.status_left)
        stl.addStretch(1)
        stl.addWidget(self.status_right)
        stl.addWidget(self.log_btn)
        outer.addWidget(status)

        self.toasts = ToastHost(root)
        self.toasts.raise_()

        self._sidebar_anim = QPropertyAnimation(self.sidebar, b"maximumWidth", self)
        self._sidebar_anim.setDuration(T_W.dur(260))
        self._sidebar_anim.setEasingCurve(QEasingCurve.InOutCubic)
        self._sidebar_anim.valueChanged.connect(lambda v: self.sidebar.setMinimumWidth(v))

        self.goto("home")
        self.nav_buttons["home"].setChecked(True)

    def _wire(self) -> None:
        e = self.engine
        e.state_changed.connect(self._on_state)
        e.device_changed.connect(lambda _d: self.refresh_pages())
        e.session_changed.connect(self._on_session)
        e.stats_changed.connect(self._on_stats)
        e.notice.connect(self.toast)
        e.log_line.connect(self._on_log)
        e.video_window_found.connect(self._on_video_window)
        e.video_window_lost.connect(self._on_video_lost)

    # ------------------------------------------------------------------
    def _post_show(self) -> None:
        winapi.set_dark_frame(winapi.hwnd_of(self))
        self.apply_topmost()
        self.apply_power_policy()
        if self.cfg.autostart and winapi.IS_WINDOWS and not autostart.is_enabled():
            autostart.enable()
        if self.cfg.start_engine_on_launch:
            self.engine.start()
        self.refresh_status()
        if self.cfg.first_run:
            self.cfg.first_run = False
            self.save_config()
            if self.engine.install is None:
                self.toast("Descarga el motor AirPlay para empezar (boton naranja en Inicio)", "info")
            else:
                self.toast("Listo: en el iPhone elegi 'Duplicar pantalla' y este receptor", "ok")

    def _center(self) -> None:
        scr = QGuiApplication.primaryScreen().availableGeometry()
        self.move(scr.center() - self.rect().center())

    # --- navegacion -------------------------------------------------------
    def goto(self, key: str) -> None:
        if key not in self.pages:
            return
        current = self.stack.currentWidget()
        if current is not None and hasattr(current, "on_hide"):
            current.on_hide()
        page = self.pages[key]
        self.stack.goto(self.stack.indexOf(page))
        for k, b in self.nav_buttons.items():
            b.setChecked(k == key)
        if hasattr(page, "on_show"):
            page.on_show()

    def set_sidebar_collapsed(self, collapsed: bool) -> None:
        self.cfg.sidebar_collapsed = collapsed
        self.save_config()
        target = 0 if collapsed else SIDEBAR_W
        self._sidebar_anim.stop()
        if not T_W.ANIM:
            self.sidebar.setMaximumWidth(target)
            self.sidebar.setMinimumWidth(target)
            return
        self._sidebar_anim.setDuration(T_W.dur(260))
        self._sidebar_anim.setStartValue(self.sidebar.width())
        self._sidebar_anim.setEndValue(target)
        self._sidebar_anim.start()

    # --- acciones ---------------------------------------------------------
    def toggle_engine(self) -> None:
        if self.engine.state in (READY, STREAMING, "starting"):
            self.engine.stop()
            self.toast("Receptor detenido", "info")
        else:
            self.engine.start()
        self.refresh_pages()

    def set_mode(self, mode: str) -> None:
        if mode == self.cfg.mode:
            return
        self.cfg.mode = mode
        self.save_and_apply(force=True)
        self.pages["music"].refresh()
        self.pages["screen"].refresh()
        if mode == MODE_MUSIC:
            self.toast("Modo Musica: solo audio, sin video", "ok")
            self.goto("music")
        else:
            self.toast("Modo Pantalla: video y audio", "ok")
            self.goto("screen")

    def save_config(self) -> None:
        self.cfg.window_geometry = [self.x(), self.y(), self.width(), self.height()]
        self.cfg.save()

    def save_and_apply(self, force: bool = False) -> None:
        self.save_config()
        self.engine.apply_config(self.cfg, force=force)
        self.refresh_pages()
        self.refresh_status()

    def apply_topmost(self) -> None:
        on = self.cfg.always_on_top
        self.setWindowFlag(Qt.WindowStaysOnTopHint, on)
        self.show()  # Qt requiere re-show al cambiar flags
        winapi.set_topmost(winapi.hwnd_of(self), on)
        self.pin_btn.accent = "violet" if on else "neutral"
        self.pin_btn.setText("Anclado" if on else "Anclar")
        self.pin_btn.update()
        self.pages["screen"].vw.keep_on_top(self.cfg.pin_video_window)

    def _toggle_pin_window(self) -> None:
        self.cfg.always_on_top = not self.cfg.always_on_top
        self.save_config()
        self.apply_topmost()
        self.toast(
            "Ventana anclada: queda arriba de todo" if self.cfg.always_on_top else "Ventana libre",
            "info",
        )

    def _enforce_topmost(self) -> None:
        if not winapi.IS_WINDOWS:
            return
        if self.cfg.always_on_top and not self.isMinimized():
            hwnd = winapi.hwnd_of(self)
            if not winapi.is_topmost(hwnd):
                winapi.set_topmost(hwnd, True)
        scr = self.pages["screen"]
        if self.cfg.pin_video_window and scr.vw.hwnd and scr.vw.floating:
            scr.vw.keep_on_top(True)

    def apply_power_policy(self) -> None:
        if self.cfg.prevent_sleep and (self.engine.streaming or self.cfg.always_on_top):
            winapi.keep_awake(True, True)
        else:
            winapi.allow_sleep()

    def apply_animation_policy(self) -> None:
        T_W.ANIM = bool(self.cfg.animations)

    def setup_firewall(self) -> None:
        inst = self.engine.install
        exe = inst.exe if inst else None
        self.toast("Acepta el aviso de administrador para abrir los puertos", "info")
        ok = firewall.install_rules(exe, self.cfg.tcp_port)
        self.toast("Firewall configurado" if ok else "No se pudieron aplicar las reglas", "ok" if ok else "warn")
        self.pages["settings"].refresh()

    def copy_diagnostics(self) -> None:
        text = self.engine.diagnostics() + "\n" + self._net_diagnostics()
        QGuiApplication.clipboard().setText(text)
        path = self.engine.save_log_snapshot()
        self.toast(f"Diagnostico copiado ({path.name})", "ok")

    def _net_diagnostics(self) -> str:
        wifi = netinfo.wifi_info()
        return (
            f"IP: {netinfo.local_ip()}\n"
            f"Wi-Fi: {wifi}\n"
            f"Bonjour: {netinfo.bonjour_service_running()}\n"
            f"Firewall: {firewall.rules_present()}\n"
            f"Calidad: {quality_summary(self.cfg)}"
        )

    def open_url(self, url: str) -> None:
        QDesktopServices.openUrl(QUrl(url))

    def open_path(self, path) -> None:
        path = str(path)
        if sys.platform.startswith("win"):
            os.startfile(path)  # type: ignore[attr-defined]  # noqa: S606
        elif sys.platform == "darwin":
            subprocess.Popen(["open", path])
        else:
            subprocess.Popen(["xdg-open", path])

    def restart_app(self) -> None:
        self.engine.stop()
        self.save_config()
        QApplication.quit()
        if getattr(sys, "frozen", False):
            subprocess.Popen([sys.executable])
        else:
            subprocess.Popen([sys.executable, *sys.argv])

    def toast(self, text: str, level: str = "info") -> None:
        self.toasts.push(text, level)

    # --- ventana ----------------------------------------------------------
    def _minimize(self) -> None:
        if self.cfg.always_on_top:
            self.toast("La ventana esta anclada. Toca 'Anclado' para poder minimizarla.", "info")
            return
        self.showMinimized()

    def toggle_maximize(self) -> None:
        if self._maximized:
            self.showNormal()
            if self._normal_geom:
                self.setGeometry(self._normal_geom)
            self._maximized = False
            self.max_btn.setText("Maximizar")
        else:
            self._normal_geom = self.geometry()
            self.showMaximized()
            self._maximized = True
            self.max_btn.setText("Restaurar")

    def toggle_fullscreen_window(self) -> None:
        if self.isFullScreen():
            self.showNormal()
        else:
            self.showFullScreen()

    def _edge_at(self, pos: QPoint):
        r = self.rect()
        edges = Qt.Edges()
        if pos.x() <= EDGE:
            edges |= Qt.LeftEdge
        if pos.x() >= r.width() - EDGE:
            edges |= Qt.RightEdge
        if pos.y() <= EDGE:
            edges |= Qt.TopEdge
        if pos.y() >= r.height() - EDGE:
            edges |= Qt.BottomEdge
        return edges

    def mousePressEvent(self, e) -> None:  # noqa: N802
        if e.button() == Qt.LeftButton:
            if self.title_bar.geometry().contains(e.position().toPoint()):
                handle = self.windowHandle()
                if handle is not None:
                    handle.startSystemMove()
                    return
            edges = self._edge_at(e.position().toPoint())
            if edges and not self._maximized:
                handle = self.windowHandle()
                if handle is not None:
                    handle.startSystemResize(edges)
                    return
        super().mousePressEvent(e)

    def mouseMoveEvent(self, e) -> None:  # noqa: N802
        pos = e.position().toPoint()
        edges = self._edge_at(pos)
        if edges in (Qt.LeftEdge, Qt.RightEdge):
            self.setCursor(Qt.SizeHorCursor)
        elif edges in (Qt.TopEdge, Qt.BottomEdge):
            self.setCursor(Qt.SizeVerCursor)
        elif edges in (Qt.TopEdge | Qt.LeftEdge, Qt.BottomEdge | Qt.RightEdge):
            self.setCursor(Qt.SizeFDiagCursor)
        elif edges in (Qt.TopEdge | Qt.RightEdge, Qt.BottomEdge | Qt.LeftEdge):
            self.setCursor(Qt.SizeBDiagCursor)
        else:
            self.unsetCursor()
        super().mouseMoveEvent(e)

    def mouseDoubleClickEvent(self, e) -> None:  # noqa: N802
        if self.title_bar.geometry().contains(e.position().toPoint()):
            self.toggle_maximize()
        super().mouseDoubleClickEvent(e)

    def resizeEvent(self, e) -> None:  # noqa: N802
        super().resizeEvent(e)
        if hasattr(self, "toasts"):
            self.toasts.setGeometry(self.centralWidget().rect())
            self.toasts.raise_()

    def closeEvent(self, e) -> None:  # noqa: N802
        self.save_config()
        try:
            self.pages["screen"].vw.reset()
        except Exception:  # noqa: BLE001
            pass
        self.engine.stop()
        winapi.allow_sleep()
        super().closeEvent(e)

    # --- eventos del motor -------------------------------------------------
    def _on_state(self, state: str) -> None:
        self.header_chip.setText(STATE_LABEL.get(state, state).upper())
        tone = {"streaming": "live", "ready": "ok", "starting": "violet",
                "error": "err", "missing": "warn"}.get(state, "neutral")
        self.header_chip.set_tone(tone)
        self.refresh_pages()
        self.refresh_status()

    def _on_session(self, active: bool) -> None:
        self.apply_power_policy()
        self.refresh_pages()
        if active and self.cfg.mode == MODE_SCREEN:
            self.goto("screen")

    def _on_stats(self, s: dict) -> None:
        for page in self.pages.values():
            if hasattr(page, "update_stats"):
                page.update_stats(s)

    def _on_log(self, line: str) -> None:
        self.pages["help"].append_log(line)

    def _on_video_window(self, hwnd: int) -> None:
        self.pages["screen"].set_video_hwnd(hwnd)
        if self.cfg.pin_video_window:
            self.pages["screen"].vw.keep_on_top(True)

    def _on_video_lost(self) -> None:
        self.pages["screen"].clear_video()

    def refresh_pages(self) -> None:
        for page in self.pages.values():
            if hasattr(page, "refresh"):
                page.refresh()

    def refresh_status(self) -> None:
        ip = netinfo.local_ip()
        mode = "Musica (solo audio)" if self.cfg.mode == MODE_MUSIC else "Pantalla + audio"
        self.status_left.setText(f"Wi-Fi {ip}  -  puerto {self.cfg.tcp_port}  -  {mode}")
        inst = self.engine.install
        self.status_right.setText(
            f"Motor: {'UxPlay ' + (inst.version or '') if inst else 'no instalado'}  -  Bluetooth: apagado"
        )
        self.side_info.setText(quality_summary(self.cfg))
