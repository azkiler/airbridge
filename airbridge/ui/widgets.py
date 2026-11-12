"""Componentes de interfaz de AirBridge.

Todo son TEXTOS: no hay iconos ni glifos en ningun boton.
Las animaciones (hover, cambio de pagina, paneles que se abren/cierran,
toasts, visualizador) se pueden apagar desde Ajustes.
"""
from __future__ import annotations

import math
import time

from PySide6.QtCore import (
    Property, QEasingCurve, QParallelAnimationGroup, QPropertyAnimation,
    QRectF, QSize, Qt, QTimer, QVariantAnimation, Signal,
)
from PySide6.QtGui import QColor, QFont, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import (
    QFrame, QGraphicsOpacityEffect, QHBoxLayout, QLabel, QPushButton,
    QSizePolicy, QSlider, QStackedWidget, QVBoxLayout, QWidget,
)

from . import theme as T

ANIM = True          # se setea desde la configuracion
SPEED = 1.0


def dur(ms: int) -> int:
    return int(ms * SPEED) if ANIM else 0


def lerp(a: str, b: str, t: float) -> QColor:
    ca, cb = QColor(a), QColor(b)
    t = max(0.0, min(1.0, t))
    return QColor(
        int(ca.red() + (cb.red() - ca.red()) * t),
        int(ca.green() + (cb.green() - ca.green()) * t),
        int(ca.blue() + (cb.blue() - ca.blue()) * t),
        int(ca.alpha() + (cb.alpha() - ca.alpha()) * t),
    )


def label(text: str, role: str = "", wrap: bool = False) -> QLabel:
    lb = QLabel(text)
    if role:
        lb.setProperty("role", role)
    if wrap:
        lb.setWordWrap(True)
    return lb


def card(inner: QWidget | None = None, level: int = 1, pad: int = 18) -> QFrame:
    f = QFrame()
    f.setProperty("card", str(level))
    lay = QVBoxLayout(f)
    lay.setContentsMargins(pad, pad, pad, pad)
    lay.setSpacing(12)
    if inner is not None:
        lay.addWidget(inner)
    f.body = lay  # acceso comodo
    return f


def hsep() -> QFrame:
    f = QFrame()
    f.setProperty("sep", "1")
    f.setFixedHeight(1)
    return f


def row(*widgets, spacing: int = 10, stretch_last: bool = False) -> QWidget:
    w = QWidget()
    lay = QHBoxLayout(w)
    lay.setContentsMargins(0, 0, 0, 0)
    lay.setSpacing(spacing)
    for item in widgets:
        if isinstance(item, int):
            lay.addSpacing(item)
        elif item == "stretch":
            lay.addStretch(1)
        else:
            lay.addWidget(item)
    if stretch_last:
        lay.addStretch(1)
    return w


# ----------------------------------------------------------------------
class ActionButton(QPushButton):
    """Boton de texto con transicion de color animada.

    accent: primary (naranja) | violet | neutral | ghost | danger
    """

    def __init__(self, text: str, accent: str = "neutral", small: bool = False, parent=None) -> None:
        super().__init__(text, parent)
        self.accent = accent
        self.small = small
        self._hover = 0.0
        self.setCursor(Qt.PointingHandCursor)
        self.setMinimumHeight(32 if small else 42)
        f = QFont(self.font())
        f.setBold(True)
        f.setPointSizeF(10.0 if small else 11.0)
        self.setFont(f)
        self._anim = QVariantAnimation(self)
        self._anim.setDuration(dur(160))
        self._anim.valueChanged.connect(self._set_hover)
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)

    def _get_hover(self) -> float:
        return self._hover

    def _set_hover(self, v: float) -> None:
        self._hover = float(v)
        self.update()

    hoverAmount = Property(float, _get_hover, _set_hover)

    def _animate(self, to: float) -> None:
        self._anim.stop()
        if not ANIM:
            self._set_hover(to)
            return
        self._anim.setDuration(dur(160))
        self._anim.setStartValue(self._hover)
        self._anim.setEndValue(to)
        self._anim.start()

    def enterEvent(self, e) -> None:
        self._animate(1.0)
        super().enterEvent(e)

    def leaveEvent(self, e) -> None:
        self._animate(0.0)
        super().leaveEvent(e)

    def sizeHint(self) -> QSize:
        base = super().sizeHint()
        return QSize(max(base.width(), 96), 32 if self.small else 42)

    def _palette(self) -> tuple[str, str, str, str, str]:
        if self.accent == "primary":
            return T.ORANGE, T.ORANGE_HOVER, T.ORANGE_PRESS, T.ORANGE_INK, T.ORANGE_HOVER
        if self.accent == "violet":
            return T.VIOLET_DEEP, T.VIOLET_HOVER, "#5B21B6", "#FFFFFF", T.VIOLET
        if self.accent == "danger":
            return "#2A1622", "#3A1C2C", "#22121C", T.ERR, "#4A2334"
        if self.accent == "ghost":
            return "#00000000", T.SURFACE_2, T.SURFACE_3, T.TEXT_DIM, "#00000000"
        return T.SURFACE_2, T.SURFACE_3, "#1A1526", T.TEXT, T.LINE

    def paintEvent(self, _e) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        base, hov, press, ink, border = self._palette()
        enabled = self.isEnabled()
        bg = lerp(base, hov, self._hover)
        if self.isDown():
            bg = QColor(press)
        if not enabled:
            bg = QColor("#14111E")
            ink = T.TEXT_MUTE
            border = "#221C31"
        r = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        path = QPainterPath()
        path.addRoundedRect(r, T.RADIUS_SM, T.RADIUS_SM)
        p.fillPath(path, bg)
        if QColor(border).alpha() > 0 and self.accent != "primary":
            p.setPen(QPen(lerp(border, T.VIOLET, self._hover * 0.5) if self.accent == "neutral" else QColor(border), 1))
            p.drawPath(path)
        p.setPen(QColor(ink if enabled else T.TEXT_MUTE))
        f = QFont(self.font())
        f.setBold(True)
        p.setFont(f)
        p.drawText(self.rect(), Qt.AlignCenter, self.text())
        p.end()


class NavButton(QPushButton):
    """Item de menu lateral: texto + barra violeta animada cuando esta activo."""

    def __init__(self, text: str, parent=None) -> None:
        super().__init__(text, parent)
        self.setCheckable(True)
        self.setCursor(Qt.PointingHandCursor)
        self.setMinimumHeight(44)
        self._active = 0.0
        self._hover = 0.0
        f = QFont(self.font())
        f.setPointSizeF(11.0)
        f.setBold(True)
        self.setFont(f)
        self._a = QVariantAnimation(self)
        self._a.setDuration(dur(200))
        self._a.setEasingCurve(QEasingCurve.OutCubic)
        self._a.valueChanged.connect(self._set_active)
        self._h = QVariantAnimation(self)
        self._h.setDuration(dur(140))
        self._h.valueChanged.connect(self._set_hover)
        self.toggled.connect(self._on_toggle)

    def _get_active(self): return self._active
    def _set_active(self, v): self._active = float(v); self.update()
    activeAmount = Property(float, _get_active, _set_active)

    def _get_hover(self): return self._hover
    def _set_hover(self, v): self._hover = float(v); self.update()
    hoverAmount = Property(float, _get_hover, _set_hover)

    def _on_toggle(self, on: bool) -> None:
        self._a.stop()
        if not ANIM:
            self._set_active(1.0 if on else 0.0)
            return
        self._a.setDuration(dur(220))
        self._a.setStartValue(self._active)
        self._a.setEndValue(1.0 if on else 0.0)
        self._a.start()

    def enterEvent(self, e):
        self._h.stop(); self._h.setDuration(dur(140))
        self._h.setStartValue(self._hover); self._h.setEndValue(1.0); self._h.start()
        super().enterEvent(e)

    def leaveEvent(self, e):
        self._h.stop(); self._h.setDuration(dur(140))
        self._h.setStartValue(self._hover); self._h.setEndValue(0.0); self._h.start()
        super().leaveEvent(e)

    def paintEvent(self, _e) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        r = QRectF(self.rect()).adjusted(0, 2, 0, -2)
        bg = lerp("#00000000", T.SURFACE_2, max(self._hover * 0.8, self._active))
        path = QPainterPath()
        path.addRoundedRect(r, 10, 10)
        p.fillPath(path, bg)
        if self._active > 0.01:
            bar = QRectF(6, r.center().y() - 11 * self._active, 3, 22 * self._active)
            p.fillPath(self._round(bar, 2), QColor(T.VIOLET))
        p.setPen(QColor(lerp(T.TEXT_DIM, T.TEXT, max(self._active, self._hover))))
        f = QFont(self.font()); f.setBold(True); p.setFont(f)
        p.drawText(QRectF(22, 0, self.width() - 30, self.height()), Qt.AlignVCenter | Qt.AlignLeft, self.text())
        p.end()

    @staticmethod
    def _round(r: QRectF, rad: float) -> QPainterPath:
        path = QPainterPath()
        path.addRoundedRect(r, rad, rad)
        return path


class TextToggle(QPushButton):
    """Interruptor de solo texto: 'Activado' / 'Desactivado'."""

    changed = Signal(bool)

    def __init__(self, on: bool = False, on_text: str = "Activado", off_text: str = "Desactivado", parent=None):
        super().__init__(parent)
        self._on = on
        self.on_text, self.off_text = on_text, off_text
        self._t = 1.0 if on else 0.0
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedSize(126, 34)
        f = QFont(self.font()); f.setBold(True); f.setPointSizeF(10.0)
        self.setFont(f)
        self._anim = QVariantAnimation(self)
        self._anim.setDuration(dur(220))
        self._anim.setEasingCurve(QEasingCurve.InOutCubic)
        self._anim.valueChanged.connect(self._set_t)
        self.clicked.connect(self._toggle)
        self.setText(self.on_text if on else self.off_text)

    def _get_t(self): return self._t
    def _set_t(self, v): self._t = float(v); self.update()
    amount = Property(float, _get_t, _set_t)

    def is_on(self) -> bool:
        return self._on

    def set_on(self, on: bool, notify: bool = False) -> None:
        if on == self._on:
            return
        self._on = on
        self.setText(self.on_text if on else self.off_text)
        self._anim.stop()
        if not ANIM:
            self._set_t(1.0 if on else 0.0)
        else:
            self._anim.setDuration(dur(220))
            self._anim.setStartValue(self._t)
            self._anim.setEndValue(1.0 if on else 0.0)
            self._anim.start()
        if notify:
            self.changed.emit(on)

    def _toggle(self) -> None:
        self.set_on(not self._on, notify=True)

    def paintEvent(self, _e) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        r = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        path = QPainterPath(); path.addRoundedRect(r, 17, 17)
        p.fillPath(path, lerp(T.SURFACE_2, T.VIOLET_DEEP, self._t))
        p.setPen(QPen(lerp(T.LINE, T.VIOLET, self._t), 1))
        p.drawPath(path)
        p.setPen(QColor(lerp(T.TEXT_MUTE, "#FFFFFF", self._t)))
        p.setFont(self.font())
        p.drawText(self.rect(), Qt.AlignCenter, self.text())
        p.end()


class Chip(QLabel):
    """Etiqueta de estado redondeada (texto, sin iconos)."""

    def __init__(self, text: str = "", tone: str = "neutral", parent=None) -> None:
        super().__init__(text, parent)
        self.tone = tone
        self._pulse = 0.0
        f = QFont(self.font()); f.setBold(True); f.setPointSizeF(9.5)
        self.setFont(f)
        self.setMinimumHeight(28)
        self.setAlignment(Qt.AlignCenter)
        self._timer = QTimer(self)
        self._timer.setInterval(60)
        self._timer.timeout.connect(self._tick)
        self._t0 = time.time()

    def set_tone(self, tone: str) -> None:
        self.tone = tone
        if tone == "live" and ANIM:
            self._timer.start()
        else:
            self._timer.stop()
            self._pulse = 0.0
        self.update()

    def _tick(self) -> None:
        self._pulse = (math.sin((time.time() - self._t0) * 3.0) + 1) / 2
        self.update()

    def sizeHint(self) -> QSize:
        w = self.fontMetrics().horizontalAdvance(self.text()) + 26
        return QSize(w, 28)

    def paintEvent(self, _e) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        tones = {
            "neutral": (T.SURFACE_2, T.TEXT_DIM, T.LINE),
            "ok": ("#122A22", T.OK, "#1E4536"),
            "warn": ("#2C2416", T.WARN, "#4A3C22"),
            "err": ("#2C1620", T.ERR, "#4A2333"),
            "violet": ("#1E1636", T.VIOLET_SOFT, T.VIOLET_DEEP),
            "live": ("#2A1408", T.ORANGE, T.ORANGE_PRESS),
        }
        bg, fg, border = tones.get(self.tone, tones["neutral"])
        r = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        path = QPainterPath(); path.addRoundedRect(r, 14, 14)
        p.fillPath(path, QColor(bg))
        bcol = QColor(border)
        if self.tone == "live":
            bcol = lerp(border, T.ORANGE, self._pulse)
        p.setPen(QPen(bcol, 1))
        p.drawPath(path)
        p.setPen(QColor(fg))
        p.setFont(self.font())
        p.drawText(self.rect(), Qt.AlignCenter, self.text())
        p.end()


class Collapsible(QWidget):
    """Panel extraible/contraible con animacion de altura."""

    def __init__(self, title: str, content: QWidget, opened: bool = False, parent=None) -> None:
        super().__init__(parent)
        self._open = opened
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        head = QWidget()
        hl = QHBoxLayout(head)
        hl.setContentsMargins(16, 12, 12, 12)
        hl.setSpacing(10)
        self.title_label = label(title, "h3")
        self.btn = ActionButton("Cerrar" if opened else "Abrir", "ghost", small=True)
        self.btn.setFixedWidth(88)
        self.btn.clicked.connect(self.toggle)
        hl.addWidget(self.title_label, 1)
        hl.addWidget(self.btn, 0)

        self.head = head
        self.body = content
        self.body.setParent(self)
        wrapper = QFrame()
        wrapper.setProperty("card", "1")
        wl = QVBoxLayout(wrapper)
        wl.setContentsMargins(0, 0, 0, 0)
        wl.setSpacing(0)
        wl.addWidget(head)
        self.inner = QWidget()
        il = QVBoxLayout(self.inner)
        il.setContentsMargins(16, 4, 16, 16)
        il.addWidget(self.body)
        wl.addWidget(self.inner)
        lay.addWidget(wrapper)

        self.inner.setMaximumHeight(16777215 if opened else 0)
        self.inner.setVisible(opened)
        self._anim = QPropertyAnimation(self.inner, b"maximumHeight", self)
        self._anim.setDuration(dur(240))
        self._anim.setEasingCurve(QEasingCurve.InOutCubic)
        self._anim.finished.connect(self._done)

    def toggle(self) -> None:
        self.set_open(not self._open)

    def set_open(self, opened: bool) -> None:
        if opened == self._open:
            return
        self._open = opened
        self.btn.setText("Cerrar" if opened else "Abrir")
        target = self.inner.sizeHint().height() if opened else 0
        self.inner.setVisible(True)
        self._anim.stop()
        if not ANIM:
            self.inner.setMaximumHeight(target if opened else 0)
            self._done()
            return
        self._anim.setDuration(dur(240))
        self._anim.setStartValue(self.inner.maximumHeight() if self.inner.maximumHeight() < 16777215 else self.inner.height())
        self._anim.setEndValue(target)
        self._anim.start()

    def _done(self) -> None:
        if self._open:
            self.inner.setMaximumHeight(16777215)
        else:
            self.inner.setVisible(False)


class StatTile(QFrame):
    def __init__(self, caption: str, value: str = "-", suffix: str = "", parent=None) -> None:
        super().__init__(parent)
        self.setProperty("card", "2")
        lay = QVBoxLayout(self)
        lay.setContentsMargins(14, 12, 14, 12)
        lay.setSpacing(3)
        self.cap = label(caption.upper(), "kicker")
        self.val = label(value, "value")
        self.suffix = suffix
        lay.addWidget(self.cap)
        lay.addWidget(self.val)
        self.setMinimumWidth(120)

    def set_value(self, v: str) -> None:
        text = f"{v}{self.suffix}" if v not in ("", "-") else "-"
        if self.val.text() != text:
            self.val.setText(text)


class LabeledSlider(QWidget):
    valueChanged = Signal(int)

    def __init__(self, title: str, minimum: int, maximum: int, value: int, unit: str = "", parent=None) -> None:
        super().__init__(parent)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(6)
        self.title = label(title, "dim")
        self.readout = label(f"{value}{unit}", "accent")
        self.unit = unit
        top = row(self.title, "stretch", self.readout)
        self.slider = QSlider(Qt.Horizontal)
        self.slider.setRange(minimum, maximum)
        self.slider.setValue(value)
        self.slider.valueChanged.connect(self._changed)
        lay.addWidget(top)
        lay.addWidget(self.slider)

    def _changed(self, v: int) -> None:
        self.readout.setText(f"{v}{self.unit}")
        self.valueChanged.emit(v)

    def set_value(self, v: int) -> None:
        self.slider.blockSignals(True)
        self.slider.setValue(v)
        self.slider.blockSignals(False)
        self.readout.setText(f"{v}{self.unit}")


class Toast(QFrame):
    def __init__(self, text: str, level: str = "ok", parent=None) -> None:
        super().__init__(parent)
        colors = {"ok": (T.OK, "#12261F"), "warn": (T.WARN, "#2A2314"),
                  "error": (T.ERR, "#2A1420"), "info": (T.VIOLET_SOFT, "#1C1630")}
        fg, bg = colors.get(level, colors["info"])
        self.setStyleSheet(
            f"Toast {{ background: {bg}; border: 1px solid {fg}; border-radius: 10px; }}"
        )
        lay = QHBoxLayout(self)
        lay.setContentsMargins(14, 11, 14, 11)
        lb = label(text)
        lb.setStyleSheet(f"color: {fg}; font-weight: 600;")
        lb.setWordWrap(True)
        lay.addWidget(lb)
        self.setMaximumWidth(420)
        self._eff = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self._eff)
        self._eff.setOpacity(0.0)

    def show_animated(self) -> None:
        self._fade = QPropertyAnimation(self._eff, b"opacity", self)
        self._fade.setDuration(dur(200))
        self._fade.setStartValue(0.0)
        self._fade.setEndValue(1.0)
        self._slide = QPropertyAnimation(self, b"pos", self)
        self._slide.setDuration(dur(240))
        self._slide.setEasingCurve(QEasingCurve.OutCubic)
        target = self.pos()
        self._slide.setStartValue(target + type(target)(0, 16))
        self._slide.setEndValue(target)
        self._grp = QParallelAnimationGroup(self)
        self._grp.addAnimation(self._fade)
        self._grp.addAnimation(self._slide)
        self._grp.start()
        QTimer.singleShot(3600, self.hide_animated)

    def hide_animated(self) -> None:
        self._out = QPropertyAnimation(self._eff, b"opacity", self)
        self._out.setDuration(dur(220))
        self._out.setStartValue(self._eff.opacity())
        self._out.setEndValue(0.0)
        self._out.finished.connect(self.deleteLater)
        self._out.start()


class ToastHost(QWidget):
    """Pila de avisos abajo a la derecha."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setAttribute(Qt.WA_TransparentForMouseEvents, False)
        self.lay = QVBoxLayout(self)
        self.lay.setContentsMargins(0, 0, 18, 18)
        self.lay.setSpacing(8)
        self.lay.addStretch(1)
        self.setAttribute(Qt.WA_NoSystemBackground, True)

    def push(self, text: str, level: str = "ok") -> None:
        t = Toast(text, level, self)
        self.lay.addWidget(t, 0, Qt.AlignRight)
        t.show()
        QTimer.singleShot(0, t.show_animated)


class AnimatedStack(QStackedWidget):
    """Cambio de pantalla con deslizamiento + fundido."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._grp: QParallelAnimationGroup | None = None
        self._overlay: QLabel | None = None

    def goto(self, index: int) -> None:
        if index == self.currentIndex() or index < 0 or index >= self.count():
            return
        old = self.currentWidget()
        if not ANIM or old is None:
            self.setCurrentIndex(index)
            return
        pix = old.grab()
        overlay = QLabel(self)
        overlay.setPixmap(pix)
        overlay.setGeometry(old.geometry())
        overlay.show()
        eff = QGraphicsOpacityEffect(overlay)
        overlay.setGraphicsEffect(eff)

        self.setCurrentIndex(index)
        new = self.currentWidget()
        target = new.pos()
        new.move(target.x() + 26, target.y())
        new_eff = QGraphicsOpacityEffect(new)
        new.setGraphicsEffect(new_eff)
        new_eff.setOpacity(0.0)

        fade_old = QPropertyAnimation(eff, b"opacity", self)
        fade_old.setDuration(dur(190))
        fade_old.setStartValue(1.0)
        fade_old.setEndValue(0.0)

        slide = QPropertyAnimation(new, b"pos", self)
        slide.setDuration(dur(280))
        slide.setEasingCurve(QEasingCurve.OutCubic)
        slide.setStartValue(new.pos())
        slide.setEndValue(target)

        fade_new = QPropertyAnimation(new_eff, b"opacity", self)
        fade_new.setDuration(dur(240))
        fade_new.setStartValue(0.0)
        fade_new.setEndValue(1.0)

        grp = QParallelAnimationGroup(self)
        grp.addAnimation(fade_old)
        grp.addAnimation(slide)
        grp.addAnimation(fade_new)

        def cleanup() -> None:
            overlay.deleteLater()
            new.setGraphicsEffect(None)
            new.move(target)

        grp.finished.connect(cleanup)
        self._grp = grp
        grp.start()


class Visualizer(QWidget):
    """Barras de audio (reaccionan al pico real del dispositivo si hay pycaw)."""

    def __init__(self, bars: int = 42, parent=None) -> None:
        super().__init__(parent)
        self.bars = bars
        self.level = 0.0
        self.active = False
        self._phase = 0.0
        self._heights = [0.06] * bars
        self.setMinimumHeight(96)
        self._timer = QTimer(self)
        self._timer.setInterval(45)
        self._timer.timeout.connect(self._tick)
        self._timer.start()

    def set_level(self, level: float, active: bool) -> None:
        self.level = max(0.0, min(1.0, level))
        self.active = active

    def _tick(self) -> None:
        if not ANIM:
            return
        self._phase += 0.16
        for i in range(self.bars):
            if self.active:
                wave = (math.sin(self._phase + i * 0.42) + 1) / 2
                target = 0.10 + self.level * (0.35 + 0.65 * wave)
            else:
                target = 0.05 + 0.02 * ((math.sin(self._phase * 0.4 + i * 0.3) + 1) / 2)
            self._heights[i] += (target - self._heights[i]) * 0.25
        self.update()

    def paintEvent(self, _e) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        w, h = self.width(), self.height()
        gap = 4
        bw = max(2.0, (w - gap * (self.bars - 1)) / self.bars)
        segments = 5
        for i, val in enumerate(self._heights):
            bh = max(3.0, val * h)
            x = i * (bw + gap)
            y = h - bh
            path = QPainterPath()
            path.addRoundedRect(QRectF(x, y, bw, bh), 2, 2)
            p.save()
            p.setClipPath(path)
            seg_h = bh / segments
            for k in range(segments):
                t = k / (segments - 1)
                col = lerp(T.ORANGE, T.VIOLET_DEEP, t) if self.active else lerp("#2E2740", "#1C1729", t)
                p.fillRect(QRectF(x, y + k * seg_h, bw, seg_h + 0.8), col)
            p.restore()
        p.end()


class VideoSurface(QWidget):
    """Area donde se incrusta el video nativo del motor (o el placeholder)."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setAttribute(Qt.WA_NativeWindow, True)
        self.setAttribute(Qt.WA_OpaquePaintEvent, True)
        self.setMinimumSize(320, 180)
        self.hwnd = 0
        self.demo = False
        self.title = "Esperando transmision"
        self.subtitle = "En el iPhone: Centro de control  >  Duplicar pantalla  >  AirBridge"
        self._t0 = time.time()
        self._timer = QTimer(self)
        self._timer.setInterval(50)
        self._timer.timeout.connect(self.update)
        self._timer.start()

    def set_embedded(self, hwnd: int) -> None:
        self.hwnd = hwnd
        self.update()

    def set_texts(self, title: str, subtitle: str) -> None:
        self.title, self.subtitle = title, subtitle
        self.update()

    def paintEvent(self, _e) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        r = QRectF(self.rect())
        p.fillRect(self.rect(), QColor("#05040A"))
        if self.hwnd:
            p.end()
            return
        t = time.time() - self._t0
        if self.demo:
            self._paint_demo(p, r, t)
        else:
            p.fillRect(self.rect(), QColor("#0B0814"))
            # Halo violeta suave que respira (sin degradados: mas rapido y estable)
            shift = (math.sin(t * 0.5) + 1) / 2
            for k in range(6):
                col = QColor(T.VIOLET_DEEP)
                col.setAlpha(9)
                inset = 40 + k * 26 - shift * 18
                p.fillPath(self._rr(r.adjusted(inset, inset * 0.5, -inset, -inset * 0.5), 18), col)
            p.setPen(QColor(T.TEXT))
            f = QFont(self.font()); f.setPointSizeF(15); f.setBold(True); p.setFont(f)
            p.drawText(QRectF(0, r.height() / 2 - 42, r.width(), 30), Qt.AlignCenter, self.title)
            p.setPen(QColor(T.TEXT_MUTE))
            f2 = QFont(self.font()); f2.setPointSizeF(10.5); f2.setBold(False); p.setFont(f2)
            p.drawText(QRectF(20, r.height() / 2 - 6, r.width() - 40, 40),
                       Qt.AlignCenter | Qt.TextWordWrap, self.subtitle)
        p.setPen(QPen(QColor(T.LINE), 1))
        p.drawRoundedRect(r.adjusted(0.5, 0.5, -0.5, -0.5), 12, 12)
        p.end()

    def _paint_demo(self, p: QPainter, r: QRectF, t: float) -> None:
        """Patron de prueba animado para recorrer la app sin iPhone."""
        colors = ["#FF7A2F", "#8B5CF6", "#3DDC97", "#FFC857", "#4C7DFF", "#FF6B8A", "#E9E4F5"]
        bw = r.width() / len(colors)
        for i, c in enumerate(colors):
            col = QColor(c)
            col.setAlpha(70)
            p.fillRect(QRectF(i * bw, 0, bw, r.height() * 0.62), col)
        p.fillRect(QRectF(0, r.height() * 0.62, r.width(), r.height() * 0.38), QColor("#0C0916"))
        x = (math.sin(t * 0.9) * 0.5 + 0.5) * (r.width() - 120) + 20
        p.fillPath(self._rr(QRectF(x, r.height() * 0.66, 100, 44), 10), QColor(T.ORANGE))
        p.setPen(QColor(T.ORANGE_INK))
        f = QFont(self.font()); f.setBold(True); f.setPointSizeF(10); p.setFont(f)
        p.drawText(QRectF(x, r.height() * 0.66, 100, 44), Qt.AlignCenter, "60 FPS")
        p.setPen(QColor(T.TEXT))
        f2 = QFont(self.font()); f2.setPointSizeF(13); f2.setBold(True); p.setFont(f2)
        p.drawText(QRectF(0, r.height() * 0.2, r.width(), 30), Qt.AlignCenter, "MODO DEMO - SIN IPHONE CONECTADO")
        p.setPen(QColor(T.TEXT_DIM))
        f3 = QFont(self.font()); f3.setPointSizeF(10); f3.setBold(False); p.setFont(f3)
        p.drawText(QRectF(0, r.height() * 0.2 + 30, r.width(), 24), Qt.AlignCenter,
                   time.strftime("Origen simulado  %H:%M:%S"))

    @staticmethod
    def _rr(rect: QRectF, rad: float) -> QPainterPath:
        path = QPainterPath()
        path.addRoundedRect(rect, rad, rad)
        return path
