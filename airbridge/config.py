"""Configuracion persistente de AirBridge.

Todo lo que el usuario toca en la interfaz vive aca y se guarda en
%APPDATA%/AirBridge/config.json. El archivo es tolerant a versiones viejas:
las claves desconocidas se ignoran y las faltantes toman su valor por defecto.
"""
from __future__ import annotations

import json
import random
from dataclasses import asdict, dataclass, field, fields
from pathlib import Path
from typing import Any

from .paths import config_file

MODE_SCREEN = "screen"
MODE_MUSIC = "music"

RESOLUTIONS = ["1280x720", "1920x1080", "2560x1440", "3840x2160"]
FPS_CHOICES = [30, 60, 120]


def _random_mac() -> str:
    """MAC localmente administrada, estable entre reinicios.

    Se la pasamos al motor con -m para que el iPhone vea siempre el mismo
    receptor (si no, cada arranque aparece un receptor nuevo en la lista).
    """
    octets = [0x02, 0x42] + [random.randrange(0, 256) for _ in range(4)]
    return ":".join(f"{o:02x}" for o in octets)


@dataclass
class Config:
    # --- Identidad / descubrimiento -------------------------------------
    receiver_name: str = "AirBridge PC"
    device_mac: str = field(default_factory=_random_mac)
    tcp_port: int = 7000
    pin_code: str = ""            # "" = sin PIN (conectar y listo)
    allowed_ids: list[str] = field(default_factory=list)
    restrict_clients: bool = False

    # --- Modo y calidad --------------------------------------------------
    mode: str = MODE_SCREEN       # screen | music
    preset: str = "gaming"        # gaming | balanced | cinema | custom
    resolution: str = "1920x1080"
    fps: int = 60
    decoder: str = "auto"         # auto | d3d11h264dec | nvh264dec | avdec_h264
    video_sink: str = "d3d11videosink"
    audio_sink: str = "autoaudiosink"
    audio_latency_ms: int = 60
    av_sync: bool = False         # False = minima latencia (gaming)
    volume: float = 1.0
    muted: bool = False

    # --- Comportamiento en Windows --------------------------------------
    autostart: bool = True
    start_engine_on_launch: bool = True
    always_on_top: bool = True
    pin_video_window: bool = True
    prevent_sleep: bool = True
    embed_video: bool = True
    floating_video: bool = False
    close_to_tray: bool = False

    # --- Interfaz --------------------------------------------------------
    animations: bool = True
    ui_scale: float = 1.0
    sidebar_collapsed: bool = False
    stats_overlay: bool = True
    client_fps_data: bool = True
    window_geometry: list[int] = field(default_factory=lambda: [0, 0, 1200, 760])

    # --- Motor -----------------------------------------------------------
    engine_kind: str = "auto"     # auto | uxplay-windows | uxplay-cli
    engine_path: str = ""
    extra_args: str = ""
    first_run: bool = True

    # ------------------------------------------------------------------
    @classmethod
    def load(cls, path: Path | None = None) -> "Config":
        path = path or config_file()
        cfg = cls()
        try:
            raw = json.loads(path.read_text("utf-8"))
        except (OSError, ValueError):
            return cfg
        known = {f.name for f in fields(cls)}
        for k, v in raw.items():
            if k in known:
                setattr(cfg, k, v)
        cfg.validate()
        return cfg

    def save(self, path: Path | None = None) -> None:
        path = path or config_file()
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(asdict(self), indent=2, ensure_ascii=False), "utf-8")
        tmp.replace(path)

    def validate(self) -> None:
        if self.mode not in (MODE_SCREEN, MODE_MUSIC):
            self.mode = MODE_SCREEN
        if self.resolution not in RESOLUTIONS:
            self.resolution = "1920x1080"
        if self.fps not in FPS_CHOICES:
            self.fps = 60
        self.tcp_port = max(1024, min(65530, int(self.tcp_port)))
        self.audio_latency_ms = max(0, min(1000, int(self.audio_latency_ms)))
        self.volume = max(0.0, min(1.0, float(self.volume)))
        self.ui_scale = max(0.85, min(1.35, float(self.ui_scale)))
        if self.pin_code and (len(self.pin_code) != 4 or not self.pin_code.isdigit()):
            self.pin_code = ""
        if not self.receiver_name.strip():
            self.receiver_name = "AirBridge PC"
        if not self.device_mac:
            self.device_mac = _random_mac()

    # --- helpers ---------------------------------------------------------
    @property
    def width(self) -> int:
        return int(self.resolution.split("x")[0])

    @property
    def height(self) -> int:
        return int(self.resolution.split("x")[1])

    def update(self, **kwargs: Any) -> None:
        for k, v in kwargs.items():
            if hasattr(self, k):
                setattr(self, k, v)
        self.validate()
