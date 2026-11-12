"""Rutas de datos de la aplicacion (multiplataforma, pensada para Windows 11)."""
from __future__ import annotations

import os
import sys
from pathlib import Path

APP = "AirBridge"


def is_windows() -> bool:
    return sys.platform.startswith("win")


def app_dir() -> Path:
    """Carpeta donde vive el codigo / el .exe (solo lectura en general)."""
    if getattr(sys, "frozen", False):  # PyInstaller
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent


def data_dir() -> Path:
    """Configuracion persistente del usuario."""
    if is_windows():
        base = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
    else:
        base = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    p = base / APP
    p.mkdir(parents=True, exist_ok=True)
    return p


def local_dir() -> Path:
    """Datos grandes / temporales (motor AirPlay, logs, caratulas)."""
    if is_windows():
        base = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
    else:
        base = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))
    p = base / APP
    p.mkdir(parents=True, exist_ok=True)
    return p


def config_file() -> Path:
    return data_dir() / "config.json"


def engine_dir() -> Path:
    p = local_dir() / "engine"
    p.mkdir(parents=True, exist_ok=True)
    return p


def logs_dir() -> Path:
    p = local_dir() / "logs"
    p.mkdir(parents=True, exist_ok=True)
    return p


def media_dir() -> Path:
    """Aca el motor escribe metadatos y caratula del modo Musica."""
    p = local_dir() / "media"
    p.mkdir(parents=True, exist_ok=True)
    return p


def metadata_file() -> Path:
    return media_dir() / "metadata.txt"


def coverart_file() -> Path:
    return media_dir() / "coverart.img"


def key_file() -> Path:
    """Clave privada persistente: el iPhone reconoce siempre al mismo receptor."""
    return data_dir() / "airbridge.pem"


def uxplay_windows_args_file() -> Path:
    """Archivo de argumentos que lee el motor uxplay-windows (Qt AppDataLocation)."""
    if is_windows():
        base = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
        return base / "leapbtw" / "uxplay-windows" / "arguments.txt"
    return data_dir() / "dev-arguments.txt"


def uxplay_windows_machine_args_file() -> Path:
    if is_windows():
        base = Path(os.environ.get("ProgramData", r"C:\ProgramData"))
        return base / "uxplay-windows" / "arguments.txt"
    return data_dir() / "dev-machine-arguments.txt"


def uxplay_windows_log_dir() -> Path:
    """El motor escribe su log de sesion aca (QStandardPaths GenericDataLocation)."""
    if is_windows():
        base = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
        return base / "uxplay-windows" / "logs"
    return local_dir() / "dev-engine-logs"
