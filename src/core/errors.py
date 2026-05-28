"""Utilidades para manejo amigable de errores."""
from __future__ import annotations

import re


def friendly_error(ex: Exception) -> str:
    """Convierte una excepción en un mensaje amigable para el usuario."""
    msg = str(ex)
    exc_type = type(ex).__name__

    if exc_type == "TimeoutError" or "Timeout" in exc_type or "timed out" in msg.lower():
        return "La conexión con el servidor no respondió a tiempo. Verifique su conexión a internet e intente nuevamente."
    if "Credenciales incorrectas" in msg or "credenciales" in msg.lower():
        return "Credenciales incorrectas o sin acceso al ERP. Verifique usuario y contraseña en el diálogo de credenciales."
    if msg == "" or ("user" in msg.lower() and "pass" in msg.lower()):
        return "Debe ingresar usuario y contraseña para descargar del ERP."
    if exc_type in ("ConnectionError", "ConnectionRefusedError", "ConnectionAbortedError", "ConnectionResetError"):
        return "No se pudo conectar al servidor. Verifique su conexión a internet o que el servidor esté disponible."
    if "ENOTFOUND" in msg or "getaddrinfo" in msg:
        return "No se pudo resolver la dirección del servidor. Verifique su conexión a internet."
    if "ECONNREFUSED" in msg:
        return "El servidor rechazó la conexión. Puede estar caído o no accesible desde su red."
    if "HTTPError" in exc_type or "status" in msg.lower():
        match = re.search(r"(\d{3})", msg)
        code = match.group(1) if match else ""
        return f"El servidor respondió con un error (HTTP {code}). Intente más tarde." if code else "El servidor respondió con un error inesperado."
    if "Playwright" in msg or "playwright" in msg.lower():
        return "Error al controlar el navegador automático. Revise los logs para más detalles."
    if "parse" in msg.lower() or "parsing" in msg.lower():
        return "Error al procesar el archivo descargado. El formato puede ser incorrecto."

    # fallback: short, clean message
    short = msg if len(msg) < 150 else msg[:147] + "..."
    return f"Error inesperado: {short}"