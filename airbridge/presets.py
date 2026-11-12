"""Presets de rendimiento y traduccion de la configuracion a argumentos del motor.

El motor AirPlay (UxPlay) se controla por linea de comandos. Aca vive TODA la
logica que convierte lo que el usuario elige en la interfaz a esos argumentos,
asi el resto de la app no necesita saber nada del protocolo.
"""
from __future__ import annotations

from dataclasses import dataclass

from .config import MODE_MUSIC, Config
from .paths import coverart_file, key_file, metadata_file


@dataclass(frozen=True)
class Preset:
    key: str
    title: str
    tagline: str
    detail: str
    fps: int
    resolution: str
    av_sync: bool
    audio_latency_ms: int
    decoder: str


PRESETS: dict[str, Preset] = {
    "gaming": Preset(
        key="gaming",
        title="Gaming",
        tagline="Latencia minima",
        detail=(
            "Sin sincronizacion audio/video, buffer de audio corto y decodificacion "
            "por GPU. Es el modo para jugar o usar el iPhone como segunda pantalla."
        ),
        fps=60,
        resolution="1920x1080",
        av_sync=False,
        audio_latency_ms=40,
        decoder="auto",
    ),
    "balanced": Preset(
        key="balanced",
        title="Equilibrado",
        tagline="Fluidez y estabilidad",
        detail=(
            "Sincroniza audio con video y usa un buffer intermedio. Recomendado "
            "para Wi-Fi con varios dispositivos o para ver apps y navegar."
        ),
        fps=60,
        resolution="1920x1080",
        av_sync=True,
        audio_latency_ms=120,
        decoder="auto",
    ),
    "cinema": Preset(
        key="cinema",
        title="Cine",
        tagline="Maxima calidad",
        detail=(
            "Buffer amplio y sincronizacion labial precisa. Ideal para peliculas "
            "y series: mas estable, con un poco mas de retardo."
        ),
        fps=60,
        resolution="1920x1080",
        av_sync=True,
        audio_latency_ms=250,
        decoder="auto",
    ),
}


def apply_preset(cfg: Config, key: str) -> Config:
    """Aplica un preset sobre la configuracion (in place) y la devuelve."""
    p = PRESETS.get(key)
    if p is None:
        cfg.preset = "custom"
        return cfg
    cfg.preset = p.key
    cfg.fps = p.fps
    cfg.resolution = p.resolution
    cfg.av_sync = p.av_sync
    cfg.audio_latency_ms = p.audio_latency_ms
    cfg.decoder = p.decoder
    return cfg


def mark_custom(cfg: Config) -> None:
    """Si el usuario toca un valor individual, el preset pasa a 'Personalizado'."""
    p = PRESETS.get(cfg.preset)
    if p is None:
        return
    if (
        cfg.fps != p.fps
        or cfg.resolution != p.resolution
        or cfg.av_sync != p.av_sync
        or cfg.audio_latency_ms != p.audio_latency_ms
        or cfg.decoder != p.decoder
    ):
        cfg.preset = "custom"


def build_engine_args(cfg: Config) -> list[str]:
    """Lista de argumentos para el motor AirPlay segun la configuracion."""
    a: list[str] = ["-n", cfg.receiver_name, "-nh"]

    # Identidad estable: mismo deviceID y misma clave => el iPhone recuerda el receptor.
    a += ["-m", cfg.device_mac, "-key", str(key_file())]
    a += ["-p", str(cfg.tcp_port)]

    if cfg.mode == MODE_MUSIC:
        # -vs 0 => el motor NO abre ventana de video: solo audio.
        a += ["-vs", "0"]
        # En modo musica (AirPlay audio / ALAC) el cliente manda su propio reloj.
        a += ["-async", "no"]
        a += ["-md", str(metadata_file()), "-ca", str(coverart_file())]
    else:
        a += ["-s", f"{cfg.width}x{cfg.height}@{min(cfg.fps, 60)}"]
        a += ["-fps", str(cfg.fps)]
        a += ["-vs", cfg.video_sink]
        if cfg.decoder != "auto":
            a += ["-vd", cfg.decoder]
        a += ["-vsync"] if cfg.av_sync else ["-vsync", "no"]
        if cfg.client_fps_data:
            a += ["-FPSdata"]
        # -nc: no cerrar la ventana al terminar la sesion (la incrustamos en la app).
        a += ["-nc"]

    a += ["-as", cfg.audio_sink]
    a += ["-al", f"{cfg.audio_latency_ms / 1000:.3f}"]
    a += ["-vol", "0.0" if cfg.muted else f"{cfg.volume:.2f}"]
    # Si el cliente se queda callado, cortar a los 10 s y quedar listos de nuevo.
    a += ["-reset", "10"]

    if cfg.pin_code:
        a += ["-pin", cfg.pin_code]
    if cfg.restrict_clients and cfg.allowed_ids:
        a += ["-restrict"]
        for dev_id in cfg.allowed_ids:
            a += ["-allow", dev_id]

    if cfg.extra_args.strip():
        a += cfg.extra_args.split()
    return a


def args_to_text(args: list[str]) -> str:
    """Representacion legible (para el panel de diagnostico)."""
    out: list[str] = []
    for token in args:
        out.append(f'"{token}"' if " " in token else token)
    return " ".join(out)


def estimated_latency_ms(cfg: Config) -> int:
    """Latencia aproximada de punta a punta (estimacion, no medicion).

    Suma el buffer de audio declarado al cliente mas el costo tipico de
    captura + codificacion en el iPhone, transporte Wi-Fi y render en la PC.
    """
    capture_encode = 35
    network = 12
    decode_render = 14 if cfg.decoder != "avdec_h264" else 26
    sync = 18 if cfg.av_sync else 0
    return int(cfg.audio_latency_ms + capture_encode + network + decode_render + sync)


def quality_summary(cfg: Config) -> str:
    if cfg.mode == MODE_MUSIC:
        return "Solo audio - ALAC sin perdida 44.1 kHz / 16 bit (calidad CD)"
    return f"{cfg.width}x{cfg.height} - {cfg.fps} fps - H.264 + AAC-ELD estereo"


def audio_format_note(cfg: Config) -> str:
    if cfg.mode == MODE_MUSIC:
        return (
            "En Modo Musica el iPhone manda audio ALAC sin perdida (lo mismo que "
            "un AirPlay a un equipo de sonido). No se transmite video."
        )
    return (
        "Al duplicar pantalla, AirPlay usa AAC-ELD estereo de baja latencia: es "
        "el formato del protocolo para mirroring. Para audio sin perdida, usa Modo Musica."
    )
