"""Incrustacion y anclado de la ventana de video del motor.

El motor renderiza con GStreamer + Direct3D11 en su propia ventana nativa.
Windows permite re-parentar ese HWND dentro de un widget nuestro (SetParent),
que es lo que hace que el video se vea DENTRO de AirBridge, con nuestra
interfaz alrededor, y que quede fijo arriba de todo.
"""
from __future__ import annotations

from dataclasses import dataclass

from . import winapi

# Titulos/clases tipicas de la ventana de video segun el sink elegido.
VIDEO_HINTS = ("direct3d11 renderer", "direct3d12 renderer", "renderer", "uxplay", "video")
IGNORE_CLASSES = ("Qt6", "Qt5", "Shell_TrayWnd", "IME", "MSCTFIME UI")


@dataclass
class WindowBackup:
    hwnd: int
    style: int
    ex_style: int


class VideoWindow:
    def __init__(self) -> None:
        self.hwnd: int = 0
        self.pid: int = 0
        self.embedded: bool = False
        self.floating: bool = False
        self._backup: WindowBackup | None = None

    # ------------------------------------------------------------------
    def find(self, pid: int) -> int:
        """Busca la ventana de video del proceso del motor."""
        if not winapi.IS_WINDOWS or not pid:
            return 0
        best, best_score = 0, 0
        for w in winapi.list_process_windows(pid):
            if not w.visible or w.area < 60_000:
                continue
            if any(w.cls.startswith(p) for p in IGNORE_CLASSES):
                continue
            title = w.title.lower()
            score = w.area
            if any(h in title for h in VIDEO_HINTS):
                score *= 4
            if "uxplay-windows" == title:      # ventana de control del motor
                continue
            if score > best_score:
                best, best_score = w.hwnd, score
        self.hwnd = best
        self.pid = pid
        return best

    def alive(self) -> bool:
        return winapi.is_window(self.hwnd)

    # ------------------------------------------------------------------
    def attach(self, parent_hwnd: int) -> bool:
        if not self.hwnd or not parent_hwnd:
            return False
        if self._backup is None:
            self._backup = WindowBackup(self.hwnd, winapi.get_style(self.hwnd), winapi.get_ex_style(self.hwnd))
        ok = winapi.embed(self.hwnd, parent_hwnd)
        self.embedded = ok
        self.floating = False
        return ok

    def layout(self, x: int, y: int, w: int, h: int) -> None:
        if self.hwnd:
            winapi.move_resize(self.hwnd, x, y, w, h)

    def detach(self) -> None:
        if not self.hwnd:
            return
        b = self._backup
        winapi.unembed(self.hwnd, b.style if b else None, b.ex_style if b else None)
        self.embedded = False
        self._backup = None

    def make_floating(self, topmost: bool = True) -> None:
        if not self.hwnd:
            return
        if self.embedded:
            self.detach()
        winapi.strip_frame(self.hwnd)
        winapi.set_topmost(self.hwnd, topmost)
        self.floating = True

    def keep_on_top(self, on: bool = True) -> None:
        if self.hwnd and not self.embedded:
            winapi.set_topmost(self.hwnd, on)

    def reset(self) -> None:
        if self.embedded:
            self.detach()
        self.hwnd = 0
        self.pid = 0
        self.floating = False
