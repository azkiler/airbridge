"""Pagina Pantalla: video incrustado, estadisticas y controles de anclado."""
from __future__ import annotations

from PySide6.QtCore import QEvent, Qt, QTimer
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import QComboBox, QHBoxLayout, QVBoxLayout, QWidget

from ...config import FPS_CHOICES, RESOLUTIONS
from ...presets import mark_custom, quality_summary
from ...win import winapi
from ...win.embed import VideoWindow
from .. import theme as T
from ..widgets import (
    ActionButton, Chip, Collapsible, StatTile, TextToggle, VideoSurface, card, label, row,
)
from .base import Page

DECODERS = [
    ("auto", "Automatico (recomendado)"),
    ("d3d11h264dec", "GPU Direct3D11 (AMD / Intel / NVIDIA)"),
    ("nvh264dec", "GPU NVIDIA NVDEC"),
    ("avdec_h264", "CPU (software, mas lento)"),
]


class ScreenPage(Page):
    key = "screen"
    title = "Pantalla"

    def build(self) -> None:
        self.vw = VideoWindow()
        self.fullscreen = False

        head = QWidget()
        hl = QHBoxLayout(head)
        hl.setContentsMargins(0, 0, 0, 0)
        hl.setSpacing(10)
        titles = QVBoxLayout()
        titles.setSpacing(4)
        titles.addWidget(label("MIRRORING", "kicker"))
        titles.addWidget(label("Pantalla del iPhone", "h1"))
        hl.addLayout(titles, 1)
        self.state_chip = Chip("EN ESPERA", "neutral")
        self.dev_chip = Chip("Sin dispositivo", "neutral")
        hl.addWidget(self.state_chip, 0, Qt.AlignVCenter)
        hl.addWidget(self.dev_chip, 0, Qt.AlignVCenter)
        self.lay.addWidget(head)

        # --- Controles principales ---------------------------------------
        self.fs_btn = ActionButton("Pantalla completa", "primary")
        self.fs_btn.clicked.connect(self.toggle_fullscreen)
        self.float_toggle = TextToggle(self.app.cfg.floating_video, "Ventana flotante", "Ventana flotante")
        self.float_toggle.setFixedWidth(150)
        self.float_toggle.changed.connect(self._toggle_floating)
        self.pin_toggle = TextToggle(self.app.cfg.pin_video_window, "Video anclado", "Video anclado")
        self.pin_toggle.changed.connect(self._toggle_pin)
        self.stats_toggle = TextToggle(self.app.cfg.stats_overlay, "Estadisticas", "Estadisticas")
        self.stats_toggle.changed.connect(self._toggle_stats)
        self.reconnect_btn = ActionButton("Reconectar", "neutral")
        self.reconnect_btn.clicked.connect(self.app.engine.restart)
        self.lay.addWidget(row(self.fs_btn, self.float_toggle, self.pin_toggle,
                               self.stats_toggle, "stretch", self.reconnect_btn))

        # --- Superficie de video -----------------------------------------
        self.surface = VideoSurface()
        self.surface.demo = bool(getattr(self.app, "demo", False))
        self.surface.installEventFilter(self)
        video_card = card(self.surface, 1, 10)
        video_card.setMinimumHeight(300)
        self.lay.addWidget(video_card, 1)

        self.quality_label = label(quality_summary(self.app.cfg), "mute")
        self.lay.addWidget(self.quality_label)

        # --- Aviso de modo musica ----------------------------------------
        self.music_notice = QWidget()
        mn = QVBoxLayout(self.music_notice)
        mn.setContentsMargins(0, 0, 0, 0)
        mn.setSpacing(10)
        mn.addWidget(label("Estas en Modo Musica", "h2"))
        mn.addWidget(label(
            "El video esta desactivado a proposito: solo se transmite audio. "
            "Volve a Modo Pantalla para ver la pantalla del iPhone.", "dim", wrap=True))
        back = ActionButton("Volver a Modo Pantalla", "primary")
        back.clicked.connect(lambda: self.app.set_mode("screen"))
        mn.addWidget(back, 0, Qt.AlignLeft)
        self.music_card = card(self.music_notice, 2, 20)
        self.lay.addWidget(self.music_card)

        # --- Estadisticas -------------------------------------------------
        self.stats_row = QWidget()
        sr = QHBoxLayout(self.stats_row)
        sr.setContentsMargins(0, 0, 0, 0)
        sr.setSpacing(10)
        self.tile_fps = StatTile("FPS", "-")
        self.tile_res = StatTile("Resolucion", "-")
        self.tile_lat = StatTile("Latencia est.", "-", " ms")
        self.tile_audio = StatTile("Audio", "-")
        self.tile_time = StatTile("Sesion", "-")
        for t in (self.tile_fps, self.tile_res, self.tile_lat, self.tile_audio, self.tile_time):
            sr.addWidget(t, 1)
        self.lay.addWidget(self.stats_row)

        # --- Ajustes rapidos ----------------------------------------------
        quick = QWidget()
        ql = QVBoxLayout(quick)
        ql.setContentsMargins(0, 0, 0, 0)
        ql.setSpacing(12)
        r1 = QHBoxLayout()
        r1.setSpacing(12)
        self.res_combo = QComboBox()
        self.res_combo.addItems([f"{r.split('x')[0]} x {r.split('x')[1]}" for r in RESOLUTIONS])
        self.res_combo.setCurrentIndex(RESOLUTIONS.index(self.app.cfg.resolution))
        self.fps_combo = QComboBox()
        self.fps_combo.addItems([f"{f} fps" for f in FPS_CHOICES])
        self.fps_combo.setCurrentIndex(FPS_CHOICES.index(self.app.cfg.fps))
        self.dec_combo = QComboBox()
        for _k, text in DECODERS:
            self.dec_combo.addItem(text)
        keys = [k for k, _ in DECODERS]
        self.dec_combo.setCurrentIndex(keys.index(self.app.cfg.decoder) if self.app.cfg.decoder in keys else 0)
        for cap, w in (("Resolucion solicitada", self.res_combo), ("FPS maximos", self.fps_combo),
                       ("Decodificacion", self.dec_combo)):
            box = QVBoxLayout()
            box.setSpacing(5)
            box.addWidget(label(cap, "dim"))
            box.addWidget(w)
            holder = QWidget()
            holder.setLayout(box)
            r1.addWidget(holder, 1)
        ql.addLayout(r1)
        apply_btn = ActionButton("Aplicar y reconectar", "primary")
        apply_btn.clicked.connect(self.apply_quick)
        ql.addWidget(apply_btn, 0, Qt.AlignLeft)
        ql.addWidget(label(
            "AirPlay entrega como maximo 1080p a 60 fps en modo duplicar pantalla. "
            "1440p y 4K dependen del modelo de iPhone y de la app; 120 fps es experimental.",
            "mute", wrap=True))
        self.lay.addWidget(Collapsible("Ajustes rapidos de imagen", quick, opened=False))

        self._layout_timer = QTimer(self)
        self._layout_timer.setInterval(500)
        self._layout_timer.timeout.connect(self._relayout)
        self._layout_timer.start()

    # ------------------------------------------------------------------
    def eventFilter(self, obj, event):  # noqa: N802
        if obj is getattr(self, "surface", None) and event.type() in (QEvent.Resize, QEvent.Move, QEvent.Show):
            QTimer.singleShot(0, self._relayout)
        return super().eventFilter(obj, event)

    def set_video_hwnd(self, hwnd: int) -> None:
        self.vw.hwnd = hwnd
        self.surface.set_embedded(hwnd if self.app.cfg.embed_video else 0)
        if self.app.cfg.mode == "music":
            return
        if self.app.cfg.floating_video:
            self.vw.make_floating(self.app.cfg.pin_video_window)
            self._place_floating()
        elif self.app.cfg.embed_video:
            self.vw.attach(winapi.hwnd_of(self.surface))
            self._relayout()
        self.surface.set_texts("Transmitiendo", "")

    def clear_video(self) -> None:
        self.vw.reset()
        self.surface.set_embedded(0)
        self.surface.set_texts("Esperando transmision",
                               "En el iPhone: Centro de control  >  Duplicar pantalla  >  AirBridge")

    def _relayout(self) -> None:
        if not self.vw.hwnd or not winapi.is_window(self.vw.hwnd):
            return
        if self.vw.embedded:
            w, h = self.surface.width(), self.surface.height()
            self.vw.layout(0, 0, w, h)
        elif self.vw.floating:
            self._place_floating()

    def _place_floating(self) -> None:
        """La ventana flotante sigue al panel de video de la app."""
        if not self.vw.hwnd:
            return
        if self.fullscreen:
            scr = QGuiApplication.primaryScreen().geometry()
            self.vw.layout(scr.x(), scr.y(), scr.width(), scr.height())
            return
        top = self.surface.mapToGlobal(self.surface.rect().topLeft())
        self.vw.layout(top.x(), top.y(), self.surface.width(), self.surface.height())

    # ------------------------------------------------------------------
    def toggle_fullscreen(self) -> None:
        self.fullscreen = not self.fullscreen
        self.fs_btn.setText("Salir de pantalla completa" if self.fullscreen else "Pantalla completa")
        if self.vw.hwnd:
            if self.fullscreen:
                self.vw.make_floating(True)
            elif self.app.cfg.floating_video:
                self.vw.make_floating(self.app.cfg.pin_video_window)
            elif self.app.cfg.embed_video:
                self.vw.attach(winapi.hwnd_of(self.surface))
            self._relayout()
        else:
            self.app.toggle_fullscreen_window()
        self.app.toast("Pantalla completa" if self.fullscreen else "Ventana normal", "info")

    def _toggle_floating(self, on: bool) -> None:
        self.app.cfg.floating_video = on
        self.app.save_config()
        if not self.vw.hwnd:
            return
        if on:
            self.surface.set_embedded(0)
            self.vw.make_floating(self.app.cfg.pin_video_window)
            self._place_floating()
        else:
            self.vw.attach(winapi.hwnd_of(self.surface))
            self.surface.set_embedded(self.vw.hwnd)
            self._relayout()

    def _toggle_pin(self, on: bool) -> None:
        self.app.cfg.pin_video_window = on
        self.app.save_config()
        self.vw.keep_on_top(on)
        self.app.toast("Video anclado arriba de todo" if on else "Video sin anclar", "info")

    def _toggle_stats(self, on: bool) -> None:
        self.app.cfg.stats_overlay = on
        self.app.save_config()
        self.stats_row.setVisible(on)

    def apply_quick(self) -> None:
        cfg = self.app.cfg
        cfg.resolution = RESOLUTIONS[self.res_combo.currentIndex()]
        cfg.fps = FPS_CHOICES[self.fps_combo.currentIndex()]
        cfg.decoder = DECODERS[self.dec_combo.currentIndex()][0]
        mark_custom(cfg)
        cfg.validate()
        self.quality_label.setText(quality_summary(cfg))
        self.app.save_and_apply(force=True)
        self.app.toast("Ajustes de imagen aplicados", "ok")

    # ------------------------------------------------------------------
    def on_show(self) -> None:
        self.refresh()
        if self.vw.hwnd and winapi.is_window(self.vw.hwnd):
            if self.app.cfg.embed_video and not self.app.cfg.floating_video:
                self.vw.attach(winapi.hwnd_of(self.surface))
                self.surface.set_embedded(self.vw.hwnd)
            winapi.show_window(self.vw.hwnd, True)
            QTimer.singleShot(60, self._relayout)

    def on_hide(self) -> None:
        # Si el video queda incrustado y cambiamos de pagina, hay que ocultar
        # el HWND: si no, se dibuja por encima de la otra pagina.
        if self.vw.hwnd and self.vw.embedded:
            winapi.show_window(self.vw.hwnd, False)

    def refresh(self) -> None:
        eng = self.app.engine
        music = self.app.cfg.mode == "music"
        self.music_card.setVisible(music)
        self.surface.setVisible(not music)
        self.quality_label.setText(quality_summary(self.app.cfg))
        streaming = eng.streaming and not music
        self.state_chip.setText("EN VIVO" if streaming else "EN ESPERA")
        self.state_chip.set_tone("live" if streaming else "neutral")
        self.dev_chip.setText(eng.device.get("name") or "Sin dispositivo")
        self.dev_chip.set_tone("violet" if eng.device else "neutral")
        self.stats_row.setVisible(self.app.cfg.stats_overlay)
        self.float_toggle.set_on(self.app.cfg.floating_video)
        self.pin_toggle.set_on(self.app.cfg.pin_video_window)
        if music:
            self.surface.set_texts("Modo Musica activo", "El video no se transmite en este modo")

    def update_stats(self, s: dict) -> None:
        fps = s.get("fps")
        self.tile_fps.set_value(f"{fps:.0f}" if fps else "-")
        self.tile_res.set_value(s.get("resolution") or "-")
        lat = s.get("latency_ms")
        self.tile_lat.set_value(f"{lat:.0f}" if lat else "-")
        self.tile_audio.set_value("ALAC" if "ALAC" in (s.get("audio") or "") else "AAC-ELD")
        el = int(s.get("elapsed", 0))
        self.tile_time.set_value(f"{el // 60:02d}:{el % 60:02d}" if s.get("streaming") else "-")
