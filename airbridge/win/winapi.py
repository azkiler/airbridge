"""Capa Win32 pura (ctypes). En otros sistemas todo degrada a no-ops.

Aca vive lo que hace que la ventana quede REALMENTE arriba de todo en
Windows 11, que el video del motor se incruste en la app y que la PC no se
duerma mientras estas transmitiendo.
"""
from __future__ import annotations

import sys
from dataclasses import dataclass

IS_WINDOWS = sys.platform.startswith("win")

if IS_WINDOWS:  # pragma: no cover - solo se ejecuta en Windows
    import ctypes
    from ctypes import wintypes

    user32 = ctypes.WinDLL("user32", use_last_error=True)
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    dwmapi = ctypes.WinDLL("dwmapi", use_last_error=True)

    HWND_TOPMOST = -1
    HWND_NOTOPMOST = -2
    SWP_NOSIZE = 0x0001
    SWP_NOMOVE = 0x0002
    SWP_NOZORDER = 0x0004
    SWP_NOACTIVATE = 0x0010
    SWP_NOOWNERZORDER = 0x0200
    SWP_SHOWWINDOW = 0x0040
    SWP_ASYNCWINDOWPOS = 0x4000

    GWL_STYLE = -16
    GWL_EXSTYLE = -20
    WS_CAPTION = 0x00C00000
    WS_THICKFRAME = 0x00040000
    WS_BORDER = 0x00800000
    WS_DLGFRAME = 0x00400000
    WS_POPUP = 0x80000000
    WS_CHILD = 0x40000000
    WS_VISIBLE = 0x10000000
    WS_SYSMENU = 0x00080000
    WS_MINIMIZEBOX = 0x00020000
    WS_MAXIMIZEBOX = 0x00010000
    WS_EX_TOPMOST = 0x00000008
    WS_EX_APPWINDOW = 0x00040000
    WS_EX_TOOLWINDOW = 0x00000080

    SW_SHOW = 5
    SW_RESTORE = 9

    user32.SetWindowPos.argtypes = [
        wintypes.HWND, wintypes.HWND, ctypes.c_int, ctypes.c_int,
        ctypes.c_int, ctypes.c_int, wintypes.UINT,
    ]
    user32.SetWindowPos.restype = wintypes.BOOL
    user32.GetWindowLongW.argtypes = [wintypes.HWND, ctypes.c_int]
    user32.GetWindowLongW.restype = ctypes.c_long
    user32.SetWindowLongW.argtypes = [wintypes.HWND, ctypes.c_int, ctypes.c_long]
    user32.SetWindowLongW.restype = ctypes.c_long
    user32.SetParent.argtypes = [wintypes.HWND, wintypes.HWND]
    user32.SetParent.restype = wintypes.HWND
    user32.MoveWindow.argtypes = [wintypes.HWND, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int, wintypes.BOOL]
    user32.GetClientRect.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.RECT)]
    user32.GetWindowRect.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.RECT)]
    user32.IsWindowVisible.argtypes = [wintypes.HWND]
    user32.IsWindow.argtypes = [wintypes.HWND]
    user32.GetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
    user32.GetClassNameW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
    user32.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
    user32.ShowWindow.argtypes = [wintypes.HWND, ctypes.c_int]

    WNDENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    user32.EnumWindows.argtypes = [WNDENUMPROC, wintypes.LPARAM]

    ES_CONTINUOUS = 0x80000000
    ES_SYSTEM_REQUIRED = 0x00000001
    ES_DISPLAY_REQUIRED = 0x00000002
    kernel32.SetThreadExecutionState.argtypes = [wintypes.UINT]
    kernel32.SetThreadExecutionState.restype = wintypes.UINT


@dataclass
class WinInfo:
    hwnd: int
    title: str
    cls: str
    x: int
    y: int
    w: int
    h: int
    visible: bool

    @property
    def area(self) -> int:
        return max(0, self.w) * max(0, self.h)


def hwnd_of(widget) -> int:
    """HWND de un QWidget (0 si no estamos en Windows)."""
    if not IS_WINDOWS or widget is None:
        return 0
    try:
        return int(widget.winId())
    except Exception:
        return 0


def set_topmost(hwnd: int, on: bool = True) -> None:
    if not IS_WINDOWS or not hwnd:
        return
    user32.SetWindowPos(
        wintypes.HWND(hwnd), wintypes.HWND(HWND_TOPMOST if on else HWND_NOTOPMOST),
        0, 0, 0, 0,
        SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE | SWP_NOOWNERZORDER | SWP_ASYNCWINDOWPOS,
    )


def is_topmost(hwnd: int) -> bool:
    if not IS_WINDOWS or not hwnd:
        return False
    return bool(user32.GetWindowLongW(wintypes.HWND(hwnd), GWL_EXSTYLE) & WS_EX_TOPMOST)


def raise_without_focus(hwnd: int) -> None:
    """Vuelve al frente SIN robar el foco (clave para no molestar mientras jugas)."""
    if not IS_WINDOWS or not hwnd:
        return
    user32.SetWindowPos(
        wintypes.HWND(hwnd), wintypes.HWND(HWND_TOPMOST), 0, 0, 0, 0,
        SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE | SWP_ASYNCWINDOWPOS,
    )


def list_process_windows(pid: int) -> list[WinInfo]:
    """Todas las ventanas top-level de un proceso."""
    if not IS_WINDOWS or not pid:
        return []
    out: list[WinInfo] = []

    @WNDENUMPROC
    def _cb(hwnd, _lparam):
        proc = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(proc))
        if proc.value == pid:
            tbuf = ctypes.create_unicode_buffer(512)
            cbuf = ctypes.create_unicode_buffer(256)
            user32.GetWindowTextW(hwnd, tbuf, 512)
            user32.GetClassNameW(hwnd, cbuf, 256)
            r = wintypes.RECT()
            user32.GetWindowRect(hwnd, ctypes.byref(r))
            out.append(WinInfo(
                hwnd=int(hwnd), title=tbuf.value, cls=cbuf.value,
                x=r.left, y=r.top, w=r.right - r.left, h=r.bottom - r.top,
                visible=bool(user32.IsWindowVisible(hwnd)),
            ))
        return True

    user32.EnumWindows(_cb, 0)
    return out


def is_window(hwnd: int) -> bool:
    return bool(IS_WINDOWS and hwnd and user32.IsWindow(wintypes.HWND(hwnd)))


def client_size(hwnd: int) -> tuple[int, int]:
    if not IS_WINDOWS or not hwnd:
        return (0, 0)
    r = wintypes.RECT()
    user32.GetClientRect(wintypes.HWND(hwnd), ctypes.byref(r))
    return (r.right - r.left, r.bottom - r.top)


def embed(child: int, parent: int) -> bool:
    """Mete la ventana de video del motor dentro de un widget de la app."""
    if not IS_WINDOWS or not child or not parent:
        return False
    style = user32.GetWindowLongW(wintypes.HWND(child), GWL_STYLE)
    style &= ~(WS_CAPTION | WS_THICKFRAME | WS_BORDER | WS_DLGFRAME | WS_POPUP |
               WS_SYSMENU | WS_MINIMIZEBOX | WS_MAXIMIZEBOX)
    style |= WS_CHILD | WS_VISIBLE
    user32.SetWindowLongW(wintypes.HWND(child), GWL_STYLE, style)
    ex = user32.GetWindowLongW(wintypes.HWND(child), GWL_EXSTYLE)
    ex &= ~(WS_EX_TOPMOST | WS_EX_APPWINDOW)
    user32.SetWindowLongW(wintypes.HWND(child), GWL_EXSTYLE, ex)
    user32.SetParent(wintypes.HWND(child), wintypes.HWND(parent))
    user32.ShowWindow(wintypes.HWND(child), SW_SHOW)
    return True


def unembed(child: int, style_backup: int | None = None, ex_backup: int | None = None) -> bool:
    if not IS_WINDOWS or not child:
        return False
    user32.SetParent(wintypes.HWND(child), None)
    if style_backup is not None:
        user32.SetWindowLongW(wintypes.HWND(child), GWL_STYLE, style_backup)
    else:
        style = user32.GetWindowLongW(wintypes.HWND(child), GWL_STYLE)
        style &= ~WS_CHILD
        style |= WS_POPUP | WS_VISIBLE
        user32.SetWindowLongW(wintypes.HWND(child), GWL_STYLE, style)
    if ex_backup is not None:
        user32.SetWindowLongW(wintypes.HWND(child), GWL_EXSTYLE, ex_backup)
    user32.ShowWindow(wintypes.HWND(child), SW_RESTORE)
    return True


def get_style(hwnd: int) -> int:
    return int(user32.GetWindowLongW(wintypes.HWND(hwnd), GWL_STYLE)) if IS_WINDOWS and hwnd else 0


def get_ex_style(hwnd: int) -> int:
    return int(user32.GetWindowLongW(wintypes.HWND(hwnd), GWL_EXSTYLE)) if IS_WINDOWS and hwnd else 0


def strip_frame(hwnd: int) -> None:
    """Le saca el borde/titulo a la ventana flotante del motor."""
    if not IS_WINDOWS or not hwnd:
        return
    style = user32.GetWindowLongW(wintypes.HWND(hwnd), GWL_STYLE)
    style &= ~(WS_CAPTION | WS_THICKFRAME | WS_BORDER | WS_DLGFRAME)
    user32.SetWindowLongW(wintypes.HWND(hwnd), GWL_STYLE, style)


def move_resize(hwnd: int, x: int, y: int, w: int, h: int) -> None:
    if not IS_WINDOWS or not hwnd:
        return
    user32.MoveWindow(wintypes.HWND(hwnd), int(x), int(y), max(1, int(w)), max(1, int(h)), True)


def show_window(hwnd: int, show: bool = True) -> None:
    if not IS_WINDOWS or not hwnd:
        return
    user32.ShowWindow(wintypes.HWND(hwnd), SW_SHOW if show else 0)


def set_dark_frame(hwnd: int, dark: bool = True, rounded: bool = True) -> None:
    """Barra de titulo oscura + esquinas redondeadas al estilo Windows 11."""
    if not IS_WINDOWS or not hwnd:
        return
    for attr in (20, 19):  # DWMWA_USE_IMMERSIVE_DARK_MODE (build nuevo / viejo)
        val = ctypes.c_int(1 if dark else 0)
        dwmapi.DwmSetWindowAttribute(wintypes.HWND(hwnd), attr, ctypes.byref(val), ctypes.sizeof(val))
    if rounded:
        val = ctypes.c_int(2)  # DWMWCP_ROUND
        dwmapi.DwmSetWindowAttribute(wintypes.HWND(hwnd), 33, ctypes.byref(val), ctypes.sizeof(val))


def keep_awake(system: bool = True, display: bool = True) -> None:
    """Evita suspension y apagado de pantalla mientras hay transmision."""
    if not IS_WINDOWS:
        return
    flags = ES_CONTINUOUS
    if system:
        flags |= ES_SYSTEM_REQUIRED
    if display:
        flags |= ES_DISPLAY_REQUIRED
    kernel32.SetThreadExecutionState(flags)


def allow_sleep() -> None:
    if not IS_WINDOWS:
        return
    kernel32.SetThreadExecutionState(ES_CONTINUOUS)
