"""Informacion de red para la pantalla de Inicio y el diagnostico."""
from __future__ import annotations

import re
import socket
import subprocess

from ..win.winapi import IS_WINDOWS


def local_ip() -> str:
    """IP local con la que el iPhone va a hablar con esta PC."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))  # no manda paquetes, solo elige la interfaz
        return s.getsockname()[0]
    except OSError:
        try:
            return socket.gethostbyname(socket.gethostname())
        except OSError:
            return "127.0.0.1"
    finally:
        s.close()


def hostname() -> str:
    return socket.gethostname()


def wifi_info() -> dict:
    """SSID / senal / banda de la interfaz Wi-Fi (solo Windows)."""
    info = {"connected": False, "ssid": "", "signal": "", "band": "", "radio": ""}
    if not IS_WINDOWS:
        return info
    try:
        out = subprocess.run(
            ["netsh", "wlan", "show", "interfaces"], capture_output=True, text=True,
            timeout=10, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        ).stdout
    except Exception:
        return info
    for line in out.splitlines():
        if ":" not in line:
            continue
        key, val = [p.strip() for p in line.split(":", 1)]
        k = key.lower()
        if k == "ssid":
            info["ssid"] = val
            info["connected"] = bool(val)
        elif k in ("signal", "señal"):
            info["signal"] = val
        elif k in ("band", "banda"):
            info["band"] = val
        elif k in ("radio type", "tipo de radio"):
            info["radio"] = val
    return info


def bonjour_service_running() -> bool:
    """El servicio Bonjour (mDNSResponder) es lo que hace visible al receptor."""
    if not IS_WINDOWS:
        return False
    try:
        out = subprocess.run(
            ["sc", "query", "Bonjour Service"], capture_output=True, text=True, timeout=10,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        ).stdout
        return "RUNNING" in out.upper()
    except Exception:
        return False


def port_listening(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.4)
        return s.connect_ex(("127.0.0.1", port)) == 0


def network_hint(ip: str, wifi: dict) -> str:
    if ip.startswith("127."):
        return "La PC no tiene red: conectala al mismo Wi-Fi que el iPhone."
    if wifi.get("band", "").startswith("2.4"):
        return "Estas en Wi-Fi 2.4 GHz: para 1080p60 conviene 5 GHz (menos interferencia)."
    return "PC y iPhone tienen que estar en la misma red Wi-Fi (sin 'aislamiento de clientes')."


def sanitize_receiver_name(name: str) -> str:
    """Nombre valido y lindo para mostrar en el iPhone."""
    name = re.sub(r"[\r\n\t]+", " ", name).strip()
    name = re.sub(r"\s{2,}", " ", name)
    return name[:48] or "AirBridge PC"
