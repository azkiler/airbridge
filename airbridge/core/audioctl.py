"""Control de volumen del motor en caliente (Windows).

El motor AirPlay solo acepta el volumen al arrancar, asi que para que el
slider de la app funcione SIN reiniciar la transmision usamos el volumen de
sesion de audio de Windows (WASAPI) del proceso del motor, via pycaw.
Si pycaw no esta instalado, el slider queda como volumen inicial y se avisa.
"""
from __future__ import annotations

from ..win.winapi import IS_WINDOWS

try:  # pragma: no cover - dependencia opcional, solo Windows
    from pycaw.pycaw import AudioUtilities, ISimpleAudioVolume  # type: ignore
    from pycaw.pycaw import IAudioMeterInformation  # type: ignore
    HAS_PYCAW = True
except Exception:  # noqa: BLE001
    HAS_PYCAW = False


class SessionVolume:
    def __init__(self) -> None:
        self.available = HAS_PYCAW and IS_WINDOWS

    def _session(self, pid: int):
        if not self.available or not pid:
            return None
        try:
            for s in AudioUtilities.GetAllSessions():
                if s.ProcessId == pid:
                    return s._ctl.QueryInterface(ISimpleAudioVolume)
        except Exception:  # noqa: BLE001
            return None
        return None

    def set_volume(self, pid: int, value: float) -> bool:
        ctl = self._session(pid)
        if ctl is None:
            return False
        try:
            ctl.SetMasterVolume(max(0.0, min(1.0, value)), None)
            return True
        except Exception:  # noqa: BLE001
            return False

    def set_mute(self, pid: int, muted: bool) -> bool:
        ctl = self._session(pid)
        if ctl is None:
            return False
        try:
            ctl.SetMute(bool(muted), None)
            return True
        except Exception:  # noqa: BLE001
            return False

    def peak(self) -> float:
        """Pico del dispositivo de salida (0..1) para el visualizador."""
        if not self.available:
            return 0.0
        try:
            dev = AudioUtilities.GetSpeakers()
            meter = dev.Activate(IAudioMeterInformation._iid_, 23, None)  # CLSCTX_ALL
            return float(meter.GetPeakValue())
        except Exception:  # noqa: BLE001
            return 0.0
