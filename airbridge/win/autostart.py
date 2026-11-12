"""Inicio automatico con Windows (sin permisos de administrador).

Usamos HKCU\\...\\Run, que es la forma soportada y no requiere UAC.
Ademas limpiamos el arranque propio del motor para que no se abran dos
receptores AirPlay peleandose por el mismo puerto.
"""
from __future__ import annotations

import sys
from pathlib import Path

from .winapi import IS_WINDOWS

RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
VALUE_NAME = "AirBridge"
ENGINE_VALUE_NAME = "uxplay-windows"


def _command() -> str:
    if getattr(sys, "frozen", False):
        return f'"{sys.executable}" --autostart'
    pythonw = Path(sys.executable).with_name("pythonw.exe")
    interp = str(pythonw) if pythonw.exists() else sys.executable
    entry = Path(__file__).resolve().parent.parent.parent / "run.py"
    return f'"{interp}" "{entry}" --autostart'


def is_enabled() -> bool:
    if not IS_WINDOWS:
        return False
    import winreg
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY) as k:
            winreg.QueryValueEx(k, VALUE_NAME)
            return True
    except OSError:
        return False


def enable() -> bool:
    if not IS_WINDOWS:
        return False
    import winreg
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, RUN_KEY) as k:
        winreg.SetValueEx(k, VALUE_NAME, 0, winreg.REG_SZ, _command())
    disable_engine_autostart()
    return True


def disable() -> bool:
    if not IS_WINDOWS:
        return False
    import winreg
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_SET_VALUE) as k:
            winreg.DeleteValue(k, VALUE_NAME)
    except OSError:
        pass
    return True


def disable_engine_autostart() -> None:
    """El motor trae su propio autoarranque: lo apagamos, arranca AirBridge."""
    if not IS_WINDOWS:
        return
    import winreg
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_SET_VALUE) as k:
            winreg.DeleteValue(k, ENGINE_VALUE_NAME)
    except OSError:
        pass


def apply(wanted: bool) -> bool:
    return enable() if wanted else disable()
