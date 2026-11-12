"""Pagina Gaming: presets de latencia y ajustes finos de rendimiento."""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import QComboBox, QFrame, QHBoxLayout, QVBoxLayout, QWidget

from ...config import FPS_CHOICES, RESOLUTIONS
from ...presets import PRESETS, apply_preset, estimated_latency_ms, mark_custom
from .. import theme as T
from ..widgets import (
    ActionButton, Chip, Collapsible, LabeledSlider, StatTile, TextToggle, card, label, row,
)
from .base import Page
from .screen import DECODERS


class PresetCard(QFrame):
    chosen = Signal(str)

    def __init__(self, key: str, title: str, tagline: str, detail: str, parent=None) -> None:
        super().__init__(parent)
        self.key = key
        self.active = False
        self.setCursor(Qt.PointingHandCursor)
        self.setProperty("card", "2")
        lay = QVBoxLayout(self)
        lay.setContentsMargins(18, 16, 18, 16)
        lay.setSpacing(8)
        head = row(label(title, "h2"), "stretch")
        lay.addWidget(head)
        self.chip = Chip(tagline.upper(), "neutral")
        lay.addWidget(self.chip, 0, Qt.AlignLeft)
        lay.addWidget(label(detail, "dim", wrap=True))
        self.select_btn = ActionButton("Usar este preset", "neutral", small=True)
        self.select_btn.clicked.connect(lambda: self.chosen.emit(self.key))
        lay.addWidget(self.select_btn, 0, Qt.AlignLeft)
        self.setMinimumWidth(230)

    def set_active(self, active: bool) -> None:
        self.active = active
        self.chip.set_tone("violet" if active else "neutral")
        self.select_btn.setText("Preset activo" if active else "Usar este preset")
        self.select_btn.accent = "violet" if active else "neutral"
        self.select_btn.setEnabled(not active)
        self.update()

    def mousePressEvent(self, e) -> None:  # noqa: N802
        if e.button() == Qt.LeftButton:
            self.chosen.emit(self.key)
        super().mousePressEvent(e)

    def paintEvent(self, e) -> None:  # noqa: N802
        super().paintEvent(e)
        if self.active:
            p = QPainter(self)
            p.setRenderHint(QPainter.Antialiasing, True)
            p.setPen(QPen(QColor(T.VIOLET), 2))
            p.drawRoundedRect(self.rect().adjusted(1, 1, -1, -1), T.RADIUS, T.RADIUS)
            p.end()


class GamingPage(Page):
    key = "gaming"
    title = "Gaming"

    def build(self) -> None:
        self.lay.addWidget(self.header(
            "Baja latencia",
            "Ajustes de gaming",
            "Elegi un perfil y afiná la respuesta. Todo se aplica reiniciando el receptor "
            "(el iPhone se vuelve a conectar solo en la mayoria de los casos).",
        ))

        cards = QWidget()
        cl = QHBoxLayout(cards)
        cl.setContentsMargins(0, 0, 0, 0)
        cl.setSpacing(12)
        self.preset_cards: dict[str, PresetCard] = {}
        for key, p in PRESETS.items():
            c = PresetCard(key, p.title, p.tagline, p.detail)
            c.chosen.connect(self.choose_preset)
            self.preset_cards[key] = c
            cl.addWidget(c, 1)
        self.lay.addWidget(cards)

        # --- Afinado -------------------------------------------------------
        tune = QWidget()
        tl = QVBoxLayout(tune)
        tl.setContentsMargins(0, 0, 0, 0)
        tl.setSpacing(14)

        line1 = QHBoxLayout()
        line1.setSpacing(12)
        self.fps_combo = QComboBox()
        self.fps_combo.addItems([f"{f} fps" for f in FPS_CHOICES])
        self.res_combo = QComboBox()
        self.res_combo.addItems([r.replace("x", " x ") for r in RESOLUTIONS])
        self.dec_combo = QComboBox()
        for _k, text in DECODERS:
            self.dec_combo.addItem(text)
        for cap, w in (("FPS maximos", self.fps_combo), ("Resolucion", self.res_combo),
                       ("Decodificacion de video", self.dec_combo)):
            box = QVBoxLayout()
            box.setSpacing(5)
            box.addWidget(label(cap, "dim"))
            box.addWidget(w)
            holder = QWidget()
            holder.setLayout(box)
            line1.addWidget(holder, 1)
        tl.addLayout(line1)

        self.sync_toggle = TextToggle(self.app.cfg.av_sync, "Sync A/V activa", "Sync A/V apagada")
        self.sync_toggle.setFixedWidth(160)
        tl.addWidget(row(
            self.sync_toggle,
            label("Apagada = menos retardo (gaming). Activada = labios sincronizados (video).",
                  "mute", wrap=True),
        ))

        self.lat_slider = LabeledSlider("Buffer de audio declarado al iPhone", 0, 400,
                                        self.app.cfg.audio_latency_ms, " ms")
        tl.addWidget(self.lat_slider)

        self.sleep_toggle = TextToggle(self.app.cfg.prevent_sleep, "No suspender PC", "Permitir suspension")
        self.sleep_toggle.setFixedWidth(170)
        self.sleep_toggle.changed.connect(self._sleep_changed)
        tl.addWidget(row(self.sleep_toggle,
                         label("Evita que Windows duerma la PC o apague la pantalla mientras transmitis.",
                               "mute", wrap=True)))

        buttons = row(
            self._btn("Aplicar y reconectar", "primary", self.apply_tuning),
            self._btn("Volver al preset Gaming", "neutral", lambda: self.choose_preset("gaming")),
            "stretch",
        )
        tl.addWidget(buttons)
        self.lay.addWidget(card(tune, 1, 20))

        # --- Latencia -------------------------------------------------------
        lat = QWidget()
        ll = QHBoxLayout(lat)
        ll.setContentsMargins(0, 0, 0, 0)
        ll.setSpacing(10)
        self.tile_lat = StatTile("Latencia estimada", "-", " ms")
        self.tile_fps = StatTile("FPS reales", "-")
        self.tile_mode = StatTile("Perfil", "-")
        for t in (self.tile_lat, self.tile_fps, self.tile_mode):
            ll.addWidget(t, 1)
        self.lay.addWidget(lat)

        tips = QWidget()
        tpl = QVBoxLayout(tips)
        tpl.setContentsMargins(0, 0, 0, 0)
        tpl.setSpacing(8)
        for t in [
            "Usa Wi-Fi de 5 GHz y deja el router cerca: el mirroring 1080p60 necesita unos 10-20 Mbps estables.",
            "Conecta la PC por cable de red al router si podes: baja el jitter mas que cualquier ajuste.",
            "En el iPhone, desactiva 'Datos moviles' durante la transmision si el Wi-Fi es debil.",
            "Cerrar apps en segundo plano del iPhone libera CPU para el codificador y sube los FPS.",
            "Si ves tirones, proba el decodificador 'GPU Direct3D11'; si tu GPU es vieja, usa CPU.",
            "El modo Gaming apaga la sincronizacion A/V: el audio puede adelantarse unos milisegundos, es normal.",
        ]:
            tpl.addWidget(label("- " + t, "dim", wrap=True))
        self.lay.addWidget(Collapsible("Consejos para menos lag", tips, opened=False))

        self.sync_controls()

    def _btn(self, text: str, accent: str, slot) -> ActionButton:
        b = ActionButton(text, accent)
        b.clicked.connect(slot)
        return b

    # ------------------------------------------------------------------
    def choose_preset(self, key: str) -> None:
        apply_preset(self.app.cfg, key)
        self.app.save_and_apply(force=True)
        self.sync_controls()
        self.app.toast(f"Preset {PRESETS[key].title} aplicado", "ok")

    def apply_tuning(self) -> None:
        cfg = self.app.cfg
        cfg.fps = FPS_CHOICES[self.fps_combo.currentIndex()]
        cfg.resolution = RESOLUTIONS[self.res_combo.currentIndex()]
        cfg.decoder = DECODERS[self.dec_combo.currentIndex()][0]
        cfg.av_sync = self.sync_toggle.is_on()
        cfg.audio_latency_ms = self.lat_slider.slider.value()
        mark_custom(cfg)
        cfg.validate()
        self.app.save_and_apply(force=True)
        self.sync_controls()
        self.app.toast("Ajustes de gaming aplicados", "ok")

    def _sleep_changed(self, on: bool) -> None:
        self.app.cfg.prevent_sleep = on
        self.app.save_config()
        self.app.apply_power_policy()

    def sync_controls(self) -> None:
        cfg = self.app.cfg
        self.fps_combo.setCurrentIndex(FPS_CHOICES.index(cfg.fps))
        self.res_combo.setCurrentIndex(RESOLUTIONS.index(cfg.resolution))
        keys = [k for k, _ in DECODERS]
        self.dec_combo.setCurrentIndex(keys.index(cfg.decoder) if cfg.decoder in keys else 0)
        self.sync_toggle.set_on(cfg.av_sync)
        self.lat_slider.set_value(cfg.audio_latency_ms)
        self.sleep_toggle.set_on(cfg.prevent_sleep)
        for key, c in self.preset_cards.items():
            c.set_active(cfg.preset == key)
        self.tile_mode.set_value(PRESETS[cfg.preset].title if cfg.preset in PRESETS else "Personalizado")
        self.tile_lat.set_value(str(estimated_latency_ms(cfg)))

    def on_show(self) -> None:
        self.sync_controls()

    def refresh(self) -> None:
        self.sync_controls()

    def update_stats(self, s: dict) -> None:
        fps = s.get("fps")
        self.tile_fps.set_value(f"{fps:.0f}" if fps else "-")
        if s.get("latency_ms"):
            self.tile_lat.set_value(f"{s['latency_ms']:.0f}")
