"""Control del motor AirPlay: arranque, supervision, eventos y estadisticas.

Dos backends reales:
  * uxplay-windows : build portable para Windows 11 (se descarga sola).
                     Se configura con arguments.txt + registro y se supervisa
                     leyendo su log de sesion.
  * uxplay-cli     : uxplay.exe clasico (si el usuario lo compilo con MSYS2).
                     Se controla por argumentos y stdout.
Y un backend 'demo' para recorrer la interfaz sin motor instalado.
"""
from __future__ import annotations

import time
from pathlib import Path

from PySide6.QtCore import QObject, QProcess, QTimer, Signal

from ..config import MODE_MUSIC, Config
from ..paths import (
    logs_dir,
    uxplay_windows_args_file,
    uxplay_windows_log_dir,
    uxplay_windows_machine_args_file,
)
from ..presets import build_engine_args, estimated_latency_ms
from ..win import winapi
from . import logparse, provision

MISSING = "missing"
STOPPED = "stopped"
STARTING = "starting"
READY = "ready"
STREAMING = "streaming"
ERROR = "error"

STATE_LABEL = {
    MISSING: "Falta el motor",
    STOPPED: "Receptor detenido",
    STARTING: "Iniciando receptor",
    READY: "Visible para tu iPhone",
    STREAMING: "Transmitiendo",
    ERROR: "Error del motor",
}


class EngineController(QObject):
    state_changed = Signal(str)
    log_line = Signal(str)
    device_changed = Signal(dict)
    session_changed = Signal(bool)
    stats_changed = Signal(dict)
    video_window_found = Signal(int)
    video_window_lost = Signal()
    notice = Signal(str, str)          # nivel, texto

    def __init__(self, cfg: Config, demo: bool = False, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.cfg = cfg
        self.demo = demo
        self.state = MISSING
        self.install: provision.EngineInstall | None = None
        self.device: dict = {}
        self.streaming = False
        self.started_at = 0.0
        self.session_start = 0.0
        self.client_fps: float | None = None
        self.client_latency: float | None = None
        self.audio_label = ""
        self.last_error = ""
        self.video_hwnd = 0

        self._proc: QProcess | None = None
        self._log_path: Path | None = None
        self._log_pos = 0
        self._stdout_buf = ""
        self._last_args: list[str] = []
        self._window_misses = 0

        self._log_timer = QTimer(self)
        self._log_timer.setInterval(300)
        self._log_timer.timeout.connect(self._pump_log)

        self._watch_timer = QTimer(self)
        self._watch_timer.setInterval(800)
        self._watch_timer.timeout.connect(self._watch)

        self._stats_timer = QTimer(self)
        self._stats_timer.setInterval(1000)
        self._stats_timer.timeout.connect(self._emit_stats)

        self._demo_timer = QTimer(self)
        self._demo_timer.setInterval(900)
        self._demo_timer.timeout.connect(self._demo_tick)
        self._demo_step = 0

        self.refresh_install()

    # ------------------------------------------------------------------
    @property
    def pid(self) -> int:
        if self._proc is not None and self._proc.state() != QProcess.NotRunning:
            return int(self._proc.processId())
        return 0

    @property
    def args(self) -> list[str]:
        return list(self._last_args)

    def refresh_install(self) -> provision.EngineInstall | None:
        self.install = provision.find_engine(self.cfg.engine_path)
        if self.install is None and self.state == MISSING:
            self._set_state(MISSING)
        elif self.install is not None and self.state == MISSING:
            self._set_state(STOPPED)
        return self.install

    def _set_state(self, state: str) -> None:
        if state != self.state:
            self.state = state
            self.state_changed.emit(state)

    # ------------------------------------------------------------------
    def start(self) -> None:
        if self.demo:
            self._last_args = build_engine_args(self.cfg)
            self._set_state(STARTING)
            self._demo_step = 0
            self._demo_timer.start()
            self._stats_timer.start()
            self.log_line.emit("[demo] Motor simulado: no hay transmision real.")
            return

        if self.install is None:
            self.refresh_install()
        if self.install is None:
            self._set_state(MISSING)
            self.notice.emit("warn", "Falta el motor AirPlay. Descargalo desde Inicio.")
            return
        if self._proc is not None and self._proc.state() != QProcess.NotRunning:
            return

        args = build_engine_args(self.cfg)
        self._last_args = args
        self._set_state(STARTING)
        self.last_error = ""
        self.client_fps = None
        self.device = {}
        self.video_hwnd = 0
        self.started_at = time.time()

        if self.install.kind == "uxplay-windows":
            self._prepare_wrapper(args)

        self._proc = QProcess(self)
        self._proc.setProgram(str(self.install.exe))
        self._proc.setWorkingDirectory(str(self.install.folder))
        self._proc.setArguments(args if self.install.kind == "uxplay-cli" else [])
        self._proc.setProcessChannelMode(QProcess.MergedChannels)
        self._proc.readyReadStandardOutput.connect(self._pump_stdout)
        self._proc.errorOccurred.connect(self._proc_error)
        self._proc.finished.connect(self._proc_finished)
        self._proc.start()
        if not self._proc.waitForStarted(8000):
            self._set_state(ERROR)
            self.last_error = "No se pudo iniciar el motor."
            self.notice.emit("error", self.last_error)
            return

        self._log_path = None
        self._log_pos = 0
        self._log_timer.start()
        self._watch_timer.start()
        self._stats_timer.start()
        self.log_line.emit(f"[airbridge] Motor iniciado: {self.install.exe}")
        self._set_state(READY)

    def stop(self) -> None:
        self._demo_timer.stop()
        self._log_timer.stop()
        self._watch_timer.stop()
        self._stats_timer.stop()
        if self._proc is not None:
            try:
                self._proc.readyReadStandardOutput.disconnect()
            except (RuntimeError, TypeError):
                pass
            if self._proc.state() != QProcess.NotRunning:
                self._proc.terminate()
                if not self._proc.waitForFinished(1500):
                    self._proc.kill()
                    self._proc.waitForFinished(1500)
            self._proc.deleteLater()
            self._proc = None
        if self.streaming:
            self.streaming = False
            self.session_changed.emit(False)
        self.video_hwnd = 0
        self.video_window_lost.emit()
        self._set_state(STOPPED if self.install else MISSING)

    def restart(self) -> None:
        self.stop()
        QTimer.singleShot(400, self.start)

    def apply_config(self, cfg: Config, force: bool = False) -> None:
        """Reinicia el motor solo si cambiaron argumentos que lo requieren."""
        old = build_engine_args(self.cfg)
        self.cfg = cfg
        new = build_engine_args(cfg)
        if force or (old != new and self.state not in (STOPPED, MISSING)):
            self.log_line.emit("[airbridge] Aplicando cambios: reiniciando receptor...")
            self.restart()

    # ------------------------------------------------------------------
    def _prepare_wrapper(self, args: list[str]) -> None:
        """uxplay-windows lee argumentos de un archivo y opciones del registro."""
        machine = uxplay_windows_machine_args_file()
        if machine.exists():
            self.notice.emit(
                "warn",
                "Hay un arguments.txt global en ProgramData que pisa la configuracion de AirBridge.",
            )
        path = uxplay_windows_args_file()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(" ".join(f'"{a}"' if " " in a else a for a in args) + "\n", "utf-8")
        if winapi.IS_WINDOWS:
            try:
                import winreg
                with winreg.CreateKey(winreg.HKEY_CURRENT_USER, r"Software\leapbtw\uxplay-windows") as k:
                    # 'auto' = respetar el -vs que escribimos nosotros.
                    winreg.SetValueEx(k, "renderer_mode", 0, winreg.REG_SZ, "auto")
                    winreg.SetValueEx(k, "ble_enabled", 0, winreg.REG_SZ, "false")   # sin Bluetooth
                    winreg.SetValueEx(k, "force_fs_enabled", 0, winreg.REG_SZ, "false")
            except OSError as e:
                self.log_line.emit(f"[airbridge] No se pudo escribir el registro del motor: {e}")

    # ------------------------------------------------------------------
    def _pump_stdout(self) -> None:
        if self._proc is None:
            return
        data = bytes(self._proc.readAllStandardOutput()).decode("utf-8", "replace")
        self._stdout_buf += data
        *lines, self._stdout_buf = self._stdout_buf.split("\n")
        for line in lines:
            self._handle_line(line)

    def _pump_log(self) -> None:
        if self.install is None or self.install.kind != "uxplay-windows":
            return
        path = self._newest_log()
        if path is None:
            return
        if path != self._log_path:
            self._log_path = path
            self._log_pos = 0
        try:
            with open(path, "rb") as fh:
                fh.seek(self._log_pos)
                chunk = fh.read()
                self._log_pos = fh.tell()
        except OSError:
            return
        if not chunk:
            return
        for line in chunk.decode("utf-8", "replace").splitlines():
            self._handle_line(line)

    def _newest_log(self) -> Path | None:
        folder = uxplay_windows_log_dir()
        try:
            files = [p for p in folder.glob("*.log") if p.stat().st_mtime >= self.started_at - 5]
        except OSError:
            return None
        if not files:
            return None
        return max(files, key=lambda p: p.stat().st_mtime)

    def _handle_line(self, line: str) -> None:
        if not line.strip():
            return
        self.log_line.emit(line)
        for ev in logparse.parse_line(line):
            k, d = ev.kind, ev.data
            if k == "client_request":
                self.device = d
                self.device_changed.emit(d)
                self._begin_session()
                self.notice.emit("ok", f"{d.get('name', 'iPhone')} conectado.")
            elif k == "client_registered":
                self.device.update({"name": d.get("name", ""), "device_id": d.get("device_id", "")})
                self.device_changed.emit(self.device)
            elif k == "disconnected":
                self._end_session("Se perdio la conexion con el iPhone.")
            elif k == "denied":
                self.notice.emit("warn", "Conexion rechazada por la lista de dispositivos permitidos.")
            elif k == "audio_format":
                self.audio_label = d.get("label", "")
                if d.get("is_media"):
                    self._begin_session()
            elif k == "client_stats":
                fps = logparse.extract_fps(d)
                lat = logparse.extract_latency_ms(d)
                if fps:
                    self.client_fps = fps
                if lat:
                    self.client_latency = lat
            elif k == "mdns_error":
                self.notice.emit("warn", "Bonjour no pudo anunciar el receptor: revisa el servicio mDNS.")
            elif k == "engine_ready":
                self._set_state(READY if not self.streaming else STREAMING)

    def _begin_session(self) -> None:
        if not self.streaming:
            self.streaming = True
            self.session_start = time.time()
            self.session_changed.emit(True)
        self._set_state(STREAMING)

    def _end_session(self, reason: str = "") -> None:
        if self.streaming:
            self.streaming = False
            self.session_changed.emit(False)
            if reason:
                self.notice.emit("warn", reason)
        self.client_fps = None
        self._set_state(READY)

    # ------------------------------------------------------------------
    def _watch(self) -> None:
        if self._proc is None or self._proc.state() == QProcess.NotRunning:
            if self.state not in (STOPPED, MISSING, ERROR):
                self._set_state(ERROR)
                self.last_error = "El motor se cerro inesperadamente."
                self.notice.emit("error", self.last_error)
            return
        if self.cfg.mode == MODE_MUSIC or not winapi.IS_WINDOWS:
            return
        from ..win.embed import VideoWindow  # import diferido (Win32)
        if self.video_hwnd and winapi.is_window(self.video_hwnd):
            self._window_misses = 0
            return
        vw = VideoWindow()
        hwnd = vw.find(self.pid)
        if hwnd:
            self.video_hwnd = hwnd
            self._window_misses = 0
            self.video_window_found.emit(hwnd)
            self._begin_session()
        else:
            self._window_misses += 1
            if self.video_hwnd and self._window_misses >= 4:
                self.video_hwnd = 0
                self.video_window_lost.emit()
                self._end_session()

    def _proc_error(self, _err) -> None:
        self.last_error = "No se pudo ejecutar el motor AirPlay."
        self._set_state(ERROR)
        self.notice.emit("error", self.last_error)

    def _proc_finished(self, code: int, _status) -> None:
        self.log_line.emit(f"[airbridge] Motor finalizado (codigo {code}).")
        if self.streaming:
            self._end_session()
        if self.state not in (STOPPED, MISSING):
            self._set_state(STOPPED if self.install else MISSING)

    # ------------------------------------------------------------------
    def _emit_stats(self) -> None:
        elapsed = int(time.time() - self.session_start) if self.streaming else 0
        self.stats_changed.emit({
            "fps": self.client_fps,
            "target_fps": self.cfg.fps if self.cfg.mode != MODE_MUSIC else 0,
            "resolution": self.cfg.resolution if self.cfg.mode != MODE_MUSIC else "",
            "latency_ms": self.client_latency or estimated_latency_ms(self.cfg),
            "latency_is_estimate": self.client_latency is None,
            "elapsed": elapsed,
            "audio": self.audio_label or ("ALAC sin perdida" if self.cfg.mode == MODE_MUSIC else "AAC-ELD"),
            "streaming": self.streaming,
            "device": self.device.get("name", ""),
        })

    # --- demo ---------------------------------------------------------
    def _demo_tick(self) -> None:
        self._demo_step += 1
        if self._demo_step == 1:
            self._set_state(READY)
            self.log_line.emit("[demo] Receptor anunciado por mDNS (simulado).")
        elif self._demo_step == 3:
            self.device = {"name": "iPhone de Alex", "model": "iPhone 15 Pro", "device_id": "02:42:aa:10:20:30"}
            self.device_changed.emit(self.device)
            self.audio_label = "ALAC sin perdida" if self.cfg.mode == MODE_MUSIC else "AAC-ELD (mirroring)"
            self._begin_session()
            self.notice.emit("ok", "iPhone de Alex conectado (demo).")
        elif self._demo_step > 3:
            import math
            t = self._demo_step
            self.client_fps = 59.0 + math.sin(t / 3.0)
            self.client_latency = 58 + 6 * math.sin(t / 5.0)

    # ------------------------------------------------------------------
    def diagnostics(self) -> str:
        lines = [
            f"AirBridge - estado: {STATE_LABEL.get(self.state, self.state)}",
            f"Motor: {self.install.exe if self.install else 'no instalado'}",
            f"Tipo de motor: {self.install.kind if self.install else '-'}",
            f"Modo: {self.cfg.mode} | Preset: {self.cfg.preset}",
            f"Dispositivo: {self.device or '-'}",
            f"Argumentos: {' '.join(self._last_args)}",
            f"Log del motor: {self._log_path or '-'}",
            f"Errores: {self.last_error or 'ninguno'}",
        ]
        return "\n".join(lines)

    def save_log_snapshot(self) -> Path:
        p = logs_dir() / f"airbridge-diagnostico-{int(time.time())}.txt"
        p.write_text(self.diagnostics(), "utf-8")
        return p
