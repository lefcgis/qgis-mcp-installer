#!/usr/bin/env python3
"""
build_exe.py — Empaqueta el ETL como un único .exe autocontenido (Windows).

QUÉ HACE Y QUÉ NO
-----------------
SÍ:  produce `dist/qgis-mcp-installer.exe`, un binario de un solo archivo que
     incluye el intérprete de Python y `manifest.py`, para que el usuario final
     no tenga que instalar Python ni manejar archivos .py sueltos.

NO:  no ofusca, no cifra, no empaqueta anti-análisis ni intenta evadir
     antivirus. El código fuente que va dentro es EXACTAMENTE el de este
     repositorio, publicado y auditable. El "binario" es solo un formato de
     distribución cómodo, no un escondite.

FIRMA DE CÓDIGO (recomendado para distribución pública)
-------------------------------------------------------
Un .exe sin firmar dispara advertencias de SmartScreen y de varios antivirus.
La forma correcta de que Windows CONFÍE en tu instalador NO es esconderse, sino
FIRMARLO con un certificado de firma de código (OV/EV). Tras el build:

    signtool sign /fd SHA256 /tr http://timestamp.digicert.com /td SHA256 \\
        /a dist\\qgis-mcp-installer.exe

y publica el SHA-256 del .exe junto a la descarga para que cualquiera lo verifique.

Uso:
    python build_exe.py            # construye el .exe
    python build_exe.py --clean    # limpia build/ dist/ antes de construir
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
APP_NAME = "qgis-mcp-installer"
ENTRY = HERE / "etl_installer.py"


def _ensure_pyinstaller() -> None:
    try:
        import PyInstaller  # noqa: F401
    except ImportError:
        print("PyInstaller no está instalado. Instálalo con:")
        print("    python -m pip install -r requirements-build.txt")
        sys.exit(1)


def main() -> int:
    parser = argparse.ArgumentParser(description="Construye el .exe del instalador.")
    parser.add_argument("--clean", action="store_true", help="Limpia build/ y dist/.")
    args = parser.parse_args()

    _ensure_pyinstaller()

    if args.clean:
        for d in ("build", "dist"):
            shutil.rmtree(HERE / d, ignore_errors=True)
        for spec in HERE.glob("*.spec"):
            spec.unlink()

    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--onefile",                 # un solo .exe
        "--console",                 # instalador de consola (muestra el progreso)
        "--name", APP_NAME,
        # manifest.py se importa en runtime: lo incluimos como módulo.
        "--add-data", f"{HERE / 'manifest.py'}{';' if sys.platform == 'win32' else ':'}.",
        "--hidden-import", "manifest",
        # Sin UPX ni strip: nada de reducir/ofuscar el binario.
        "--noupx",
        str(ENTRY),
    ]
    print("Ejecutando:", " ".join(cmd))
    rc = subprocess.run(cmd, cwd=HERE).returncode
    if rc != 0:
        print("Build falló.")
        return rc

    exe = HERE / "dist" / (APP_NAME + (".exe" if sys.platform == "win32" else ""))
    if exe.exists():
        print(f"\nOK -> {exe}  ({exe.stat().st_size / 1e6:.1f} MB)")
        print("\nSiguiente paso recomendado: FIRMA el .exe (ver cabecera de este archivo)")
        print("y publica su SHA-256 junto a la descarga.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
