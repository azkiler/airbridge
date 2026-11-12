"""Pagina Ayuda: guia, soluciones y registro en vivo del motor."""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QPlainTextEdit, QVBoxLayout, QWidget

from ...core import provision
from ...paths import logs_dir
from ..widgets import ActionButton, Collapsible, card, label, row
from .base import Page

FAQ = [
    ("El iPhone no ve el receptor",
     "1. PC y iPhone deben estar en la MISMA red Wi-Fi (no una red de invitados).\n"
     "2. En el router, desactiva 'AP isolation' / 'aislamiento de clientes'.\n"
     "3. Acepta el aviso de firewall de Windows o usa Ajustes > Configurar firewall.\n"
     "4. El servicio Bonjour (mDNSResponder) tiene que estar corriendo: el motor lo "
     "instala la primera vez y pide permisos de administrador.\n"
     "5. Reinicia el receptor con el boton 'Reiniciar receptor'."),
    ("Se ve con tirones o pocos FPS",
     "1. Usa Wi-Fi 5 GHz; el 2.4 GHz suele saturarse.\n"
     "2. Perfil Gaming en la pagina Gaming (menos buffer, menos latencia).\n"
     "3. Proba el decodificador 'GPU Direct3D11'.\n"
     "4. Baja a 1280x720 si la red es lenta: se ve mejor que 1080p con cortes.\n"
     "5. Cerra descargas y streaming en la misma red."),
    ("No se escucha el audio",
     "1. Revisa el volumen del receptor en la pagina Musica y el mezclador de Windows.\n"
     "2. Si el iPhone esta en silencio, el mirroring manda audio igual: revisa la app.\n"
     "3. Cambia el dispositivo de salida por defecto de Windows antes de conectar.\n"
     "4. En Ajustes avanzados del motor podes forzar el sink de audio (WASAPI)."),
    ("La ventana se va atras de otros programas",
     "Activa 'Anclar' en la barra superior y 'Siempre arriba de todo' en Ajustes. "
     "AirBridge vuelve a ponerse arriba automaticamente cada segundo, sin robarte el foco."),
    ("Quiero solo audio, sin mostrar mi pantalla",
     "Activa el Modo Musica. El motor deja de aceptar video (-vs 0) y el iPhone puede "
     "enviar audio desde el reproductor con AirPlay. Ademas el audio pasa a ALAC sin perdida."),
    ("Como hago que arranque solo al prender la PC",
     "Ajustes > Inicio y comportamiento > 'Iniciar con Windows'. Se guarda en el registro "
     "del usuario (no necesita administrador) y el receptor queda anunciando solo."),
    ("Privacidad y Bluetooth",
     "AirBridge no usa Bluetooth ni el beacon BLE: el descubrimiento es por Wi-Fi con "
     "Bonjour/mDNS. Todo el trafico queda dentro de tu red local; no se sube nada a internet "
     "(salvo la descarga del motor desde GitHub la primera vez)."),
]


class HelpPage(Page):
    key = "help"
    title = "Ayuda"

    def build(self) -> None:
        self.lay.addWidget(self.header(
            "Guia rapida",
            "Ayuda y diagnostico",
            "Si algo no funciona, casi siempre es la red o el firewall. Aca esta el detalle.",
        ))

        quick = QWidget()
        ql = QVBoxLayout(quick)
        ql.setContentsMargins(0, 0, 0, 0)
        ql.setSpacing(8)
        ql.addWidget(label("Conectar en 20 segundos", "h2"))
        for t in [
            "1. Deja la PC y el iPhone en el mismo Wi-Fi.",
            "2. En esta app, toca 'Iniciar receptor' (si ya esta iniciado, no hace falta).",
            "3. En el iPhone: Centro de control > Duplicar pantalla > elegi el nombre del receptor.",
            "4. Listo: el video aparece en la pagina Pantalla, con el audio en los parlantes de la PC.",
        ]:
            ql.addWidget(label(t, "dim", wrap=True))
        self.lay.addWidget(card(quick, 1, 20))

        for title, body in FAQ:
            box = QWidget()
            bl = QVBoxLayout(box)
            bl.setContentsMargins(0, 0, 0, 0)
            bl.addWidget(label(body, "dim", wrap=True))
            self.lay.addWidget(Collapsible(title, box, opened=False))

        logbox = QWidget()
        ll = QVBoxLayout(logbox)
        ll.setContentsMargins(0, 0, 0, 0)
        ll.setSpacing(10)
        self.log = QPlainTextEdit()
        self.log.setObjectName("log")
        self.log.setReadOnly(True)
        self.log.setMaximumBlockCount(1200)
        self.log.setMinimumHeight(220)
        ll.addWidget(self.log)
        b1 = ActionButton("Copiar diagnostico", "neutral")
        b1.clicked.connect(self.app.copy_diagnostics)
        b2 = ActionButton("Abrir carpeta de registros", "neutral")
        b2.clicked.connect(lambda: self.app.open_path(logs_dir()))
        b3 = ActionButton("Pagina del motor (GitHub)", "ghost")
        b3.clicked.connect(lambda: self.app.open_url(provision.RELEASES_PAGE))
        ll.addWidget(row(b1, b2, b3, "stretch"))
        self.lay.addWidget(Collapsible("Registro en vivo del motor", logbox, opened=True))

        legal = QWidget()
        lg = QVBoxLayout(legal)
        lg.setContentsMargins(0, 0, 0, 0)
        lg.setSpacing(6)
        lg.addWidget(label(
            "AirBridge es una interfaz original (MIT). El motor AirPlay es UxPlay, "
            "licencia GPLv3, que se descarga por separado desde su repositorio oficial. "
            "AirPlay y iPhone son marcas de Apple Inc.; este proyecto no esta afiliado a Apple.",
            "mute", wrap=True))
        self.lay.addWidget(legal)

    def append_log(self, line: str) -> None:
        self.log.appendPlainText(line)

    def on_show(self) -> None:
        pass
