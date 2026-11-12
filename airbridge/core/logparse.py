"""Lectura del log del motor AirPlay -> eventos que entiende la interfaz.

UxPlay escribe su log de sesion en %LOCALAPPDATA%/uxplay-windows/logs.
Estas expresiones estan tomadas de los mensajes reales del codigo fuente
(UxPlay 1.73.x). Todo es tolerante: si una linea no matchea, se ignora.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Iterator

RE_CONNECT = re.compile(
    r"connection request from\s+(?P<name>.+?)\s+\((?P<model>[^)]*)\)\s+with deviceID\s*=\s*(?P<id>\S+)"
)
RE_REGISTERED = re.compile(r"registered new client:\s*(?P<name>.+?)\s+DeviceID\s*=\s*(?P<id>\S+)")
RE_LOST = re.compile(r"ERROR\s+lost connection with client", re.I)
RE_DENIED = re.compile(r"attempt to connect by blocked client.*DENIED", re.I)
RE_RESTRICTED = re.compile(r"client connections have been restricted", re.I)
RE_AUDIO_FMT = re.compile(
    r"ct=(?P<ct>\d+)\s+spf=(?P<spf>\d+)\s+usingScreen=(?P<screen>\d+)\s+isMedia=(?P<media>\d+)\s+audioFormat=0x(?P<fmt>[0-9a-fA-F]+)"
)
RE_VOLUME = re.compile(r"AirPlay volume\s+(?P<db>-?[\d.]+)\s+dB\s+\(slider\s+(?P<pct>[\d.]+)%\)")
RE_COVERART = re.compile(r"coverart size\s+(?P<size>\d+)\s+written to")
RE_METADATA = re.compile(r"^(?P<tag>Album artist|Album|Artist|Title|Composer|Genre|Comment)\s*:\s*(?P<value>.*)$")
RE_PLIST_KEY = re.compile(r"<key>(?P<k>[^<]+)</key>\s*<(?P<t>integer|real)>(?P<v>[-\d.]+)</")
RE_H265 = re.compile(r"h265 sps size", re.I)
RE_VIDEO_WINDOW = re.compile(r"Direct3D11 renderer|video window", re.I)
RE_STARTED = re.compile(r"AirPlay server started|Starting UxPlay engine", re.I)
RE_MDNS_FAIL = re.compile(r"dnssd_register_(raop|airplay) failed", re.I)
RE_BONJOUR_FAIL = re.compile(r"Bonjour.*(not|fail|error)", re.I)


@dataclass
class EngineEvent:
    kind: str
    data: dict = field(default_factory=dict)


def parse_line(line: str) -> Iterator[EngineEvent]:
    """Convierte una linea de log en cero o mas eventos."""
    line = line.rstrip("\r\n")
    if not line:
        return

    m = RE_CONNECT.search(line)
    if m:
        yield EngineEvent("client_request", {
            "name": m.group("name").strip(),
            "model": m.group("model").strip(),
            "device_id": m.group("id").strip(),
        })
        return

    m = RE_REGISTERED.search(line)
    if m:
        yield EngineEvent("client_registered", {
            "name": m.group("name").strip(),
            "device_id": m.group("id").strip(),
        })
        return

    if RE_LOST.search(line):
        yield EngineEvent("disconnected", {"reason": "network"})
        return
    if RE_DENIED.search(line):
        yield EngineEvent("denied", {"reason": "blocked"})
        return
    if RE_RESTRICTED.search(line):
        yield EngineEvent("denied", {"reason": "restricted"})
        return

    m = RE_AUDIO_FMT.search(line)
    if m:
        is_media = m.group("media") == "1"
        yield EngineEvent("audio_format", {
            "is_media": is_media,
            "using_screen": m.group("screen") == "1",
            "samples_per_frame": int(m.group("spf")),
            "label": "ALAC (AirPlay Audio)" if is_media else "AAC-ELD (mirroring)",
        })
        return

    m = RE_VOLUME.search(line)
    if m:
        yield EngineEvent("volume", {"db": float(m.group("db")), "percent": float(m.group("pct"))})
        return

    if RE_COVERART.search(line):
        yield EngineEvent("coverart", {})
        return

    m = RE_METADATA.match(line.strip())
    if m:
        yield EngineEvent("metadata", {"tag": m.group("tag"), "value": m.group("value").strip()})
        return

    if RE_H265.search(line):
        yield EngineEvent("codec", {"codec": "H.265"})
        return

    if RE_MDNS_FAIL.search(line):
        yield EngineEvent("mdns_error", {})
        return

    if RE_STARTED.search(line):
        yield EngineEvent("engine_ready", {})
        return

    # Reporte de rendimiento del cliente (-FPSdata): plist XML con claves variadas.
    if "<key>" in line and "</key>" in line:
        stats: dict[str, float] = {}
        for km in RE_PLIST_KEY.finditer(line):
            key = km.group("k").strip().lower()
            try:
                stats[key] = float(km.group("v"))
            except ValueError:
                continue
        if stats:
            yield EngineEvent("client_stats", stats)


def extract_fps(stats: dict) -> float | None:
    """Busca una clave de FPS dentro del reporte del cliente (nombres variables)."""
    for k, v in stats.items():
        if "fps" in k and "drop" not in k and 0 < v <= 240:
            return v
    return None


def extract_latency_ms(stats: dict) -> float | None:
    for k, v in stats.items():
        if "latency" in k or "delay" in k:
            # algunos reportes vienen en segundos, otros en milisegundos
            return v * 1000.0 if v < 10 else v
    return None
