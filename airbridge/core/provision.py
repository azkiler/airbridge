"""Ubicacion, descarga e instalacion del motor AirPlay.

AirBridge no reimplementa AirPlay: usa UxPlay (GPLv3), el receptor open source
maduro que ya funciona en Windows 11 (Bonjour + GStreamer + D3D11 + WASAPI).
Este modulo lo encuentra en el sistema o lo baja solo, con barra de progreso.
"""
from __future__ import annotations

import os
import platform
import shutil
import zipfile
from dataclasses import dataclass
from pathlib import Path

from PySide6.QtCore import QThread, Signal

from ..paths import app_dir, engine_dir

ENGINE_VERSION = "2.0.0.1736"
UXPLAY_VERSION = "1.73.7"
RELEASE_BASE = "https://github.com/leapbtw/uxplay-windows/releases/download"
URLS = {
    "x64": f"{RELEASE_BASE}/{ENGINE_VERSION}/uxplay-windows.zip",
    "arm64": f"{RELEASE_BASE}/{ENGINE_VERSION}/uxplay-windows-arm64-UNTESTED.zip",
}
RELEASES_PAGE = "https://github.com/leapbtw/uxplay-windows/releases/latest"
ZIP_NAMES = {"x64": "uxplay-windows.zip", "arm64": "uxplay-windows-arm64.zip"}


@dataclass
class EngineInstall:
    kind: str          # "uxplay-windows" | "uxplay-cli"
    exe: Path
    version: str = ""

    @property
    def folder(self) -> Path:
        return self.exe.parent


def arch() -> str:
    m = platform.machine().lower()
    return "arm64" if m in ("arm64", "aarch64") else "x64"


def _candidates(cfg_path: str = "") -> list[Path]:
    c: list[Path] = []
    if cfg_path:
        p = Path(cfg_path)
        c += [p, p / "uxplay-windows.exe", p / "uxplay.exe"]
    c += [
        app_dir() / "engine" / "uxplay-windows.exe",
        app_dir() / "engine" / "uxplay.exe",
        engine_dir() / "uxplay-windows.exe",
        engine_dir() / "uxplay.exe",
    ]
    for base in (os.environ.get("LOCALAPPDATA", ""), os.environ.get("ProgramFiles", ""),
                 os.environ.get("ProgramFiles(x86)", "")):
        if base:
            c += [Path(base) / "uxplay-windows" / "uxplay-windows.exe",
                  Path(base) / "Programs" / "uxplay-windows" / "uxplay-windows.exe"]
    for name in ("uxplay.exe", "uxplay-windows.exe"):
        w = shutil.which(name)
        if w:
            c.append(Path(w))
    return c


def find_engine(cfg_path: str = "") -> EngineInstall | None:
    for p in _candidates(cfg_path):
        try:
            if p.is_file() and p.suffix.lower() == ".exe":
                kind = "uxplay-cli" if p.name.lower() == "uxplay.exe" else "uxplay-windows"
                return EngineInstall(kind=kind, exe=p,
                                     version=UXPLAY_VERSION if kind == "uxplay-cli" else ENGINE_VERSION)
        except OSError:
            continue
    return None


def default_download_url() -> str:
    return URLS[arch()]


class DownloadWorker(QThread):
    """Descarga + extraccion del motor, con progreso para la interfaz."""

    progress = Signal(int, str)
    done = Signal(str)
    failed = Signal(str)

    def __init__(self, url: str = "", target: Path | None = None) -> None:
        super().__init__()
        self.url = url or default_download_url()
        self.target = target or engine_dir()
        self._cancel = False

    def cancel(self) -> None:
        self._cancel = True

    def run(self) -> None:  # noqa: C901 - flujo lineal de descarga
        import urllib.error
        import urllib.request

        zip_path = self.target / ZIP_NAMES[arch()]
        try:
            self.target.mkdir(parents=True, exist_ok=True)
            self.progress.emit(0, "Conectando con GitHub...")
            req = urllib.request.Request(self.url, headers={"User-Agent": "AirBridge"})
            with urllib.request.urlopen(req, timeout=60) as resp:
                total = int(resp.headers.get("Content-Length", 0))
                read = 0
                with open(zip_path, "wb") as fh:
                    while True:
                        if self._cancel:
                            self.failed.emit("Descarga cancelada.")
                            return
                        chunk = resp.read(262144)
                        if not chunk:
                            break
                        fh.write(chunk)
                        read += len(chunk)
                        if total:
                            pct = int(read * 88 / total)
                            self.progress.emit(pct, f"Descargando motor: {read / 1e6:.0f} / {total / 1e6:.0f} MB")
                        else:
                            self.progress.emit(5, f"Descargando motor: {read / 1e6:.0f} MB")
            self.progress.emit(90, "Extrayendo archivos...")
            with zipfile.ZipFile(zip_path) as zf:
                zf.extractall(self.target)
            exe = self._locate_exe(self.target)
            if exe is None:
                self.failed.emit("El paquete no contiene uxplay-windows.exe.")
                return
            if exe.parent != self.target:
                # El zip puede traer una carpeta contenedora: aplanamos.
                for item in exe.parent.iterdir():
                    dest = self.target / item.name
                    if dest.exists():
                        continue
                    shutil.move(str(item), str(dest))
                exe = self.target / exe.name
            try:
                zip_path.unlink(missing_ok=True)
            except OSError:
                pass
            self.progress.emit(100, "Motor listo.")
            self.done.emit(str(exe))
        except urllib.error.HTTPError as e:
            self.failed.emit(f"GitHub respondio {e.code}. Descarga manual desde la pagina de releases.")
        except Exception as e:  # noqa: BLE001
            self.failed.emit(f"No se pudo descargar el motor: {e}")

    @staticmethod
    def _locate_exe(root: Path) -> Path | None:
        for p in root.rglob("uxplay-windows.exe"):
            return p
        for p in root.rglob("uxplay.exe"):
            return p
        return None
