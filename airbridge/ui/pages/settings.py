"""Pagina Ajustes: comportamiento en Windows, motor, red y apariencia."""
from __future__ import annotations

import subprocess
import sys

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QHBoxLayout, QMessageBox, QVBoxLayout, QWidget

from ... import __version__
from ...core import provision
from ...paths import app_dir, data_dir, engine_dir, logs_dir
from ...win import autostart, firewall, winapi
from ..widgets import ActionButton, Chip, Collapsible, LabeledSlider, TextToggle, card, label, row
from .base import Page


class SettingsPage(Page):
    key = "settings"
    title = "Ajustes"

    def build(self) -> None:
        self.lay.addWidget(self.header(
            "Configuracion",
            "Ajustes",
            "Todo queda guardado en tu usuario y se aplica al instante.",
        ))

        # --- Comportamiento ------------------------------------------------
        beh = QWidget()
        bl = QVBoxLayout(beh)
        bl.setContentsMargins(0, 0, 0, 0)
        bl.setSpacing(12)
        self.t_autostart = self._toggle_row(
            bl, "Iniciar con Windows",
            "AirBridge arranca solo al prender la PC y queda visible, anunciando el receptor.",
            self.app.cfg.autostart, self._set_autostart)
        self.t_topmost = self._toggle_row(
            bl, "Siempre arriba de todo",
            "La ventana no se va a segundo plano aunque abras otro programa o cambies de escritorio.",
            self.app.cfg.always_on_top, self._set_topmost)
        self.t_pinvideo = self._toggle_row(
            bl, "Anclar tambien la ventana de video",
            "El video del iPhone queda fijo por encima de las demas ventanas.",
            self.app.cfg.pin_video_window, self._set_pinvideo)
        self.t_startengine = self._toggle_row(
            bl, "Encender el receptor al abrir la app",
            "Asi solo tenes que tocar 'Duplicar pantalla' en el iPhone, nada mas.",
            self.app.cfg.start_engine_on_launch, self._set_startengine)
        self.t_sleep = self._toggle_row(
            bl, "Evitar suspension y apagado de pantalla",
            "Mientras transmite, Windows no duerme la PC ni apaga el monitor.",
            self.app.cfg.prevent_sleep, self._set_sleep)
        self.t_embed = self._toggle_row(
            bl, "Incrustar el video dentro de AirBridge",
            "Si lo apagas, el video se muestra en una ventana aparte que igual queda anclada.",
            self.app.cfg.embed_video, self._set_embed)
        self.lay.addWidget(Collapsible("Inicio y comportamiento", beh, opened=True))

        # --- Apariencia -----------------------------------------------------
        app_box = QWidget()
        ab = QVBoxLayout(app_box)
        ab.setContentsMargins(0, 0, 0, 0)
        ab.setSpacing(12)
        self.t_anim = self._toggle_row(
            ab, "Animaciones de interfaz",
            "Transiciones entre pantallas, paneles que se abren y cierran, avisos deslizantes.",
            self.app.cfg.animations, self._set_anim)
        self.scale = LabeledSlider("Tamano de la interfaz", 85, 135, int(self.app.cfg.ui_scale * 100), "%")
        self.scale.valueChanged.connect(self._set_scale)
        ab.addWidget(self.scale)
        ab.addWidget(label("El cambio de tamano se aplica al reiniciar la app.", "mute"))
        self.t_sidebar = self._toggle_row(
            ab, "Menu lateral contraido",
            "Gana espacio para el video; se abre con el boton 'Menu' de la barra superior.",
            self.app.cfg.sidebar_collapsed, self._set_sidebar)
        self.lay.addWidget(Collapsible("Apariencia", app_box, opened=False))

        # --- Motor -----------------------------------------------------------
        eng = QWidget()
        el = QVBoxLayout(eng)
        el.setContentsMargins(0, 0, 0, 0)
        el.setSpacing(10)
        self.engine_path_label = label("-", "dim", wrap=True)
        self.engine_kind_chip = Chip("SIN MOTOR", "warn")
        el.addWidget(row(self.engine_kind_chip, "stretch"))
        el.addWidget(self.engine_path_label)
        el.addWidget(label(
            f"Motor AirPlay: UxPlay {provision.UXPLAY_VERSION} (GPLv3) - empaquetado "
            f"uxplay-windows {provision.ENGINE_VERSION}. AirBridge v{__version__} es la interfaz "
            "y el orquestador; el protocolo lo implementa el motor.", "mute", wrap=True))
        el.addWidget(row(
            self._btn("Buscar motor instalado", "neutral", self.find_engine),
            self._btn("Descargar o actualizar", "primary", self.download_engine),
            self._btn("Abrir carpeta del motor", "ghost", lambda: self.app.open_path(engine_dir())),
            "stretch",
        ))
        self.lay.addWidget(Collapsible("Motor AirPlay", eng, opened=False))

        # --- Red --------------------------------------------------------------
        net = QWidget()
        nl = QVBoxLayout(net)
        nl.setContentsMargins(0, 0, 0, 0)
        nl.setSpacing(10)
        nl.addWidget(label(
            "AirPlay necesita que Windows permita el trafico entrante del motor y de Bonjour "
            "(mDNS, UDP 5353). Esto abre un unico aviso de permisos de administrador.", "dim", wrap=True))
        self.fw_chip = Chip("FIREWALL SIN CONFIGURAR", "warn")
        nl.addWidget(row(self.fw_chip, "stretch"))
        nl.addWidget(row(
            self._btn("Configurar firewall", "primary", self.app.setup_firewall),
            self._btn("Quitar reglas de AirBridge", "neutral", self.remove_fw),
            "stretch",
        ))
        nl.addWidget(label(
            "Sin Bluetooth: AirBridge nunca activa el beacon BLE del motor. El descubrimiento "
            "es 100% por Wi-Fi (Bonjour/mDNS).", "mute", wrap=True))
        self.lay.addWidget(Collapsible("Red y descubrimiento", net, opened=False))

        # --- Datos -------------------------------------------------------------
        data = QWidget()
        dl = QVBoxLayout(data)
        dl.setContentsMargins(0, 0, 0, 0)
        dl.setSpacing(10)
        dl.addWidget(label(f"Configuracion: {data_dir()}", "mute", wrap=True))
        dl.addWidget(label(f"Motor y registros: {logs_dir().parent}", "mute", wrap=True))
        dl.addWidget(row(
            self._btn("Abrir carpeta de datos", "neutral", lambda: self.app.open_path(data_dir())),
            self._btn("Abrir registros", "neutral", lambda: self.app.open_path(logs_dir())),
            self._btn("Restablecer todo", "danger", self.reset_all),
            "stretch",
        ))
        self.lay.addWidget(Collapsible("Datos y restablecimiento", data, opened=False))

        self.refresh()

    # ------------------------------------------------------------------
    def _btn(self, text, accent, slot) -> ActionButton:
        b = ActionButton(text, accent)
        b.clicked.connect(slot)
        return b

    def _toggle_row(self, layout, title: str, desc: str, value: bool, slot) -> TextToggle:
        w = QWidget()
        lay = QHBoxLayout(w)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(14)
        texts = QVBoxLayout()
        texts.setSpacing(2)
        texts.addWidget(label(title, "h3"))
        texts.addWidget(label(desc, "mute", wrap=True))
        t = TextToggle(value)
        t.changed.connect(slot)
        lay.addLayout(texts, 1)
        lay.addWidget(t, 0, Qt.AlignTop)
        layout.addWidget(w)
        return t

    # --- setters ---------------------------------------------------------
    def _set_autostart(self, on: bool) -> None:
        self.app.cfg.autostart = on
        ok = autostart.apply(on)
        self.app.save_config()
        if not ok and winapi.IS_WINDOWS:
            self.app.toast("No se pudo escribir el inicio automatico", "warn")
        else:
            self.app.toast("Inicio automatico activado" if on else "Inicio automatico desactivado", "info")

    def _set_topmost(self, on: bool) -> None:
        self.app.cfg.always_on_top = on
        self.app.save_config()
        self.app.apply_topmost()

    def _set_pinvideo(self, on: bool) -> None:
        self.app.cfg.pin_video_window = on
        self.app.save_config()
        self.app.pages["screen"].pin_toggle.set_on(on)
        self.app.pages["screen"].vw.keep_on_top(on)

    def _set_startengine(self, on: bool) -> None:
        self.app.cfg.start_engine_on_launch = on
        self.app.save_config()

    def _set_sleep(self, on: bool) -> None:
        self.app.cfg.prevent_sleep = on
        self.app.save_config()
        self.app.apply_power_policy()
        self.app.pages["gaming"].sleep_toggle.set_on(on)

    def _set_embed(self, on: bool) -> None:
        self.app.cfg.embed_video = on
        self.app.save_config()
        self.app.toast("Se aplica en la proxima conexion", "info")

    def _set_anim(self, on: bool) -> None:
        self.app.cfg.animations = on
        self.app.save_config()
        self.app.apply_animation_policy()

    def _set_scale(self, v: int) -> None:
        self.app.cfg.ui_scale = v / 100.0
        self.app.save_config()

    def _set_sidebar(self, on: bool) -> None:
        self.app.cfg.sidebar_collapsed = on
        self.app.save_config()
        self.app.set_sidebar_collapsed(on)

    # --- motor / red ------------------------------------------------------
    def find_engine(self) -> None:
        found = provision.find_engine("")
        if found:
            self.app.cfg.engine_path = str(found.exe)
            self.app.engine.refresh_install()
            self.app.save_config()
            self.refresh()
            self.app.toast("Motor encontrado", "ok")
        else:
            self.app.toast("No se encontro ningun motor instalado", "warn")

    def download_engine(self) -> None:
        self.app.goto("home")
        self.app.pages["home"].start_download()

    def remove_fw(self) -> None:
        firewall.remove_rules()
        self.refresh()
        self.app.toast("Reglas de AirBridge eliminadas", "info")

    def reset_all(self) -> None:
        box = QMessageBox(self)
        box.setWindowTitle("Restablecer AirBridge")
        box.setText("Se vuelven todos los ajustes a sus valores de fabrica.")
        box.setInformativeText("El motor descargado no se borra. La app se reinicia sola.")
        box.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        box.button(QMessageBox.Yes).setText("Restablecer")
        box.button(QMessageBox.No).setText("Cancelar")
        if box.exec() != QMessageBox.Yes:
            return
        from ...config import Config
        fresh = Config()
        fresh.engine_path = self.app.cfg.engine_path
        fresh.device_mac = self.app.cfg.device_mac
        fresh.first_run = False
        fresh.save()
        self.app.restart_app()

    # ------------------------------------------------------------------
    def on_show(self) -> None:
        self.refresh()

    def refresh(self) -> None:
        inst = self.app.engine.install
        if inst:
            self.engine_kind_chip.setText(
                "UXPLAY CLI" if inst.kind == "uxplay-cli" else "UXPLAY WINDOWS"
            )
            self.engine_kind_chip.set_tone("ok")
            self.engine_path_label.setText(str(inst.exe))
        else:
            self.engine_kind_chip.setText("SIN MOTOR")
            self.engine_kind_chip.set_tone("warn")
            self.engine_path_label.setText("Descarga el motor desde Inicio para poder recibir AirPlay.")
        present = firewall.rules_present()
        self.fw_chip.setText("FIREWALL CONFIGURADO" if present else "FIREWALL SIN CONFIGURAR")
        self.fw_chip.set_tone("ok" if present else "warn")
        self.t_autostart.set_on(autostart.is_enabled() if winapi.IS_WINDOWS else self.app.cfg.autostart)
