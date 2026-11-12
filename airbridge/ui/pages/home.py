"""Pagina Inicio: estado del receptor, conexion y descarga del motor."""
from __future__ import annotations

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import QComboBox, QGridLayout, QHBoxLayout, QLineEdit, QProgressBar, QVBoxLayout, QWidget

from ...core import netinfo, provision
from ...core.engine import MISSING, READY, STREAMING, ERROR, STARTING, STOPPED, STATE_LABEL
from ...paths import engine_dir
from .. import theme as T
from ..widgets import (
    ActionButton, Chip, Collapsible, LabeledSlider, StatTile, card, hsep, label, row,
)
from .base import Page


class HomePage(Page):
    key = "home"
    title = "Inicio"

    def build(self) -> None:
        self.lay.addWidget(self.header(
            "Receptor AirPlay por Wi-Fi",
            "Tu iPhone, en esta pantalla",
            "Sin cables, sin Bluetooth y sin instalar nada en el celular: solo AirPlay.",
        ))

        # --- Tarjeta principal -----------------------------------------
        hero = QWidget()
        hl = QHBoxLayout(hero)
        hl.setContentsMargins(0, 0, 0, 0)
        hl.setSpacing(22)

        left = QVBoxLayout()
        left.setSpacing(8)
        self.state_chip = Chip("INICIANDO", "neutral")
        self.name_label = label(self.app.cfg.receiver_name, "h1")
        self.hint_label = label("Buscando red...", "dim", wrap=True)
        left.addWidget(self.state_chip, 0, Qt.AlignLeft)
        left.addWidget(self.name_label)
        left.addWidget(self.hint_label)
        left.addStretch(1)

        right = QVBoxLayout()
        right.setSpacing(10)
        self.main_btn = ActionButton("Iniciar receptor", "primary")
        self.main_btn.setMinimumWidth(210)
        self.main_btn.clicked.connect(self.app.toggle_engine)
        self.music_btn = ActionButton("Ir a Modo Musica", "violet")
        self.music_btn.clicked.connect(lambda: self.app.goto("music"))
        self.restart_btn = ActionButton("Reiniciar receptor", "neutral")
        self.restart_btn.clicked.connect(self.app.engine.restart)
        right.addWidget(self.main_btn)
        right.addWidget(self.music_btn)
        right.addWidget(self.restart_btn)
        right.addStretch(1)

        hl.addLayout(left, 1)
        hl.addLayout(right, 0)
        self.lay.addWidget(card(hero, 1, 22))

        # --- Motor ausente ---------------------------------------------
        self.engine_box = QWidget()
        eb = QVBoxLayout(self.engine_box)
        eb.setContentsMargins(0, 0, 0, 0)
        eb.setSpacing(10)
        eb.addWidget(label("Falta el motor AirPlay", "h2"))
        eb.addWidget(label(
            "AirBridge usa UxPlay, el receptor AirPlay open source (GPLv3) que ya "
            "funciona en Windows 11 con Bonjour, Direct3D11 y WASAPI. Se descarga "
            "una sola vez (unos 113 MB) y queda guardado en tu usuario.", "dim", wrap=True))
        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setTextVisible(False)
        self.progress.setFixedHeight(8)
        self.progress.setStyleSheet(
            f"QProgressBar {{ background: {T.SURFACE_3}; border: none; border-radius: 4px; }}"
            f"QProgressBar::chunk {{ background: {T.ORANGE}; border-radius: 4px; }}"
        )
        self.progress.hide()
        self.progress_label = label("", "mute")
        self.download_btn = ActionButton("Descargar motor AirPlay", "primary")
        self.download_btn.clicked.connect(self.start_download)
        pick = ActionButton("Ya lo tengo: elegir carpeta", "neutral")
        pick.clicked.connect(self.pick_engine)
        web = ActionButton("Abrir pagina de descargas", "ghost")
        web.clicked.connect(lambda: self.app.open_url(provision.RELEASES_PAGE))
        eb.addWidget(self.progress)
        eb.addWidget(self.progress_label)
        eb.addWidget(row(self.download_btn, pick, web, "stretch"))
        self.engine_card = card(self.engine_box, 2, 20)
        self.lay.addWidget(self.engine_card)

        # --- Pasos ------------------------------------------------------
        steps = QWidget()
        sl = QVBoxLayout(steps)
        sl.setContentsMargins(0, 0, 0, 0)
        sl.setSpacing(10)
        sl.addWidget(label("Conectar el iPhone", "h2"))
        for n, (t, d) in enumerate([
            ("Misma red Wi-Fi", "Conecta el iPhone al mismo Wi-Fi que esta PC (ideal 5 GHz)."),
            ("Centro de control", "Desliza desde la esquina superior derecha del iPhone."),
            ("Duplicar pantalla", "Toca 'Duplicar pantalla' y elige el nombre de este receptor."),
        ], start=1):
            item = QWidget()
            il = QHBoxLayout(item)
            il.setContentsMargins(0, 0, 0, 0)
            il.setSpacing(12)
            num = label(f"PASO {n}", "kicker")
            num.setFixedWidth(64)
            txt = QVBoxLayout()
            txt.setSpacing(2)
            txt.addWidget(label(t, "h3"))
            txt.addWidget(label(d, "dim", wrap=True))
            il.addWidget(num, 0, Qt.AlignTop)
            il.addLayout(txt, 1)
            sl.addWidget(item)
        self.lay.addWidget(card(steps, 1, 20))

        # --- Tiles de red y sesion --------------------------------------
        tiles = QWidget()
        tl = QHBoxLayout(tiles)
        tl.setContentsMargins(0, 0, 0, 0)
        tl.setSpacing(12)
        net = QWidget()
        nl = QVBoxLayout(net)
        nl.setContentsMargins(0, 0, 0, 0)
        nl.setSpacing(6)
        nl.addWidget(label("RED", "kicker"))
        self.ip_value = label("-", "h3")
        self.wifi_value = label("-", "dim")
        self.bonjour_value = label("-", "dim")
        nl.addWidget(self.ip_value)
        nl.addWidget(self.wifi_value)
        nl.addWidget(self.bonjour_value)
        sess = QWidget()
        sl2 = QVBoxLayout(sess)
        sl2.setContentsMargins(0, 0, 0, 0)
        sl2.setSpacing(6)
        sl2.addWidget(label("SESION", "kicker"))
        self.dev_value = label("Sin dispositivo", "h3")
        self.mode_value = label("-", "dim")
        self.time_value = label("-", "dim")
        sl2.addWidget(self.dev_value)
        sl2.addWidget(self.mode_value)
        sl2.addWidget(self.time_value)
        tl.addWidget(card(net, 2, 16), 1)
        tl.addWidget(card(sess, 2, 16), 1)
        self.lay.addWidget(tiles)

        # --- Conexion avanzada ------------------------------------------
        adv = QWidget()
        al = QGridLayout(adv)
        al.setContentsMargins(0, 0, 0, 0)
        al.setHorizontalSpacing(14)
        al.setVerticalSpacing(10)
        al.addWidget(label("Nombre visible en el iPhone", "dim"), 0, 0)
        self.name_edit = QLineEdit(self.app.cfg.receiver_name)
        self.name_edit.setMaxLength(48)
        al.addWidget(self.name_edit, 0, 1)
        al.addWidget(label("Puerto base (TCP y UDP)", "dim"), 1, 0)
        self.port_edit = QLineEdit(str(self.app.cfg.tcp_port))
        self.port_edit.setFixedWidth(120)
        al.addWidget(self.port_edit, 1, 1, Qt.AlignLeft)
        al.addWidget(label("PIN de 4 digitos (vacio = sin PIN)", "dim"), 2, 0)
        self.pin_edit = QLineEdit(self.app.cfg.pin_code)
        self.pin_edit.setFixedWidth(120)
        self.pin_edit.setMaxLength(4)
        self.pin_edit.setPlaceholderText("sin PIN")
        al.addWidget(self.pin_edit, 2, 1, Qt.AlignLeft)
        apply_btn = ActionButton("Aplicar y reiniciar receptor", "primary")
        apply_btn.clicked.connect(self.apply_advanced)
        al.addWidget(apply_btn, 3, 0, 1, 2, Qt.AlignLeft)
        al.addWidget(label(
            "Sin PIN el iPhone conecta directo. Con PIN, el celular pide el codigo "
            "una vez y lo recuerda.", "mute", wrap=True), 4, 0, 1, 2)
        self.lay.addWidget(Collapsible("Conexion avanzada", adv, opened=False))

        # --- Diagnostico -------------------------------------------------
        diag = QWidget()
        dl = QVBoxLayout(diag)
        dl.setContentsMargins(0, 0, 0, 0)
        dl.setSpacing(10)
        self.diag_label = label("Todavia no se ejecuto ninguna comprobacion.", "dim", wrap=True)
        fw = ActionButton("Configurar firewall de Windows", "neutral")
        fw.clicked.connect(self.app.setup_firewall)
        chk = ActionButton("Comprobar red y Bonjour", "neutral")
        chk.clicked.connect(self.run_check)
        cp = ActionButton("Copiar diagnostico", "ghost")
        cp.clicked.connect(self.app.copy_diagnostics)
        dl.addWidget(row(fw, chk, cp, "stretch"))
        dl.addWidget(self.diag_label)
        self.lay.addWidget(Collapsible("Diagnostico y firewall", diag, opened=False))

        self._worker = None
        self.refresh_network()

    # ------------------------------------------------------------------
    def refresh_network(self) -> None:
        ip = netinfo.local_ip()
        wifi = netinfo.wifi_info()
        self.ip_value.setText(f"IP local  {ip}  -  puerto {self.app.cfg.tcp_port}")
        if wifi.get("ssid"):
            extra = f"  -  {wifi.get('band') or wifi.get('radio') or ''}  -  senal {wifi.get('signal', '')}"
            self.wifi_value.setText(f"Wi-Fi  {wifi['ssid']}{extra}")
        else:
            self.wifi_value.setText("Wi-Fi: no detectado (puede ser Ethernet)")
        self.bonjour_value.setText(
            "Bonjour (mDNS): activo" if netinfo.bonjour_service_running()
            else "Bonjour (mDNS): se inicia con el motor"
        )
        self.hint_label.setText(netinfo.network_hint(ip, wifi))

    def run_check(self) -> None:
        ip = netinfo.local_ip()
        wifi = netinfo.wifi_info()
        ok_bonjour = netinfo.bonjour_service_running()
        listening = netinfo.port_listening(self.app.cfg.tcp_port)
        from ...win import firewall
        lines = [
            f"IP de la PC: {ip}",
            f"Wi-Fi: {wifi.get('ssid') or 'no detectado'} {wifi.get('band', '')}",
            f"Servicio Bonjour: {'activo' if ok_bonjour else 'no activo (el motor lo instala al arrancar)'}",
            f"Puerto {self.app.cfg.tcp_port} escuchando: {'si' if listening else 'no'}",
            f"Reglas de firewall AirBridge: {'presentes' if firewall.rules_present() else 'faltantes'}",
            netinfo.network_hint(ip, wifi),
        ]
        self.diag_label.setText("\n".join(lines))
        self.app.toast("Comprobacion terminada", "info")

    def apply_advanced(self) -> None:
        cfg = self.app.cfg
        cfg.receiver_name = netinfo.sanitize_receiver_name(self.name_edit.text())
        try:
            cfg.tcp_port = int(self.port_edit.text())
        except ValueError:
            pass
        cfg.pin_code = self.pin_edit.text().strip()
        cfg.validate()
        self.name_label.setText(cfg.receiver_name)
        self.app.save_and_apply(force=True)
        self.app.toast(f"Receptor anunciado como '{cfg.receiver_name}'", "ok")

    # ------------------------------------------------------------------
    def start_download(self) -> None:
        if self._worker is not None and self._worker.isRunning():
            return
        self.download_btn.setEnabled(False)
        self.progress.show()
        self.progress.setValue(0)
        self._worker = provision.DownloadWorker(target=engine_dir())
        self._worker.progress.connect(self._on_progress)
        self._worker.done.connect(self._on_done)
        self._worker.failed.connect(self._on_failed)
        self._worker.start()

    def _on_progress(self, pct: int, text: str) -> None:
        self.progress.setValue(pct)
        self.progress_label.setText(text)

    def _on_done(self, path: str) -> None:
        self.progress.setValue(100)
        self.progress_label.setText("Motor instalado correctamente.")
        self.download_btn.setEnabled(True)
        self.app.cfg.engine_path = path
        self.app.engine.refresh_install()
        self.app.save_and_apply()
        self.app.toast("Motor AirPlay listo", "ok")
        self.refresh()
        if self.app.cfg.start_engine_on_launch:
            QTimer.singleShot(600, self.app.engine.start)

    def _on_failed(self, msg: str) -> None:
        self.progress_label.setText(msg)
        self.download_btn.setEnabled(True)
        self.app.toast(msg, "error")

    def pick_engine(self) -> None:
        from PySide6.QtWidgets import QFileDialog
        path = QFileDialog.getExistingDirectory(self, "Carpeta donde esta uxplay-windows.exe")
        if not path:
            return
        found = provision.find_engine(path)
        if found is None:
            self.app.toast("En esa carpeta no hay un motor AirPlay valido", "warn")
            return
        self.app.cfg.engine_path = str(found.exe)
        self.app.engine.refresh_install()
        self.app.save_and_apply()
        self.refresh()
        self.app.toast("Motor encontrado", "ok")

    # ------------------------------------------------------------------
    def on_show(self) -> None:
        self.refresh_network()
        self.refresh()

    def refresh(self) -> None:
        eng = self.app.engine
        state = eng.state
        self.state_chip.setText(STATE_LABEL.get(state, state).upper())
        tone = {STREAMING: "live", READY: "ok", STARTING: "violet",
                ERROR: "err", MISSING: "warn", STOPPED: "neutral"}.get(state, "neutral")
        self.state_chip.set_tone(tone)
        self.state_chip.updateGeometry()
        self.main_btn.setText("Detener receptor" if state in (READY, STREAMING, STARTING) else "Iniciar receptor")
        self.engine_card.setVisible(eng.install is None)
        self.name_label.setText(self.app.cfg.receiver_name)
        dev = eng.device.get("name") or "Sin dispositivo"
        self.dev_value.setText(dev)
        self.mode_value.setText(
            "Modo Musica - solo audio" if self.app.cfg.mode == "music" else "Modo Pantalla - video + audio"
        )

    def update_stats(self, s: dict) -> None:
        if s.get("streaming"):
            m, sec = divmod(int(s.get("elapsed", 0)), 60)
            self.time_value.setText(f"Transmitiendo hace {m:02d}:{sec:02d}")
        else:
            self.time_value.setText("Sin transmision activa")
