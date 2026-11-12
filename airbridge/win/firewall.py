"""Reglas de firewall para que el iPhone pueda descubrir y conectarse.

AirPlay necesita: mDNS/Bonjour (UDP 5353) para aparecer en la lista del
iPhone y los puertos del receptor (TCP/UDP 7000-7002 por defecto).
Se agregan reglas por programa (motor + Bonjour) y por puerto.
"""
from __future__ import annotations

import subprocess
from pathlib import Path

from .winapi import IS_WINDOWS

RULE_PREFIX = "AirBridge"


def build_commands(engine_exe: Path | None, port: int = 7000) -> list[str]:
    cmds: list[str] = []
    ports_tcp = f"{port}-{port + 2}"
    ports_udp = f"{port}-{port + 2}"
    cmds.append(
        f'netsh advfirewall firewall add rule name="{RULE_PREFIX} AirPlay TCP" '
        f"dir=in action=allow protocol=TCP localport={ports_tcp} profile=any"
    )
    cmds.append(
        f'netsh advfirewall firewall add rule name="{RULE_PREFIX} AirPlay UDP" '
        f"dir=in action=allow protocol=UDP localport={ports_udp} profile=any"
    )
    cmds.append(
        f'netsh advfirewall firewall add rule name="{RULE_PREFIX} Bonjour mDNS" '
        "dir=in action=allow protocol=UDP localport=5353 profile=any"
    )
    if engine_exe:
        cmds.append(
            f'netsh advfirewall firewall add rule name="{RULE_PREFIX} Motor AirPlay" '
            f'dir=in action=allow program="{engine_exe}" enable=yes profile=any'
        )
        mdns = engine_exe.parent / "mDNSResponder.exe"
        if mdns.exists():
            cmds.append(
                f'netsh advfirewall firewall add rule name="{RULE_PREFIX} Bonjour Servicio" '
                f'dir=in action=allow program="{mdns}" enable=yes profile=any'
            )
    return cmds


def rules_present() -> bool:
    if not IS_WINDOWS:
        return False
    try:
        out = subprocess.run(
            ["netsh", "advfirewall", "firewall", "show", "rule", f"name={RULE_PREFIX} AirPlay TCP"],
            capture_output=True, text=True, timeout=15,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        return out.returncode == 0 and "AirBridge" in out.stdout
    except Exception:
        return False


def install_rules(engine_exe: Path | None, port: int = 7000) -> bool:
    """Lanza un PowerShell elevado (un solo UAC) que aplica todas las reglas."""
    if not IS_WINDOWS:
        return False
    cmds = build_commands(engine_exe, port)
    script = "; ".join(cmds)
    ps = (
        "Start-Process cmd -Verb RunAs -WindowStyle Hidden -ArgumentList '/c "
        + script.replace("'", "''")
        + "'"
    )
    try:
        subprocess.run(
            ["powershell", "-NoProfile", "-Command", ps],
            capture_output=True, text=True, timeout=120,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        return rules_present()
    except Exception:
        return False


def remove_rules() -> None:
    if not IS_WINDOWS:
        return
    for name in ("AirPlay TCP", "AirPlay UDP", "Bonjour mDNS", "Motor AirPlay", "Bonjour Servicio"):
        try:
            subprocess.run(
                ["netsh", "advfirewall", "firewall", "delete", "rule", f"name={RULE_PREFIX} {name}"],
                capture_output=True, timeout=20,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
        except Exception:
            pass
