"""Pagina Musica: solo audio, sin video, con caratula y visualizador."""
from __future__ import annotations

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QHBoxLayout, QVBoxLayout, QWidget

from ...core.audioctl import SessionVolume
from ...core.metadata import read_track
from ...presets import audio_format_note
from .. import theme as T
from ..widgets import (
    ActionButton, Chip, Collapsible, LabeledSlider, StatTile, TextToggle,
    Visualizer, card, label, row,
)
from .base import Page


class MusicPage(Page):
    key = "music"
    title = "Musica"

    def build(self) -> None:
        self.vol = SessionVolume()
        self._cover_stamp = 0.0

        self.lay.addWidget(self.header(
            "Solo audio, sin video",
            "Modo Musica",
            "El iPhone manda unicamente el audio: la pantalla del celular queda privada "
            "y no se transmite ningun video.",
        ))

        top = QWidget()
        tl = QHBoxLayout(top)
        tl.setContentsMargins(0, 0, 0, 0)
        tl.setSpacing(16)
        self.mode_toggle = TextToggle(self.app.cfg.mode == "music", "Modo Musica ON", "Modo Musica OFF")
        self.mode_toggle.setFixedWidth(160)
        self.mode_toggle.changed.connect(self._toggle_mode)
        self.state_chip = Chip("EN ESPERA", "neutral")
        tl.addWidget(self.mode_toggle, 0, Qt.AlignVCenter)
        tl.addWidget(self.state_chip, 0, Qt.AlignVCenter)
        tl.addStretch(1)
        self.apply_btn = ActionButton("Aplicar y reconectar", "primary")
        self.apply_btn.clicked.connect(lambda: self.app.save_and_apply(force=True))
        tl.addWidget(self.apply_btn, 0, Qt.AlignVCenter)
        self.lay.addWidget(card(top, 1, 18))

        # --- Reproduciendo ahora -----------------------------------------
        now = QWidget()
        nl = QHBoxLayout(now)
        nl.setContentsMargins(0, 0, 0, 0)
        nl.setSpacing(18)

        self.cover = label("Sin caratula", "mute")
        self.cover.setFixedSize(132, 132)
        self.cover.setAlignment(Qt.AlignCenter)
        self.cover.setStyleSheet(
            f"background: {T.SURFACE_3}; border: 1px solid {T.LINE}; border-radius: 10px;"
        )
        info = QVBoxLayout()
        info.setSpacing(5)
        self.track_title = label("Nada reproduciendose", "h2")
        self.track_artist = label("Conecta el iPhone y elegi este receptor en AirPlay", "dim", wrap=True)
        self.track_album = label("", "mute")
        info.addWidget(self.track_title)
        info.addWidget(self.track_artist)
        info.addWidget(self.track_album)
        info.addStretch(1)
        nl.addWidget(self.cover, 0)
        nl.addLayout(info, 1)
        self.lay.addWidget(card(now, 1, 20))

        # --- Visualizador + volumen ---------------------------------------
        audio_box = QWidget()
        ab = QVBoxLayout(audio_box)
        ab.setContentsMargins(0, 0, 0, 0)
        ab.setSpacing(14)
        self.viz = Visualizer()
        ab.addWidget(self.viz)
        self.volume = LabeledSlider("Volumen del receptor", 0, 100, int(self.app.cfg.volume * 100), "%")
        self.volume.valueChanged.connect(self._volume_changed)
        self.mute_toggle = TextToggle(self.app.cfg.muted, "Silenciado", "Con sonido")
        self.mute_toggle.changed.connect(self._mute_changed)
        ab.addWidget(self.volume)
        ab.addWidget(row(self.mute_toggle, "stretch",
                         label("El volumen se aplica sin cortar la transmision", "mute")))
        if not self.vol.available:
            ab.addWidget(label(
                "Para cambiar el volumen en caliente instala el extra 'pycaw' "
                "(viene en requirements.txt). Sin el, el volumen se aplica al reconectar.",
                "warn", wrap=True))
        self.lay.addWidget(card(audio_box, 1, 20))

        # --- Datos ---------------------------------------------------------
        tiles = QWidget()
        tl2 = QHBoxLayout(tiles)
        tl2.setContentsMargins(0, 0, 0, 0)
        tl2.setSpacing(10)
        self.tile_fmt = StatTile("Formato", "-")
        self.tile_dev = StatTile("Dispositivo", "-")
        self.tile_time = StatTile("Sesion", "-")
        for t in (self.tile_fmt, self.tile_dev, self.tile_time):
            tl2.addWidget(t, 1)
        self.lay.addWidget(tiles)

        # --- Ayuda ----------------------------------------------------------
        help_box = QWidget()
        hb = QVBoxLayout(help_box)
        hb.setContentsMargins(0, 0, 0, 0)
        hb.setSpacing(10)
        hb.addWidget(label(audio_format_note(self.app.cfg), "dim", wrap=True))
        hb.addWidget(label(
            "Como enviar solo audio desde el iPhone:\n"
            "1. Abri Musica, Spotify o cualquier reproductor.\n"
            "2. Toca el boton AirPlay del reproductor (o Centro de control > tarjeta de sonido).\n"
            "3. Elegi este receptor. La pantalla del iPhone NO se comparte.\n\n"
            "Si en cambio usas 'Duplicar pantalla', se manda video y audio; para eso "
            "esta el Modo Pantalla.", "dim", wrap=True))
        self.lay.addWidget(Collapsible("Como usar el Modo Musica", help_box, opened=True))

        self._timer = QTimer(self)
        self._timer.setInterval(700)
        self._timer.timeout.connect(self._poll)
        self._timer.start()

    # ------------------------------------------------------------------
    def _toggle_mode(self, on: bool) -> None:
        self.app.set_mode("music" if on else "screen")

    def _volume_changed(self, v: int) -> None:
        cfg = self.app.cfg
        cfg.volume = v / 100.0
        self.app.save_config()
        if not self.vol.set_volume(self.app.engine.pid, cfg.volume):
            self._pending_volume = True

    def _mute_changed(self, on: bool) -> None:
        cfg = self.app.cfg
        cfg.muted = on
        self.app.save_config()
        self.vol.set_mute(self.app.engine.pid, on)

    def _poll(self) -> None:
        if not self.isVisible():
            return
        track = read_track()
        if track.has_data:
            self.track_title.setText(track.title or "Reproduciendo")
            self.track_artist.setText(track.artist or "Artista desconocido")
            self.track_album.setText(track.album)
        if track.cover_path and track.cover_stamp != self._cover_stamp:
            pix = QPixmap(track.cover_path)
            if not pix.isNull():
                self._cover_stamp = track.cover_stamp
                self.cover.setPixmap(pix.scaled(132, 132, Qt.KeepAspectRatio, Qt.SmoothTransformation))
                self.cover.setText("")
        level = self.vol.peak()
        if level <= 0.0 and self.app.engine.streaming:
            level = 0.45
        self.viz.set_level(level, self.app.engine.streaming)

    # ------------------------------------------------------------------
    def on_show(self) -> None:
        self.refresh()
        self._poll()

    def refresh(self) -> None:
        music = self.app.cfg.mode == "music"
        self.mode_toggle.set_on(music)
        streaming = self.app.engine.streaming
        self.state_chip.setText("SONANDO" if streaming and music else ("EN ESPERA" if music else "MODO PANTALLA"))
        self.state_chip.set_tone("live" if streaming and music else ("violet" if music else "neutral"))
        self.volume.set_value(int(self.app.cfg.volume * 100))
        self.mute_toggle.set_on(self.app.cfg.muted)

    def update_stats(self, s: dict) -> None:
        self.tile_fmt.set_value("ALAC" if "ALAC" in (s.get("audio") or "") else "AAC-ELD")
        self.tile_dev.set_value(s.get("device") or "-")
        el = int(s.get("elapsed", 0))
        self.tile_time.set_value(f"{el // 60:02d}:{el % 60:02d}" if s.get("streaming") else "-")
