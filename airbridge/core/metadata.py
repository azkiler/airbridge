"""Metadatos y caratula del Modo Musica.

El motor escribe, en modo AirPlay Audio (ALAC), un archivo de texto con
'Artist: ...', 'Title: ...', 'Album: ...' y un archivo binario con la caratula.
Aca los leemos y los exponemos a la interfaz.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ..paths import coverart_file, metadata_file


@dataclass
class TrackInfo:
    title: str = ""
    artist: str = ""
    album: str = ""
    cover_path: str = ""
    cover_stamp: float = 0.0

    @property
    def has_data(self) -> bool:
        return bool(self.title or self.artist or self.album)


def read_track() -> TrackInfo:
    t = TrackInfo()
    p = metadata_file()
    try:
        text = p.read_text("utf-8", errors="replace")
    except OSError:
        text = ""
    for line in text.splitlines():
        if ":" not in line:
            continue
        tag, value = line.split(":", 1)
        tag, value = tag.strip().lower(), value.strip()
        if tag == "title":
            t.title = value
        elif tag == "artist":
            t.artist = value
        elif tag == "album":
            t.album = value
    cover = coverart_file()
    if cover.exists() and cover.stat().st_size > 128:
        t.cover_path = str(cover)
        t.cover_stamp = cover.stat().st_mtime
    return t


def clear_media() -> None:
    for p in (metadata_file(), coverart_file()):
        try:
            Path(p).unlink(missing_ok=True)
        except OSError:
            pass
