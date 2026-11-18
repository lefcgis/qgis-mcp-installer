#!/usr/bin/env python3
"""
QGIS MCP — Instalador ETL (Extract · Transform · Load)
======================================================

Aprovisiona de cero un equipo Windows para usar QGIS con Claude AI vía el
Model Context Protocol, en 6 pasos + una verificación final:

    1. Claude Desktop         (detecta; si falta, descarga el MSIX oficial)
    2. QGIS 3.44 LTR          (detecta; si falta, instala. SIN admin usa
                               OSGeo4W en la carpeta del usuario — cero UAC)
    3. Entorno de Python      (uv + CPython propio + carpeta de librerías
                               aislada; no depende del Python del sistema ni
                               del de QGIS, ni crea ejecutables sin firma)
    4. Plugin + servidor MCP  (descarga el fork e instala el servidor)
    5. Configura QGIS         (despliega el plugin y lo habilita en el perfil)
    6. Configura Claude       (escribe claude_desktop_config.json, con respaldo)
    7. Verificación           (arranca el servidor MCP como lo haría Claude y
                               comprueba que responde; nada de "listo" a ciegas)

FILOSOFÍA DE DISEÑO
-------------------
Este instalador es DELIBERADAMENTE transparente y auditable:

  • Todo lo que descarga está declarado en `manifest.py`, en claro.
  • Cada acción se imprime en pantalla y se registra en un log con fecha,
    incluida la salida de los programas que ejecuta.
  • Los binarios se verifican por firma Authenticode o por SHA-256 fijado
    antes de ejecutarse. Nada se ejecuta a ciegas.
  • El usuario elige la carpeta raíz de instalación.
  • No hay ofuscación, empaquetado anti-análisis ni evasión de detección.

Uso:
    python etl_installer.py                     # asistente interactivo
    python etl_installer.py --non-interactive --base-dir "D:/QGIS-Claude"
    python etl_installer.py --dry-run           # muestra el plan, no toca nada
    python etl_installer.py --steps 4-7         # solo plugin + configuración
    python etl_installer.py --steps 7           # solo verificar
    python etl_installer.py --uninstall         # quita plugin y configuración

Códigos de salida: 0 = todo correcto · 1 = un paso falló ·
2 = completado, pero queda algo por hacer a mano · 130 = cancelado.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import os
import platform
import re
import shutil
import socket
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
import zipfile
from dataclasses import dataclass, field
from pathlib import Path

import manifest
from messages import MSG

__version__ = "2.0.0"

IS_WIN = sys.platform == "win32"
FROZEN = bool(getattr(sys, "frozen", False))
ALL_STEPS = (1, 2, 3, 4, 5, 6, 7)
YES = ("s", "si", "sí", "sim", "y", "yes")
NO = ("n", "no", "nao", "não")

# ─────────────────────────────────────────────────────────────────────────────
# Consola
# ─────────────────────────────────────────────────────────────────────────────

try:  # mejora acentos en consolas que soportan UTF-8; inofensivo si falla
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass


def _enable_vt() -> bool:
    """Activa las secuencias ANSI en la consola clásica de Windows.

    Sin esto, en conhost los colores salen como basura («←[32m»).
    """
    if not IS_WIN:
        return True
    try:
        import ctypes
        k32 = ctypes.windll.kernel32
        handle = k32.GetStdHandle(-11)  # STD_OUTPUT_HANDLE
        mode = ctypes.c_uint32()
        if not k32.GetConsoleMode(handle, ctypes.byref(mode)):
            return False
        return bool(k32.SetConsoleMode(handle, mode.value | 0x0004))
    except Exception:
        return False


_C = {
    "reset": "\033[0m", "bold": "\033[1m", "dim": "\033[2m",
    "green": "\033[32m", "yellow": "\033[33m", "red": "\033[31m",
    "cyan": "\033[36m",
}
if os.environ.get("NO_COLOR") or not sys.stdout.isatty() or not _enable_vt():
    _C = {k: "" for k in _C}

if FROZEN and IS_WIN:
    # PyInstaller (onefile) añade su carpeta temporal a la búsqueda de DLL y los
    # procesos hijos la heredan: un Python o un instalador lanzado desde aquí
    # podría cargar DLL equivocadas. Se restablece la búsqueda por defecto.
    try:
        import ctypes
        ctypes.windll.kernel32.SetDllDirectoryW(None)
    except Exception:
        pass


# ─────────────────────────────────────────────────────────────────────────────
# Idioma (i18n): español (es) y portugués de Brasil (pt). Catálogo en messages.py
# ─────────────────────────────────────────────────────────────────────────────

LANG = "es"  # se fija en main() vía _detect_lang()


def _detect_lang(argv: list[str]) -> str:
    """Resuelve el idioma: --lang explícito > idioma de Windows > env > es."""
    for i, a in enumerate(argv):
        v = None
        if a == "--lang" and i + 1 < len(argv):
            v = argv[i + 1].lower()
        elif a.startswith("--lang="):
            v = a.split("=", 1)[1].lower()
        if v in ("es", "pt"):
            return v
        if v == "auto":
            break
    if IS_WIN:
        try:
            import ctypes
            langid = ctypes.windll.kernel32.GetUserDefaultUILanguage()
            if langid & 0x3FF == 0x16:  # id primario 0x16 = portugués
                return "pt"
        except Exception:
            pass
    for var in ("LANGUAGE", "LC_ALL", "LC_MESSAGES", "LANG"):
        if os.environ.get(var, "").lower().startswith("pt"):
            return "pt"
    return "es"


def T(key: str, **kw) -> str:
    """Devuelve el mensaje `key` en el idioma activo, formateado con `kw`."""
    entry = MSG[key]
    return (entry.get(LANG) or entry["es"]).format(**kw)


# ─────────────────────────────────────────────────────────────────────────────
# Logger
# ─────────────────────────────────────────────────────────────────────────────

class Logger:
    """Escribe a consola y, a la vez, a un archivo de log auditable.

    En modo consola-solo (dry-run) no crea ningún archivo ni carpeta.
    """

    def __init__(self, log_path: Path, to_file: bool = True):
        self.log_path = log_path
        self._fh = None
        if to_file:
            log_path.parent.mkdir(parents=True, exist_ok=True)
            self._fh = log_path.open("a", encoding="utf-8")
        self.file("===== " + T("log.session", ts=_dt.datetime.now().isoformat())
                  + " =====")

    def file(self, msg: str) -> None:
        """Solo al archivo de log (detalle para diagnóstico)."""
        if self._fh:
            self._fh.write(msg + "\n")
            self._fh.flush()

    def _both(self, console: str, plain: str) -> None:
        print(console, flush=True)
        self.file(plain)

    def line(self, msg: str = "") -> None:
        self._both(msg, msg)

    def step(self, n: int, title: str) -> None:
        text = T("ui.step_prefix", n=n, title=title)
        self._both(f"\n{_C['bold']}{_C['cyan']}{text}{_C['reset']}", "\n" + text)

    def info(self, msg: str) -> None:
        self._both(f"  {msg}", f"  {msg}")

    def sub(self, msg: str) -> None:
        """Salida de un programa externo (atenuada en pantalla)."""
        self._both(f"    {_C['dim']}{msg}{_C['reset']}", f"    | {msg}")

    def ok(self, msg: str) -> None:
        self._both(f"  {_C['green']}✓{_C['reset']} {msg}", f"  [OK] {msg}")

    def warn(self, msg: str) -> None:
        self._both(f"  {_C['yellow']}⚠{_C['reset']}  {msg}", f"  [AVISO] {msg}")

    def err(self, msg: str) -> None:
        self._both(f"  {_C['red']}✗{_C['reset']} {msg}", f"  [ERROR] {msg}")

    def close(self) -> None:
        if self._fh:
            self._fh.close()
            self._fh = None


# ─────────────────────────────────────────────────────────────────────────────
# Configuración de la ejecución
# ─────────────────────────────────────────────────────────────────────────────

def _appdata() -> Path:
    return Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))


def _local_appdata() -> Path:
    return Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))


@dataclass
class Config:
    base_dir: Path            # raíz elegida por el usuario para todo
    qgis_profile: str         # perfil de QGIS a configurar ("auto" = el activo)
    steps: set[int]
    dry_run: bool
    non_interactive: bool
    skip_signature: bool
    plugin_url: str
    qgis_install: str = "auto"  # auto | msi (requiere admin) | user (sin admin)
    assume_installed: set[str] = field(default_factory=set)  # {'claude','qgis'}
    force_install: set[str] = field(default_factory=set)     # {'claude','qgis'}
    autostart: bool = False   # iniciar el servidor del plugin al abrir QGIS
    status: dict[int, str] = field(default_factory=dict)     # etiqueta por paso
    warnings: list[str] = field(default_factory=list)        # pendientes manuales
    pending: set[int] = field(default_factory=set)           # pasos con pendiente
    qgis_version: str | None = None     # versión detectada o instalada (paso 2)
    plugin_src: Path | None = None      # plugin extraído (paso 4 -> paso 5)
    uv_path: Path | None = None
    python_exe: Path | None = None      # CPython gestionado por uv (paso 3)

    # ── carpetas derivadas de la raíz ────────────────────────────────────
    @property
    def downloads_dir(self) -> Path:
        return self.base_dir / "downloads"

    @property
    def tools_dir(self) -> Path:
        return self.base_dir / "tools"

    @property
    def python_dir(self) -> Path:
        """CPython descargado por uv (no es el del sistema ni el de QGIS)."""
        return self.base_dir / "python"

    @property
    def env_dir(self) -> Path:
        """Entorno aislado del servidor: librerías + lanzador."""
        return self.base_dir / "env"

    @property
    def site_dir(self) -> Path:
        return self.env_dir / "site-packages"

    @property
    def launcher(self) -> Path:
        return self.env_dir / "run_server.py"

    @property
    def server_dir(self) -> Path:
        """Copia del código del servidor MCP (pyproject.toml + src/)."""
        return self.base_dir / "server"

    @property
    def logs_dir(self) -> Path:
        return self.base_dir / "logs"

    @property
    def user_qgis_root(self) -> Path:
        """Raíz de QGIS SIN administrador (OSGeo4W en carpeta del usuario)."""
        return self.base_dir / "qgis"

    # ── Claude Desktop ───────────────────────────────────────────────────
    def claude_config_paths(self) -> list[Path]:
        """Todos los claude_desktop_config.json que hay que escribir.

        La ruta clásica es %APPDATA%\\Claude. La versión MSIX de Claude Desktop
        puede, según el equipo, leer una copia virtualizada dentro de
        %LOCALAPPDATA%\\Packages\\Claude_*\\LocalCache\\Roaming\\Claude; si
        existe esa carpeta se escribe también ahí. Las otras ubicaciones
        reportadas (Claude-Data, Claude-3p) solo se tocan si YA contienen un
        archivo de configuración.
        """
        name = "claude_desktop_config.json"
        paths = [_appdata() / "Claude" / name]
        local = _local_appdata()
        packages = local / "Packages"
        if packages.is_dir():
            for pkg in sorted(packages.glob("Claude_*")):
                virt = pkg / "LocalCache" / "Roaming" / "Claude"
                if virt.is_dir():
                    paths.append(virt / name)
        for root in (local / "Claude-Data", local / "Claude-3p"):
            if root.is_dir():
                for cand in (root / name, *sorted(root.glob(f"*/{name}"))):
                    if cand.is_file():
                        paths.append(cand)
        seen: set[str] = set()
        unique = []
        for p in paths:
            key = str(p).lower()
            if key not in seen:
                seen.add(key)
                unique.append(p)
        return unique

    # ── QGIS: perfiles de destino ────────────────────────────────────────
    def qgis_targets(self) -> list[tuple[str, Path]]:
        """Perfiles de QGIS donde desplegar el plugin: [(mayor, carpeta_perfil)].

        Se cubre cada versión mayor que ya tenga carpeta de datos (QGIS3 y/o
        QGIS4) más la de la versión detectada o instalada en el paso 2. Así el
        plugin aparece sea cual sea el QGIS que la persona abra.
        """
        base = _appdata() / "QGIS"
        majors = [m for m in ("3", "4") if (base / f"QGIS{m}").is_dir()]
        vt = _version_tuple(self.qgis_version)
        if vt and str(vt[0]) in ("3", "4") and str(vt[0]) not in majors:
            majors.append(str(vt[0]))
        if not majors:
            majors = ["3"]
        targets = []
        for major in sorted(majors):
            profiles = base / f"QGIS{major}" / "profiles"
            names = [self.qgis_profile]
            if self.qgis_profile == "auto":
                names = active_qgis_profiles(profiles)
            targets += [(major, profiles / name) for name in names]
        return targets


def active_qgis_profiles(profiles_dir: Path) -> list[str]:
    """Perfil(es) que QGIS va a abrir, según su profiles.ini.

    QGIS decide el perfil de arranque con `selectionPolicy`:
      0 = el último usado (`lastProfile`)   ← valor por defecto desde QGIS 3.32
      1 = uno fijo (`defaultProfile`)
      2 = preguntar al abrir               → se cubren todos los perfiles
    Sin profiles.ini (QGIS nunca se abrió) el perfil es 'default'.
    """
    try:
        text = (profiles_dir / "profiles.ini").read_text(
            encoding="utf-8", errors="replace")
    except OSError:
        return ["default"]

    def key(name: str) -> str:
        m = re.search(rf"(?mi)^\s*{name}\s*=\s*(.*?)\s*$", text)
        return m.group(1).strip().strip('"') if m else ""

    def exists(name: str) -> bool:
        return bool(name) and (profiles_dir / name).is_dir()

    policy, last, default = key("selectionPolicy"), key("lastProfile"), key("defaultProfile")
    if policy == "2":
        every = sorted(d.name for d in profiles_dir.iterdir() if d.is_dir())
        return every or ["default"]
    order = (default, last) if policy == "1" or (not policy and default) else (last, default)
    for name in order:
        if exists(name):
            return [name]
    return ["default"]


# ─────────────────────────────────────────────────────────────────────────────
# Utilidades de sistema
# ─────────────────────────────────────────────────────────────────────────────

def _human(n: float) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024:
            return f"{n:.1f}{unit}"
        n /= 1024
    return f"{n:.1f}TB"


def _decode(raw: bytes) -> str:
    for enc in ("utf-8", "oem" if IS_WIN else "latin-1"):
        try:
            return raw.decode(enc)
        except (UnicodeDecodeError, LookupError):
            continue
    return raw.decode("latin-1", errors="replace")


def _sysroot() -> Path:
    return Path(os.environ.get("SystemRoot", r"C:\Windows"))


def _powershell_exe() -> str:
    exe = _sysroot() / "System32" / "WindowsPowerShell" / "v1.0" / "powershell.exe"
    return str(exe) if exe.exists() else "powershell"


def _ps(script: str, env_extra: dict[str, str] | None = None,
        timeout: int = 120) -> tuple[int, str, str]:
    """Ejecuta un script en Windows PowerShell. Devuelve (rc, stdout, stderr).

    Los valores variables (rutas) se pasan por variables de entorno, nunca
    interpolados en el texto del script: una ruta con apóstrofo no lo rompe.
    """
    env = dict(os.environ)
    # Si el instalador se lanzó desde PowerShell 7, PSModulePath apunta a sus
    # módulos y Windows PowerShell 5.1 no logra cargar los suyos.
    env.pop("PSModulePath", None)
    env.update(env_extra or {})
    try:
        out = subprocess.run(
            [_powershell_exe(), "-NoProfile", "-NonInteractive",
             "-ExecutionPolicy", "Bypass", "-Command", script],
            capture_output=True, timeout=timeout, env=env,
            stdin=subprocess.DEVNULL,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        return -1, "", str(exc)
    return out.returncode, _decode(out.stdout), _decode(out.stderr)


def run(cmd: list, log: Logger, env: dict[str, str] | None = None,
        cwd: Path | None = None, quiet: bool = False) -> int:
    """Ejecuta un programa mostrando y registrando su salida línea a línea.

    quiet=True: la salida completa va solo al log y en pantalla se muestra un
    avance cada 5000 líneas (para programas que escriben miles, como OSGeo4W).
    """
    cmd = [str(c) for c in cmd]
    log.file("  $ " + subprocess.list2cmdline(cmd))
    try:
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT,
                                stdin=subprocess.DEVNULL, env=env, cwd=cwd)
    except OSError as exc:
        log.err(T("run.fail", exe=cmd[0], exc=exc))
        return -1
    assert proc.stdout is not None
    count = 0
    for raw in proc.stdout:
        text = _decode(raw).rstrip()
        if not text:
            continue
        if quiet:
            log.file(f"    | {text}")
            count += 1
            if count % 5000 == 0:
                print(f"    {_C['dim']}" + T("run.progress", n=count) + _C["reset"],
                      flush=True)
        else:
            log.sub(text)
    rc = proc.wait()
    log.file(f"  -> rc={rc}")
    return rc


def _is_admin() -> bool:
    """True si el proceso corre con permisos de administrador (Windows)."""
    if not IS_WIN:
        return os.geteuid() == 0 if hasattr(os, "geteuid") else False
    try:
        import ctypes
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


def _version_tuple(v: str | None) -> tuple[int, ...]:
    if not v:
        return ()
    nums = []
    for part in v.split("."):
        digits = "".join(ch for ch in part if ch.isdigit())
        if not digits:
            break
        nums.append(int(digits))
    return tuple(nums)


QGIS_IMAGE_RE = re.compile(r"^qgis(-[a-z0-9]+)*-bin\.exe$", re.IGNORECASE)


def qgis_running() -> bool:
    """True si hay un QGIS abierto (qgis-bin.exe, qgis-ltr-bin.exe…).

    Se compara el nombre exacto del ejecutable: `qgis-mcp-installer.exe` (este
    mismo programa) también empieza por «qgis».
    """
    if not IS_WIN:
        return False
    try:
        out = subprocess.run(
            [str(_sysroot() / "System32" / "tasklist.exe"),
             "/FI", "IMAGENAME eq qgis*", "/FO", "CSV", "/NH"],
            capture_output=True, timeout=30, stdin=subprocess.DEVNULL)
    except (OSError, subprocess.SubprocessError):
        return False
    for line in _decode(out.stdout).splitlines():
        image = line.split(",", 1)[0].strip().strip('"')
        if QGIS_IMAGE_RE.match(image):
            return True
    return False


def claude_desktop_running() -> bool:
    """True si Claude Desktop está abierto.

    Se filtra por ruta: `claude.exe` también es el nombre de Claude Code (CLI),
    que no tiene nada que ver con este instalador.
    """
    if not IS_WIN:
        return False
    rc, out, _ = _ps(
        "Get-Process -Name claude -ErrorAction SilentlyContinue | "
        "Where-Object { $_.Path -match 'WindowsApps|AnthropicClaude|"
        "\\\\Programs\\\\claude' } | Select-Object -First 1 | "
        "ForEach-Object { 'RUNNING' }", timeout=60)
    return "RUNNING" in out


# ─────────────────────────────────────────────────────────────────────────────
# Descarga + verificación de integridad
# ─────────────────────────────────────────────────────────────────────────────

class DownloadError(Exception):
    """La descarga no pudo completarse (red, proxy, 404…)."""


def download(dl: "manifest.Download", dest_dir: Path, log: Logger,
             dry_run: bool) -> Path:
    """Descarga con reintentos y barra de progreso. Devuelve la ruta."""
    dest = dest_dir / dl.filename
    if dry_run:
        log.info(T("dl.dry", url=dl.url, dest=dest))
        return dest
    if dl.cache and dest.exists() and dest.stat().st_size > 0:
        log.ok(T("dl.cached", name=dest.name, size=_human(dest.stat().st_size)))
        return dest

    dest_dir.mkdir(parents=True, exist_ok=True)
    log.info(T("dl.downloading", name=dl.name))
    log.info(T("dl.from", url=dl.url))
    tmp = dest.with_name(dest.name + ".part")
    last: Exception | None = None
    for attempt in (1, 2, 3):
        try:
            _download_once(dl.url, tmp)
            tmp.replace(dest)
            log.ok(T("dl.done", name=dest.name, size=_human(dest.stat().st_size)))
            return dest
        except urllib.error.HTTPError as exc:
            last = exc
            if 400 <= exc.code < 500 and exc.code not in (408, 429):
                break  # 404/403: reintentar no lo arregla
        except (urllib.error.URLError, OSError, EOFError) as exc:
            last = exc
        finally:
            if tmp.exists():
                try:
                    tmp.unlink()
                except OSError:
                    pass
        if attempt < 3:
            log.warn(T("dl.retry", n=attempt, exc=last))
            time.sleep(3 * attempt)
    raise DownloadError(T("dl.fail", name=dl.name, exc=last))


def _download_once(url: str, tmp: Path) -> None:
    req = urllib.request.Request(
        url, headers={"User-Agent": f"qgis-mcp-etl/{__version__}"})
    tty = sys.stdout.isatty()
    with urllib.request.urlopen(req, timeout=60) as resp, tmp.open("wb") as fh:
        total = int(resp.headers.get("Content-Length") or 0)
        read = 0
        while True:
            chunk = resp.read(1024 * 256)
            if not chunk:
                break
            fh.write(chunk)
            read += len(chunk)
            if total and tty:
                sys.stdout.write(f"\r    {read / total * 100:5.1f}%  "
                                 f"{_human(read)}/{_human(total)}   ")
                sys.stdout.flush()
    if tty and total:
        sys.stdout.write("\n")
    if total and read != total:
        raise EOFError(f"descarga incompleta: {read} de {total} bytes")
    if read == 0:
        raise EOFError("descarga vacía")


def verify_sha256(path: Path, expected: str | None, log: Logger) -> bool:
    if not expected:
        return True
    import hashlib
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(block)
    actual = h.hexdigest()
    if actual.lower() == expected.lower():
        log.ok(T("sha.ok", h=actual[:16]))
        return True
    log.err(T("sha.bad", e=expected[:16], a=actual[:16]))
    return False


def verify_signature(path: Path, publisher_contains: str | None,
                     log: Logger, skip: bool) -> bool:
    """Verifica la firma Authenticode del binario (solo Windows)."""
    if publisher_contains is None:
        return True
    if skip:
        log.warn(T("sig.skipped"))
        return True
    if not IS_WIN:
        log.warn(T("sig.notwin"))
        return True
    rc, out, err = _ps(
        "$s = Get-AuthenticodeSignature -LiteralPath $env:QMI_SIG_PATH; "
        "Write-Output ([string]$s.Status); "
        "Write-Output ([string]$s.SignerCertificate.Subject)",
        {"QMI_SIG_PATH": str(path)}, timeout=180)
    if rc == -1:
        log.err(T("sig.execfail", exc=err))
        return False
    lines = [ln.strip() for ln in out.splitlines() if ln.strip()]
    status = lines[0] if lines else "Unknown"
    subject = lines[1] if len(lines) > 1 else ""
    if status != "Valid":
        log.err(T("sig.invalid", status=status))
        log.file("    " + err.strip())
        return False
    if publisher_contains.lower() not in subject.lower():
        log.err(T("sig.publisher", exp=publisher_contains, subj=subject))
        return False
    log.ok(T("sig.ok", subj=subject))
    return True


def fetch_verified(dl: "manifest.Download", cfg: Config, log: Logger) -> Path | None:
    """Descarga y verifica integridad (hash + firma). None si no es confiable.

    Un archivo que no pasa la verificación se BORRA: si se quedara en la caché,
    cada reintento volvería a fallar con el mismo archivo dañado.
    """
    path = download(dl, cfg.downloads_dir, log, cfg.dry_run)
    if cfg.dry_run:
        return path
    ok = verify_sha256(path, dl.sha256, log) and verify_signature(
        path, dl.expected_publisher_contains, log, cfg.skip_signature)
    if not ok:
        try:
            path.unlink()
        except OSError:
            pass
        log.warn(T("fetch.discarded", name=path.name))
        return None
    if dl.expected_size and abs(path.stat().st_size - dl.expected_size) > dl.expected_size * 0.5:
        log.warn(T("fetch.size", size=_human(path.stat().st_size)))
    return path


# ─────────────────────────────────────────────────────────────────────────────
# Detección de software ya instalado + confirmación del usuario
# ─────────────────────────────────────────────────────────────────────────────

def detect_claude() -> tuple[bool, str | None, Path | None]:
    """Busca Claude Desktop: paquete MSIX (actual) o instalación clásica."""
    if IS_WIN:
        rc, out, _ = _ps(
            "$p = Get-AppxPackage -Name '*Claude*' -ErrorAction SilentlyContinue | "
            "Where-Object { $_.Publisher -match 'Anthropic' -or $_.Name -eq 'Claude' } | "
            "Sort-Object Version -Descending | Select-Object -First 1; "
            "if ($p) { Write-Output ('MSIX|' + $p.Version + '|' + $p.InstallLocation) }",
            timeout=90)
        for ln in out.splitlines():
            if ln.startswith("MSIX|"):
                _, ver, loc = (ln.strip().split("|", 2) + ["", ""])[:3]
                return True, ver or None, Path(loc) if loc else None
    local = _local_appdata()
    for base in (local / "AnthropicClaude", local / "Programs" / "claude",
                 local / "Programs" / "Claude"):
        if not base.exists():
            continue
        # Los builds clásicos se despliegan en carpetas app-<version>.
        versions = sorted(
            (p.name[len("app-"):] for p in base.glob("app-*") if p.is_dir()),
            key=_version_tuple, reverse=True)
        ver = versions[0] if versions else None
        has_exe = (base / "Claude.exe").exists() or any(base.glob("*/Claude.exe"))
        if ver or has_exe:
            return True, ver, base
    return False, None, None


def _has_qgis_binary(root: Path) -> bool:
    """True si `root` contiene un QGIS ejecutable de verdad.

    Una desinstalación fallida deja la carpeta `QGIS x.y.z/bin` casi vacía; sin
    esta comprobación se daría QGIS por instalado y nunca se instalaría.
    """
    try:
        return any((root / "bin").glob("qgis*-bin.exe"))
    except OSError:
        return False


def detect_qgis(extra_roots: tuple[Path, ...] = ()) -> tuple[bool, str | None, Path | None]:
    """Busca una instalación de QGIS y su versión (la más reciente).

    Cubre las instalaciones a nivel máquina (Program Files, OSGeo4W en la raíz
    de un disco) y las de nivel usuario (OSGeo4W en el home o en la raíz elegida
    por el usuario, que es donde instala el paso 2 en modo sin-administrador).
    """
    roots: list[Path] = []
    for var in ("ProgramFiles", "ProgramW6432", "ProgramFiles(x86)"):
        val = os.environ.get(var)
        if val:
            roots.append(Path(val))
    roots += [Path(r"C:\Program Files"), Path(r"C:\Program Files (x86)")]
    found: list[tuple[tuple[int, ...], str | None, Path]] = []
    seen: set[str] = set()
    for root in roots:
        key = str(root).lower()
        if key in seen or not root.is_dir():
            continue
        seen.add(key)
        for d in root.glob("QGIS*"):
            if _has_qgis_binary(d):
                ver = d.name[4:].strip() or None
                found.append((_version_tuple(ver), ver, d))
    if found:
        found.sort(key=lambda t: t[0], reverse=True)
        return True, found[0][1], found[0][2]
    o4w_roots = [*extra_roots, Path.home() / "OSGeo4W"]
    for drive in ("C", "D", "E"):
        o4w_roots += [Path(f"{drive}:\\OSGeo4W"), Path(f"{drive}:\\OSGeo4W64")]
    for p in o4w_roots:
        if _has_qgis_binary(p):
            return True, None, p
    return False, None, None


def _ask(prompt: str) -> str:
    try:
        return input(prompt).strip()
    except EOFError:
        return ""


def confirm_installed(name: str, key: str,
                      detected: tuple[bool, str | None, Path | None],
                      cfg: Config, log: Logger) -> tuple[bool, str | None]:
    """Muestra la detección y pregunta al usuario si ya tiene el software.

    Devuelve (ya_lo_tiene, version). En modo no interactivo usa la detección
    automática. En interactivo, el usuario confirma y puede corregir la versión.
    """
    found, ver, loc = detected
    if found:
        detail = f" v{ver}" if ver else T("det.ver_unknown")
        log.info(T("det.found", name=name, detail=detail,
                   loc=(f"  ·  {loc}" if loc else "")))
    else:
        log.info(T("det.notfound", name=name))

    if key in cfg.force_install:
        log.info(T("det.force", name=name))
        return False, None
    if key in cfg.assume_installed:
        log.info(T("det.assume", name=name))
        return True, ver
    if cfg.non_interactive:
        return found, ver

    prompt_default = "S/n" if found else "s/N"
    ans = _ask(T("det.ask_have", name=name, d=prompt_default)).lower()
    if not ans:
        ans = "s" if found else "n"
    if ans not in YES:
        return False, None
    if found and ver:
        return True, ver
    typed = _ask(T("det.ask_ver", name=name, d=ver or T("det.dontknow")))
    return True, (typed or ver)


# ─────────────────────────────────────────────────────────────────────────────
# Entorno de Python: uv + CPython propio + venv
# ─────────────────────────────────────────────────────────────────────────────

def _uv_env(cfg: Config) -> dict[str, str]:
    """Entorno para `uv`: todo queda dentro de la raíz elegida por el usuario."""
    env = dict(os.environ)
    for var in ("VIRTUAL_ENV", "PYTHONHOME", "PYTHONPATH", "CONDA_PREFIX",
                "UV_PROJECT_ENVIRONMENT", "UV_PYTHON", "UV_NO_MANAGED_PYTHON"):
        env.pop(var, None)
    env.update({
        "UV_PYTHON_INSTALL_DIR": str(cfg.python_dir),
        "UV_CACHE_DIR": str(cfg.base_dir / "cache" / "uv"),
        "UV_MANAGED_PYTHON": "1",   # nunca el Python del sistema ni el de QGIS
        "UV_LINK_MODE": "copy",     # el venv no depende de la caché
        "UV_NO_CONFIG": "1",        # ignora uv.toml/pyproject del usuario
        "UV_NO_PROJECT": "1",
        "UV_NO_PROGRESS": "1",
        "UV_SYSTEM_CERTS": "1",     # usa los certificados de Windows (proxys corporativos)
    })
    return env


def ensure_uv(cfg: Config, log: Logger) -> Path | None:
    """Deja `uv` en <raíz>/tools/uv y devuelve su ruta. None si falla."""
    uv = cfg.tools_dir / "uv" / ("uv.exe" if IS_WIN else "uv")
    if uv.exists():
        try:
            out = subprocess.run([str(uv), "--version"], capture_output=True,
                                 timeout=60, stdin=subprocess.DEVNULL)
            if manifest.UV_VERSION in _decode(out.stdout):
                cfg.uv_path = uv
                log.ok(T("uv.present", v=manifest.UV_VERSION))
                return uv
        except (OSError, subprocess.SubprocessError):
            pass
    if not IS_WIN:
        log.err(T("uv.notwin"))
        return None
    try:
        archive = fetch_verified(manifest.UV, cfg, log)
    except DownloadError as exc:
        log.err(str(exc))
        return None
    if archive is None:
        return None
    uv.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(archive) as zf:
        for member in zf.infolist():
            name = Path(member.filename).name
            if member.is_dir() or not name.lower().endswith(".exe"):
                continue
            with zf.open(member) as src, (uv.parent / name).open("wb") as dst:
                shutil.copyfileobj(src, dst)
    if not uv.exists():
        log.err(T("uv.fail"))
        return None
    cfg.uv_path = uv
    log.ok(T("uv.ready", path=uv))
    return uv


def _python_ok(py: Path) -> bool:
    """True si `py` arranca y es >= la versión mínima del servidor."""
    try:
        out = subprocess.run(
            [str(py), "-I", "-c",
             "import sys; print(sys.version_info[0], sys.version_info[1])"],
            capture_output=True, timeout=120, stdin=subprocess.DEVNULL)
        major, minor = (int(x) for x in _decode(out.stdout).split()[:2])
    except (OSError, subprocess.SubprocessError, ValueError):
        return False
    return out.returncode == 0 and (major, minor) >= manifest.PYTHON_MIN


def find_managed_python(cfg: Config) -> Path | None:
    """El CPython que `uv` dejó en <raíz>/python (el más reciente), o None."""
    name = "python.exe" if IS_WIN else "bin/python3"
    cands = sorted(
        (p for p in cfg.python_dir.glob(f"cpython-{manifest.PYTHON_VERSION}*/{name}")
         if p.is_file()),
        key=lambda p: _version_tuple(p.parent.name.split("-")[1]), reverse=True)
    return cands[0] if cands else None


# Lanzador del servidor. Se escribe junto a site-packages y lo ubica por ruta
# relativa, así que no lleva ninguna ruta del equipo dentro.
LAUNCHER_SOURCE = """\
# Arranca el servidor MCP de QGIS. Generado por qgis-mcp-installer.
#
# Claude Desktop ejecuta:  <raiz>/python/cpython-.../python.exe -I run_server.py
#
# Se usa el python.exe real (no el lanzador de un entorno virtual) porque
# Windows con Smart App Control bloquea los ejecutables sin firma que crean los
# venv. Las librerias del servidor estan en la carpeta site-packages de al lado.
import site
import sys
from pathlib import Path

site.addsitedir(str(Path(__file__).resolve().parent / "site-packages"))

from qgis_mcp.server import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main())
"""


def ensure_python_env(cfg: Config, log: Logger) -> bool:
    """Deja listo el entorno aislado: uv, CPython propio y dependencias base.

    NO se crea un venv: el `python.exe` de un venv es un lanzador sin firma y
    Smart App Control (activo en muchas PC nuevas con Windows 11) lo bloquea.
    Se usa el `python.exe` real de la distribución y las librerías van a una
    carpeta propia (`env/site-packages`) que el lanzador añade al arrancar.
    """
    uv = ensure_uv(cfg, log)
    if uv is None:
        return False
    env = _uv_env(cfg)
    py = find_managed_python(cfg)
    if py is not None and _python_ok(py):
        log.ok(T("s3.reuse", py=py))
    else:
        log.info(T("s3.python", py=manifest.PYTHON_VERSION, dir=cfg.python_dir))
        rc = run([uv, "python", "install", "--no-bin", "--no-registry",
                  manifest.PYTHON_VERSION], log, env=env)
        py = find_managed_python(cfg)
        if rc != 0 or py is None:
            log.err(T("s3.pyerr"))
            return False
        if not _python_ok(py):
            log.err(T("s3.blocked", py=py))
            return False
    cfg.python_exe = py
    cfg.site_dir.mkdir(parents=True, exist_ok=True)
    log.info(T("s3.deps", deps=", ".join(manifest.RUNTIME_DEPENDENCIES)))
    rc = run([uv, "pip", "install", "--python", py, "--target", cfg.site_dir,
              *manifest.RUNTIME_DEPENDENCIES], log, env=env)
    if rc != 0:
        log.err(T("s3.depserr"))
        return False
    cfg.launcher.write_text(LAUNCHER_SOURCE, encoding="utf-8")
    return True


# ─────────────────────────────────────────────────────────────────────────────
# PASOS DEL ETL
# ─────────────────────────────────────────────────────────────────────────────

def step1_claude_desktop(cfg: Config, log: Logger) -> bool:
    log.step(1, T("s1.title"))
    has, ver = confirm_installed("Claude Desktop", "claude", detect_claude(), cfg, log)
    if has:
        cfg.status[1] = T("st.present", v=f" (v{ver})" if ver else "")
        log.ok(T("s1.existing_ok", v=f" (v{ver})" if ver else ""))
        return True

    if not cfg.dry_run:
        # Si %APPDATA%\Claude existe ANTES de instalar, la versión MSIX usa esa
        # carpeta en vez de una copia virtualizada; es donde escribe el paso 6.
        (_appdata() / "Claude").mkdir(parents=True, exist_ok=True)

    # El paquete MSIX de Claude registra un servicio de Windows y por eso solo
    # se puede instalar con administrador (sin él: error 0x80073D28). Sin
    # permisos no tiene sentido descargar 285 MB: se va directo a la guía manual
    # (el instalador normal de claude.com/download sí funciona sin administrador).
    if not _is_admin():
        log.info(T("s1.noadmin"))
        if cfg.dry_run:
            log.info(T("s1.dry_manual", url=manifest.CLAUDE_DOWNLOAD_PAGE))
            return True
        return _claude_manual(cfg, log)

    package = None
    try:
        package = fetch_verified(manifest.CLAUDE_DESKTOP, cfg, log)
    except DownloadError as exc:
        log.warn(str(exc))
    if cfg.dry_run:
        log.info(T("s1.dry"))
        return True

    if package is not None and _install_claude_msix(package, log):
        cfg.status[1] = T("st.installed")
        log.ok(T("s1.ok"))
        return True
    return _claude_manual(cfg, log)


def _install_claude_msix(package: Path, log: Logger) -> bool:
    """Instala el MSIX oficial con los comandos que documenta Anthropic
    (support.claude.com/en/articles/12622703): primero para todo el equipo
    y, si eso no aplica, para el usuario actual."""
    log.info(T("s1.running"))
    env = {"QMI_PKG": str(package), "QMI_FAM": manifest.CLAUDE_MSIX_FAMILY}
    rc, out, err = _ps(
        "Add-AppxProvisionedPackage -Online -PackagePath $env:QMI_PKG "
        "-SkipLicense -Regions 'all' -ErrorAction Stop | Out-Null; "
        "Add-AppxPackage -RegisterByFamilyName -MainPackage $env:QMI_FAM "
        "-ErrorAction SilentlyContinue", env, timeout=1800)
    log.file(f"  Add-AppxProvisionedPackage rc={rc}\n{out}{err}")
    if not detect_claude()[0]:
        rc, out, err = _ps("Add-AppxPackage -Path $env:QMI_PKG -ErrorAction Stop",
                           env, timeout=1800)
        log.file(f"  Add-AppxPackage rc={rc}\n{out}{err}")
    if detect_claude()[0]:
        return True
    reason = " ".join(ln.strip() for ln in err.splitlines()[:3] if ln.strip()) \
        or f"rc={rc}"
    log.warn(T("s1.autofail", reason=reason[:400]))
    return False


def _claude_manual(cfg: Config, log: Logger) -> bool:
    """Guía la instalación manual. No detiene la cadena: los pasos 2 a 7 no
    dependen de que Claude Desktop ya esté instalado."""
    url = manifest.CLAUDE_DOWNLOAD_PAGE
    log.warn(T("s1.manual", url=url))
    if not cfg.non_interactive:
        try:
            os.startfile(url)  # type: ignore[attr-defined]
        except (OSError, AttributeError):
            pass
        _ask(T("s1.manual_wait"))
        if detect_claude()[0]:
            cfg.status[1] = T("st.installed_manual")
            log.ok(T("s1.ok"))
            return True
    cfg.status[1] = T("st.manual_pending")
    cfg.pending.add(1)
    cfg.warnings.append(T("w.claude", url=url))
    return True


def step2_qgis(cfg: Config, log: Logger) -> bool:
    log.step(2, T("s2.title", v=manifest.QGIS_VERSION))
    has, ver = confirm_installed(
        "QGIS", "qgis", detect_qgis((cfg.user_qgis_root,)), cfg, log)
    if has:
        cfg.qgis_version = ver
        cfg.status[2] = T("st.present", v=f" (v{ver})" if ver else "")
        if _version_tuple(ver) and _version_tuple(ver) < (3, 28):
            log.warn(T("s2.old", v=ver))
        log.ok(T("s2.existing_ok", v=f" (v{ver})" if ver else ""))
        return True

    # El MSI oficial instala a nivel máquina y EXIGE administrador; sin admin
    # se usa el instalador de red OSGeo4W con --root en la carpeta del usuario.
    mode = cfg.qgis_install
    if mode == "auto":
        if _is_admin():
            mode = "msi"
            log.info(T("s2.mode_msi"))
        else:
            mode = "user"
            log.info(T("s2.mode_user"))

    if not cfg.dry_run:
        target = cfg.base_dir if mode == "user" else Path(
            os.environ.get("ProgramFiles", r"C:\Program Files"))
        try:
            probe = target if target.exists() else Path(target.anchor)
            free = shutil.disk_usage(probe).free
            if free < manifest.QGIS_MIN_FREE_BYTES:
                log.err(T("s2.nospace", free=_human(free),
                          need=_human(manifest.QGIS_MIN_FREE_BYTES), where=probe))
                return False
        except OSError:
            pass

    ok = _install_qgis_msi(cfg, log) if mode == "msi" else _install_qgis_user(cfg, log)
    if ok:
        cfg.qgis_version = manifest.QGIS_VERSION
    return ok


def _install_qgis_msi(cfg: Config, log: Logger) -> bool:
    """Vía clásica: MSI oficial de QGIS (requiere administrador/UAC)."""
    try:
        installer = fetch_verified(manifest.QGIS_LTR, cfg, log)
    except DownloadError as exc:
        log.err(str(exc))
        return False
    if installer is None:
        return False
    if cfg.dry_run:
        log.info(T("msi.dry"))
        return True
    log.info(T("msi.installing"))
    msi_log = cfg.logs_dir / "qgis-msi.log"
    rc = run([str(_sysroot() / "System32" / "msiexec.exe"), "/i", installer,
              "/qb", "/norestart", "/l*v", msi_log], log)
    if rc in (0, 3010):  # 3010 = éxito, requiere reinicio
        cfg.status[2] = T("st.installed_msi")
        log.ok(T("msi.ok"))
        return True
    log.err(T("msi.err", rc=rc, log=msi_log))
    if rc in (1602, 1603, 1625, 1730):
        log.warn(T("msi.perm_hint"))
    return False


def _install_qgis_user(cfg: Config, log: Logger) -> bool:
    """Vía SIN administrador: instalador de red OSGeo4W con --root del usuario.

    Es el mismo QGIS LTR oficial (paquete qgis-ltr-full, con Python/GDAL/
    processing); vive en una carpeta del usuario en vez de Program Files, así
    que no hay UAC. El setup se verifica por firma Authenticode de la OSGeo
    Foundation antes de ejecutarse.
    """
    try:
        setup = fetch_verified(manifest.OSGEO4W_SETUP, cfg, log)
    except DownloadError as exc:
        log.err(str(exc))
        return False
    if setup is None:
        return False
    root = cfg.user_qgis_root
    # Windows limita las rutas a 260 caracteres y OSGeo4W no usa rutas largas:
    # con una raíz profunda falla a media descarga ("Can't open … for writing").
    if len(str(root)) > manifest.OSGEO4W_MAX_ROOT_LEN:
        log.err(T("o4w.longpath", root=root, n=len(str(root)),
                  max=manifest.OSGEO4W_MAX_ROOT_LEN))
        return False
    pkg_cache = cfg.base_dir / "o4w"
    if len(str(pkg_cache)) > manifest.OSGEO4W_MAX_ROOT_LEN:
        pkg_cache = _local_appdata() / "qgis-mcp-o4w"
    cmd = [
        str(setup),
        "--advanced", "--arch", "x86_64",
        "--quiet-mode", "--autoaccept",
        "--site", manifest.OSGEO4W_SITE, "--only-site",
        "--root", str(root),
        "--local-package-dir", str(pkg_cache),
        "--packages", manifest.OSGEO4W_PACKAGES,
        "--menu-name", "QGIS LTR (usuario)",
    ]
    if cfg.dry_run:
        log.info(T("o4w.dry", root=root))
        log.info("  " + subprocess.list2cmdline(cmd))
        return True
    log.info(T("o4w.installing", root=root))
    log.info(T("o4w.big"))
    root.mkdir(parents=True, exist_ok=True)
    pkg_cache.mkdir(parents=True, exist_ok=True)
    # El setup no declara nivel de ejecución y Windows, por llamarse «setup»,
    # puede exigirle elevación (WinError 740, visto en campo el 2026-08-31).
    # RunAsInvoker le dice que corra con los permisos que ya tiene el usuario.
    env = dict(os.environ)
    env["__COMPAT_LAYER"] = "RunAsInvoker"
    rc = run(cmd, log, env=env, quiet=True)
    qgis_bin = next((root / "bin").glob("qgis*-bin.exe"), None) \
        if (root / "bin").exists() else None
    if rc == 0 and qgis_bin is not None:
        cfg.status[2] = T("st.installed_user", root=root)
        log.ok(T("o4w.ok", root=root, bin=qgis_bin.name))
        log.info(T("o4w.open", bat=root / "bin" / "qgis-ltr.bat"))
        return True
    o4w_log = next((p for p in (root / "var" / "log" / "setup.log.full",
                                root / "setup.log.full") if p.is_file()),
                   root / "setup.log.full")
    log.err(T("o4w.err", rc=rc,
              nobin=("" if qgis_bin else T("o4w.nobin")), log=o4w_log))
    return False


def step3_python_env(cfg: Config, log: Logger) -> bool:
    log.step(3, T("s3.title"))
    if cfg.dry_run:
        log.info(T("s3.dry", uv=manifest.UV_VERSION, py=manifest.PYTHON_VERSION,
                   env=cfg.env_dir,
                   deps=", ".join(manifest.RUNTIME_DEPENDENCIES)))
        return True
    if not ensure_python_env(cfg, log):
        return False
    cfg.status[3] = T("st.venv", py=manifest.PYTHON_VERSION)
    log.ok(T("s3.ok"))
    return True


def _safe_extract(zip_path: Path, dest: Path) -> None:
    """Extrae un ZIP rechazando rutas que escapen de `dest`."""
    dest_res = dest.resolve()
    with zipfile.ZipFile(zip_path) as zf:
        for member in zf.infolist():
            target = (dest / member.filename).resolve()
            if dest_res != target and dest_res not in target.parents:
                raise ValueError(f"ruta insegura en el ZIP: {member.filename}")
        zf.extractall(dest)


def _find_repo_root(extract_dir: Path) -> Path | None:
    """Carpeta del repo dentro del ZIP: la que contiene qgis_mcp_plugin/."""
    marker = Path(manifest.PLUGIN_DIRNAME) / "metadata.txt"
    for cand in (extract_dir, *sorted(p for p in extract_dir.iterdir() if p.is_dir())):
        if (cand / marker).is_file():
            return cand
    return None


def _metadata_version(metadata: Path) -> str | None:
    try:
        text = metadata.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None
    m = re.search(r"(?m)^version\s*=\s*(\S+)", text)
    return m.group(1) if m else None


def _project_name(pyproject: Path) -> str:
    try:
        text = pyproject.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return "qgis-mcp"
    m = re.search(r'(?ms)^\[project\].*?^name\s*=\s*"([^"]+)"', text)
    return m.group(1) if m else "qgis-mcp"


def step4_plugin(cfg: Config, log: Logger) -> bool:
    log.step(4, T("s4.title"))
    dl = manifest.PLUGIN_FORK
    if cfg.plugin_url:
        dl = manifest.Download(key=dl.key, name=dl.name, url=cfg.plugin_url,
                               filename="qgis-mcp-custom.zip", cache=False)
        log.info(T("s4.url", url=cfg.plugin_url))

    zip_path = None
    try:
        zip_path = fetch_verified(dl, cfg, log)
    except DownloadError as exc:
        log.warn(T("s4.forkfail", exc=exc))
    if zip_path is None and not cfg.dry_run:
        log.warn(T("s4.fallback"))
        try:
            zip_path = fetch_verified(manifest.PLUGIN_UPSTREAM, cfg, log)
        except DownloadError as exc:
            log.err(str(exc))
            return False
    if cfg.dry_run:
        log.info(T("s4.dry", server=cfg.server_dir))
        return True
    if zip_path is None:
        return False

    extract_dir = cfg.downloads_dir / "plugin_extract"
    shutil.rmtree(extract_dir, ignore_errors=True)
    try:
        _safe_extract(zip_path, extract_dir)
    except (zipfile.BadZipFile, ValueError, OSError) as exc:
        log.err(T("s4.badzip", exc=exc))
        return False
    repo_root = _find_repo_root(extract_dir)
    if repo_root is None:
        log.err(T("s4.nometa"))
        return False
    plugin_src = repo_root / manifest.PLUGIN_DIRNAME
    version = _metadata_version(plugin_src / "metadata.txt") or "?"

    if not (repo_root / "src").is_dir() or not (repo_root / "pyproject.toml").is_file():
        log.err(T("s4.nosrc"))
        return False

    # Copia auditable del servidor: pyproject.toml + src/ (+ lo que el empaquetado
    # necesita). Es lo que se instala en el entorno aislado.
    shutil.rmtree(cfg.server_dir, ignore_errors=True)
    cfg.server_dir.mkdir(parents=True, exist_ok=True)
    shutil.copytree(repo_root / "src", cfg.server_dir / "src")
    for extra in ("pyproject.toml", "uv.lock", ".python-version", "README.md",
                  "LICENSE", "NOTICE"):
        if (repo_root / extra).is_file():
            shutil.copy2(repo_root / extra, cfg.server_dir / extra)
    log.ok(T("s4.servercopied", dir=cfg.server_dir))

    # Instalar el servidor en el entorno (lo prepara si el paso 3 no corrió).
    if not (cfg.python_exe and cfg.uv_path):
        if not ensure_python_env(cfg, log):
            return False
    assert cfg.uv_path is not None and cfg.python_exe is not None
    log.info(T("s4.installing"))
    rc = run([cfg.uv_path, "pip", "install", "--python", cfg.python_exe,
              "--target", cfg.site_dir,
              "--reinstall-package", _project_name(cfg.server_dir / "pyproject.toml"),
              cfg.server_dir, *manifest.RUNTIME_DEPENDENCIES],
             log, env=_uv_env(cfg))
    if rc != 0:
        log.err(T("s4.installerr"))
        return False

    cfg.plugin_src = plugin_src
    cfg.status[4] = f"v{version}"
    log.ok(T("s4.ok", v=version))
    return True


def set_ini_value(text: str, section: str, key: str, value: str) -> str:
    """Devuelve el INI con `key=value` dentro de `[section]`.

    Edición de texto mínima y deliberada: QGIS3.ini es un INI de Qt (claves con
    barras, dos puntos, porcentajes) y pasarlo por configparser lo reescribe
    entero y puede corromperlo. Aquí solo se toca UNA línea; el resto queda
    byte a byte (se corta solo por "\n", nunca con splitlines, que también
    parte en retornos de carro sueltos y otros separadores dentro de un valor).
    """
    cr = "\r" if "\r\n" in text else ""
    wanted = f"{key}={value}{cr}"
    lines = text.split("\n")  # el último elemento es "" si el texto acaba en \n

    def clean(line: str) -> str:
        return line[:-1] if line.endswith("\r") else line

    header = next((i for i, ln in enumerate(lines)
                   if clean(ln).strip() == f"[{section}]"), None)
    if header is None:
        if lines[-1] != "":           # el archivo no acababa en salto de línea
            lines[-1] += cr
            lines.append("")
        if len(lines) >= 2 and clean(lines[-2]).strip():
            lines.insert(len(lines) - 1, cr)   # línea en blanco de separación
        lines[len(lines) - 1:len(lines) - 1] = [f"[{section}]{cr}", wanted]
    else:
        key_re = re.compile(rf"^\s*{re.escape(key)}\s*=")
        i = header + 1
        while i < len(lines) and not clean(lines[i]).lstrip().startswith("["):
            if key_re.match(clean(lines[i])):
                lines[i] = wanted
                break
            i += 1
        else:
            if cr and not lines[header].endswith("\r"):
                lines[header] += cr
            lines.insert(header + 1, wanted)
    out = "\n".join(lines)
    return out if out.endswith("\n") else out + "\n"


def enable_plugin_in_ini_text(text: str, plugin: str) -> str:
    """Devuelve el contenido de QGIS3.ini con `plugin=true` en [PythonPlugins]."""
    return set_ini_value(text, "PythonPlugins", plugin, "true")


def plugin_enabled_in_ini_text(text: str, plugin: str) -> bool:
    """True si [PythonPlugins] contiene `plugin=true`."""
    in_section = False
    key_re = re.compile(rf"^\s*{re.escape(plugin)}\s*=\s*true\s*$", re.IGNORECASE)
    for line in text.splitlines():
        if line.lstrip().startswith("["):
            in_section = line.strip() == "[PythonPlugins]"
        elif in_section and key_re.match(line):
            return True
    return False


def _enable_plugin_in_ini(ini: Path, plugin: str, log: Logger,
                          autostart: bool = False) -> None:
    """Habilita el plugin en el INI del perfil; lo crea si QGIS nunca se abrió.

    Con autostart=True deja además `qgis_mcp/autostart=true`, la preferencia del
    propio plugin «Auto-start on startup».
    """
    existed = ini.exists()
    text = ini.read_bytes().decode("utf-8", errors="surrogateescape") if existed else ""
    new = enable_plugin_in_ini_text(text, plugin)
    if autostart:
        new = set_ini_value(new, "qgis_mcp", "autostart", "true")
    if not existed:
        ini.parent.mkdir(parents=True, exist_ok=True)
        ini.write_bytes(new.encode("utf-8"))
        log.ok(T("ini.created", ini=ini))
    elif new == text:
        log.ok(T("ini.already", ini=ini.name))
    else:
        backup = ini.with_name(
            f"{ini.name}.bak-qgismcp-{_dt.datetime.now():%Y%m%d%H%M%S}")
        shutil.copy2(ini, backup)
        ini.write_bytes(new.encode("utf-8", errors="surrogateescape"))
        log.ok(T("ini.enabled", ini=ini.name, bak=backup.name))
    if autostart:
        log.ok(T("ini.autostart"))


def step5_configure_qgis(cfg: Config, log: Logger) -> bool:
    log.step(5, T("s5.title"))
    targets = cfg.qgis_targets() if cfg.qgis_version or cfg.dry_run else None
    if targets is None:
        # El paso 2 no corrió en esta ejecución: se detecta QGIS aquí.
        _, ver, _ = detect_qgis((cfg.user_qgis_root,))
        cfg.qgis_version = ver
        targets = cfg.qgis_targets()

    if cfg.dry_run:
        for major, profile in targets:
            log.info(T("s5.dry_copy", dest=profile / "python" / "plugins"
                       / manifest.PLUGIN_DIRNAME))
            log.info(T("s5.dry_enable", ini=profile / "QGIS" / f"QGIS{major}.ini"))
        return True

    plugin_src = cfg.plugin_src
    if plugin_src is None:
        # Permite ejecutar el paso 5 aislado si el plugin ya se extrajo antes.
        extract_dir = cfg.downloads_dir / "plugin_extract"
        root = _find_repo_root(extract_dir) if extract_dir.is_dir() else None
        plugin_src = root / manifest.PLUGIN_DIRNAME if root else None
    if plugin_src is None or not (plugin_src / "metadata.txt").is_file():
        log.err(T("s5.notfound"))
        return False

    if qgis_running():
        log.warn(T("s5.qgis_open"))
        if not cfg.non_interactive:
            _ask(T("s5.qgis_wait"))

    for major, profile in targets:
        dest = profile / "python" / "plugins" / manifest.PLUGIN_DIRNAME
        try:
            dest.parent.mkdir(parents=True, exist_ok=True)
            if dest.exists() or dest.is_symlink():
                if dest.is_symlink():
                    dest.unlink()
                else:
                    shutil.rmtree(dest)
            shutil.copytree(plugin_src, dest,
                            ignore=shutil.ignore_patterns("__pycache__"))
        except OSError as exc:
            log.err(T("s5.copyerr", dest=dest, exc=exc))
            return False
        log.ok(T("s5.copied", dest=dest))
        try:
            _enable_plugin_in_ini(profile / "QGIS" / f"QGIS{major}.ini",
                                  manifest.PLUGIN_DIRNAME, log, cfg.autostart)
        except OSError as exc:
            log.warn(T("s5.iniwarn", exc=exc))
            cfg.warnings.append(T("w.enable"))
    cfg.status[5] = ", ".join(f"QGIS{m}/{p.name}" for m, p in targets)
    log.ok(T("s5.ok"))
    return True


def server_entry(cfg: Config) -> dict | None:
    """Entrada de mcpServers: el CPython propio + el lanzador, por ruta absoluta.

    No depende del PATH ni del directorio de trabajo (Claude Desktop lanza los
    servidores sin ver el PATH del usuario) ni de que `uv` siga instalado.
    `-I` aísla al intérprete de PYTHONPATH y del site del usuario. None si el
    paso 3 todavía no dejó un Python.
    """
    py = cfg.python_exe or find_managed_python(cfg)
    if py is None:
        return None
    return {"command": str(py), "args": ["-I", str(cfg.launcher)]}


def merge_claude_config(existing: str | None, entry: dict | None,
                        name: str = manifest.MCP_SERVER_NAME) -> tuple[str, bool]:
    """Fusiona `entry` en el JSON existente sin tocar lo demás.

    entry=None elimina la entrada. Devuelve (json_nuevo, era_invalido).
    """
    data: dict = {}
    invalid = False
    if existing is not None and existing.strip():
        try:
            loaded = json.loads(existing)
            if isinstance(loaded, dict):
                data = loaded
            else:
                invalid = True
        except json.JSONDecodeError:
            invalid = True
    servers = data.get("mcpServers")
    if not isinstance(servers, dict):
        servers = {}
    if entry is None:
        servers.pop(name, None)
    else:
        servers[name] = entry
    data["mcpServers"] = servers
    return json.dumps(data, indent=2, ensure_ascii=False) + "\n", invalid


def _write_claude_config(path: Path, entry: dict | None, log: Logger) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    existing = None
    if path.exists():
        # utf-8-sig: un config editado con el Bloc de notas o PowerShell trae BOM
        # y json lo rechazaría; no es motivo para perder los otros servidores.
        existing = path.read_text(encoding="utf-8-sig", errors="replace")
    new, invalid = merge_claude_config(existing, entry)
    if existing is not None:
        if new == existing and not path.read_bytes().startswith(b"\xef\xbb\xbf"):
            log.ok(T("s6.unchanged", path=path))
            return
        backup = path.with_name(f"{path.name}.bak-{_dt.datetime.now():%Y%m%d%H%M%S}")
        shutil.copy2(path, backup)
        log.ok(T("s6.backup", name=backup.name))
    if invalid:
        log.warn(T("s6.badjson"))
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(new, encoding="utf-8")
    tmp.replace(path)
    log.ok(T("s6.written", path=path))


def step6_configure_claude(cfg: Config, log: Logger) -> bool:
    log.step(6, T("s6.title"))
    entry = server_entry(cfg)
    paths = cfg.claude_config_paths()
    if cfg.dry_run:
        entry = entry or {
            "command": str(cfg.python_dir / "cpython-3.12.x" / "python.exe"),
            "args": ["-I", str(cfg.launcher)]}
        for p in paths:
            log.info(T("s6.dry", path=p))
        log.info("  " + json.dumps(
            {"mcpServers": {manifest.MCP_SERVER_NAME: entry}}, indent=2
        ).replace("\n", "\n    "))
        return True
    if entry is None or not cfg.launcher.is_file() or not (
            cfg.site_dir / "qgis_mcp").is_dir():
        log.err(T("s6.noenv"))
        return False
    for p in paths:
        try:
            _write_claude_config(p, entry, log)
        except OSError as exc:
            log.err(T("s6.writeerr", path=p, exc=exc))
            return False
    if claude_desktop_running():
        log.warn(T("s6.restart"))
        cfg.warnings.append(T("w.restart"))
    cfg.status[6] = T("st.configs", n=len(paths))
    return True


# ─────────────────────────────────────────────────────────────────────────────
# Verificación: el servidor MCP tiene que responder de verdad
# ─────────────────────────────────────────────────────────────────────────────

def mcp_handshake(command: str, args: list[str], timeout: float = 120.0,
                  extra_env: dict[str, str] | None = None
                  ) -> tuple[bool, str, int, str]:
    """Arranca el servidor como lo haría Claude Desktop y hace el saludo MCP.

    PATH mínimo y directorio de trabajo neutro: si el servidor solo funciona
    con el PATH del usuario, en Claude no va a arrancar. Devuelve
    (ok, nombre_servidor, n_herramientas, cola_de_stderr).
    """
    env = dict(os.environ)
    sysroot = str(_sysroot())
    env["PATH"] = os.pathsep.join([str(Path(sysroot) / "System32"), sysroot]) \
        if IS_WIN else env.get("PATH", "")
    for var in ("PYTHONHOME", "PYTHONPATH", "VIRTUAL_ENV"):
        env.pop(var, None)
    env.update(extra_env or {})
    try:
        proc = subprocess.Popen(
            [command, *args], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, env=env, cwd=sysroot if IS_WIN else None)
    except OSError as exc:
        return False, "", 0, str(exc)

    stderr_chunks: list[bytes] = []
    replies: list[bytes] = []
    have_reply = threading.Condition()

    def _drain_err() -> None:
        assert proc.stderr is not None
        for chunk in proc.stderr:
            stderr_chunks.append(chunk)

    def _read_out() -> None:
        assert proc.stdout is not None
        for raw in proc.stdout:
            with have_reply:
                replies.append(raw)
                have_reply.notify_all()
        with have_reply:
            replies.append(b"")  # EOF
            have_reply.notify_all()

    threading.Thread(target=_drain_err, daemon=True).start()
    threading.Thread(target=_read_out, daemon=True).start()
    deadline = time.monotonic() + timeout

    def _send(obj: dict) -> None:
        assert proc.stdin is not None
        proc.stdin.write((json.dumps(obj) + "\n").encode("utf-8"))
        proc.stdin.flush()

    def _reply(req_id: int) -> dict | None:
        idx = 0
        while True:
            with have_reply:
                while idx >= len(replies):
                    remaining = deadline - time.monotonic()
                    if remaining <= 0 or not have_reply.wait(remaining):
                        return None
                raw = replies[idx]
                idx += 1
            if raw == b"":
                return None
            try:
                msg = json.loads(raw)
            except ValueError:
                continue  # línea que no es JSON-RPC
            if isinstance(msg, dict) and msg.get("id") == req_id:
                return msg

    name, n_tools, ok = "", 0, False
    try:
        _send({"jsonrpc": "2.0", "id": 1, "method": "initialize",
               "params": {"protocolVersion": "2025-06-18", "capabilities": {},
                          "clientInfo": {"name": "qgis-mcp-installer",
                                         "version": __version__}}})
        first = _reply(1)
        if first and "result" in first:
            info = first["result"].get("serverInfo") or {}
            name = f"{info.get('name', '?')} {info.get('version', '')}".strip()
            _send({"jsonrpc": "2.0", "method": "notifications/initialized"})
            _send({"jsonrpc": "2.0", "id": 2, "method": "tools/list"})
            second = _reply(2)
            if second and "result" in second:
                n_tools = len(second["result"].get("tools") or [])
                ok = n_tools > 0
    except OSError:
        pass
    finally:
        try:
            proc.kill()
        except OSError:
            pass
        try:
            proc.wait(15)
        except subprocess.SubprocessError:
            pass
    tail = _decode(b"".join(stderr_chunks))[-1500:]
    return ok, name, n_tools, tail


def _qgis_port_open(port: int = 9876) -> bool:
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=1.5):
            return True
    except OSError:
        return False


def step7_verify(cfg: Config, log: Logger) -> bool:
    log.step(7, T("s7.title"))
    if cfg.dry_run:
        log.info(T("s7.dry"))
        return True
    ok = True

    # 1) Plugin desplegado y habilitado en cada perfil de destino.
    if not cfg.qgis_version:
        _, cfg.qgis_version, _ = detect_qgis((cfg.user_qgis_root,))
    for major, profile in cfg.qgis_targets():
        plugin = profile / "python" / "plugins" / manifest.PLUGIN_DIRNAME
        ini = profile / "QGIS" / f"QGIS{major}.ini"
        if (plugin / "metadata.txt").is_file() and (plugin / "__init__.py").is_file():
            ver = _metadata_version(plugin / "metadata.txt") or "?"
            log.ok(T("s7.plugin_ok", v=ver, dest=plugin))
        else:
            log.err(T("s7.plugin_bad", dest=plugin))
            ok = False
        enabled = ini.is_file() and plugin_enabled_in_ini_text(
            ini.read_text(encoding="utf-8", errors="replace"),
            manifest.PLUGIN_DIRNAME)
        if enabled:
            log.ok(T("s7.ini_ok", ini=ini))
        else:
            log.err(T("s7.ini_bad", ini=ini))
            ok = False

    # 2) Cada config de Claude contiene la entrada y el ejecutable existe.
    entry = None
    for path in cfg.claude_config_paths():
        try:
            data = json.loads(path.read_text(encoding="utf-8-sig"))
            found = data["mcpServers"][manifest.MCP_SERVER_NAME]
            command = found["command"]
        except (OSError, ValueError, KeyError, TypeError):
            log.err(T("s7.cfg_bad", path=path))
            ok = False
            continue
        if not Path(command).is_file():
            log.err(T("s7.cmd_missing", cmd=command, path=path))
            ok = False
            continue
        log.ok(T("s7.cfg_ok", path=path))
        entry = entry or found

    # 3) El servidor MCP arranca y responde, lanzado como lo lanza Claude.
    if entry is not None:
        log.info(T("s7.starting"))
        good, name, n_tools, tail = mcp_handshake(
            entry["command"], list(entry.get("args") or []),
            extra_env=entry.get("env"))
        if good:
            log.ok(T("s7.server_ok", name=name, n=n_tools))
        else:
            log.err(T("s7.server_bad"))
            for ln in tail.splitlines()[-12:]:
                log.sub(ln)
            ok = False

    # 4) Informativo: ¿QGIS ya está escuchando?
    if _qgis_port_open():
        log.ok(T("s7.port_open"))
    else:
        log.info(T("s7.port_closed"))

    cfg.status[7] = T("st.verified") if ok else T("st.verify_failed")
    return ok


STEPS = {
    1: step1_claude_desktop,
    2: step2_qgis,
    3: step3_python_env,
    4: step4_plugin,
    5: step5_configure_qgis,
    6: step6_configure_claude,
    7: step7_verify,
}


# ─────────────────────────────────────────────────────────────────────────────
# Desinstalación (solo lo que este instalador puso)
# ─────────────────────────────────────────────────────────────────────────────

def uninstall(cfg: Config, log: Logger) -> bool:
    """Quita el plugin de los perfiles y la entrada 'qgis' de Claude.

    No desinstala Claude Desktop ni QGIS, y no borra la carpeta raíz: eso lo
    decide la persona (se le indica la ruta).
    """
    log.line("\n" + T("un.title"))
    _, cfg.qgis_version, _ = detect_qgis((cfg.user_qgis_root,))
    for major, profile in cfg.qgis_targets():
        plugin = profile / "python" / "plugins" / manifest.PLUGIN_DIRNAME
        if cfg.dry_run:
            log.info(T("un.dry", path=plugin))
            continue
        if plugin.exists():
            try:
                shutil.rmtree(plugin)
                log.ok(T("un.removed", path=plugin))
            except OSError as exc:
                log.err(T("s5.copyerr", dest=plugin, exc=exc))
                return False
    for path in cfg.claude_config_paths():
        if not path.is_file():
            continue
        if cfg.dry_run:
            log.info(T("un.dry", path=f"{path} -> mcpServers.{manifest.MCP_SERVER_NAME}"))
            continue
        try:
            _write_claude_config(path, None, log)
        except OSError as exc:
            log.err(T("s6.writeerr", path=path, exc=exc))
            return False
    log.info(T("un.basedir", path=cfg.base_dir))
    return True


# ─────────────────────────────────────────────────────────────────────────────
# Interfaz de usuario / arranque
# ─────────────────────────────────────────────────────────────────────────────

def banner() -> str:
    line = "+" + "=" * 62 + "+"
    rows = [T("ui.banner1", v=__version__), T("ui.banner2")]
    body = "\n".join("|" + ("   " + r).ljust(62)[:62] + "|" for r in rows)
    return f"\n{line}\n{body}\n{line}\n"


def parse_steps(spec: str) -> set[int]:
    """'4,5,6' o '3-7' o '' (todos) -> {…}. ValueError si hay un paso inválido."""
    if not spec.strip():
        return set(ALL_STEPS)
    steps: set[int] = set()
    for part in spec.split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            lo, hi = part.split("-", 1)
            steps.update(range(int(lo), int(hi) + 1))
        else:
            steps.add(int(part))
    bad = sorted(s for s in steps if s not in ALL_STEPS)
    if bad or not steps:
        raise ValueError(", ".join(map(str, bad)) or spec)
    return steps


def _csv_set(value: str) -> set[str]:
    return {s.strip().lower() for s in value.split(",") if s.strip()}


def build_config(args: argparse.Namespace) -> Config:
    base = Path(args.base_dir).expanduser() if args.base_dir else \
        Path.home() / "qgis-mcp"
    if not args.non_interactive and not args.base_dir:
        print(banner())
        print(T("ui.choose"))
        raw = _ask(T("ui.rootdir") + f"\n  [{base}]: ")
        if raw:
            base = Path(raw.strip('"')).expanduser()
    return Config(
        base_dir=base.resolve() if base.is_absolute() else (Path.cwd() / base).resolve(),
        qgis_profile=args.profile,
        steps=parse_steps(args.steps),
        dry_run=args.dry_run,
        non_interactive=args.non_interactive,
        skip_signature=args.skip_signature,
        plugin_url=args.plugin_url or os.environ.get("QGIS_MCP_PLUGIN_URL", ""),
        qgis_install=args.qgis_install,
        assume_installed=_csv_set(args.assume_installed),
        force_install=_csv_set(args.force_install),
        autostart=args.autostart,
    )


def _pause_if_double_clicked(args: argparse.Namespace | None) -> None:
    """Si es el .exe abierto con doble clic, no cerrar la ventana de golpe."""
    if FROZEN and not (args and args.non_interactive) and sys.stdin and sys.stdin.isatty():
        _ask("\n" + T("ui.pressenter"))


def main(argv: list[str] | None = None) -> int:
    global LANG
    argv = sys.argv[1:] if argv is None else argv
    LANG = _detect_lang(argv)
    parser = argparse.ArgumentParser(description=T("h.desc"))
    parser.add_argument("--version", action="version",
                        version=f"qgis-mcp-installer {__version__}")
    parser.add_argument("--base-dir", help=T("h.basedir"))
    parser.add_argument("--profile", default="auto", help=T("h.profile"))
    parser.add_argument("--steps", default="", help=T("h.steps"))
    parser.add_argument("--plugin-url", default="", help=T("h.pluginurl"))
    parser.add_argument("--assume-installed", default="", help=T("h.assume"))
    parser.add_argument("--force-install", default="", help=T("h.force"))
    parser.add_argument("--qgis-install", default="auto",
                        choices=("auto", "msi", "user"), help=T("h.qgisinstall"))
    parser.add_argument("--lang", default="auto", choices=("auto", "es", "pt"),
                        help=T("h.lang"))
    parser.add_argument("--non-interactive", action="store_true",
                        help=T("h.noninteractive"))
    parser.add_argument("--dry-run", action="store_true", help=T("h.dryrun"))
    parser.add_argument("--skip-signature", action="store_true",
                        help=T("h.skipsig"))
    parser.add_argument("--autostart", action="store_true", help=T("h.autostart"))
    parser.add_argument("--uninstall", action="store_true", help=T("h.uninstall"))
    args = parser.parse_args(argv)

    try:
        cfg = build_config(args)
    except ValueError as exc:
        print(T("ui.badsteps", v=exc))
        _pause_if_double_clicked(args)
        return 1

    try:
        log = Logger(cfg.logs_dir / f"install-{_dt.datetime.now():%Y%m%d-%H%M%S}.log",
                     to_file=not cfg.dry_run)
    except OSError as exc:
        print(T("ui.badbase", path=cfg.base_dir, exc=exc))
        _pause_if_double_clicked(args)
        return 1

    try:
        code = _run(cfg, log, args)
    except KeyboardInterrupt:
        log.err(T("ui.interrupted"))
        code = 130
    finally:
        log.close()
    _pause_if_double_clicked(args)
    return code


def _run(cfg: Config, log: Logger, args: argparse.Namespace) -> int:
    print(banner())
    # Diagnóstico para soporte: queda en el log, no molesta en pantalla.
    log.file(f"  instalador={__version__} frozen={FROZEN} admin={_is_admin()} "
             f"lang={LANG}")
    log.file(f"  sistema={platform.platform()} python={sys.version.split()[0]} "
             f"exe={sys.executable}")
    log.file(f"  argv={sys.argv[1:]}")

    log.info(T("ui.root", v=cfg.base_dir))
    log.info(T("ui.profile", v=cfg.qgis_profile))
    log.info(T("ui.qgismode", v=cfg.qgis_install,
               extra=(T("ui.qgismode_user") if cfg.qgis_install == "user" else "")))
    log.info(T("ui.steps", v=sorted(cfg.steps)))
    log.info(T("ui.lang"))
    log.info(T("ui.mode", v=T("ui.mode_dry") if cfg.dry_run else T("ui.mode_real")))
    if cfg.skip_signature:
        log.warn(T("ui.sigoff"))
    if not IS_WIN and not cfg.dry_run:
        log.err(T("ui.notwin"))
        return 1

    if not cfg.non_interactive and not cfg.dry_run:
        if _ask(T("ui.continue")).lower() in NO:
            log.info(T("ui.cancelled"))
            return 130

    if args.uninstall:
        return 0 if uninstall(cfg, log) else 1

    results: dict[int, bool] = {}
    for n in sorted(cfg.steps):
        try:
            results[n] = STEPS[n](cfg, log)
        except KeyboardInterrupt:
            raise
        except Exception as exc:  # noqa: BLE001 - reportar y seguir con resumen
            import traceback
            log.err(T("ui.exception", n=n, exc=exc))
            log.file(traceback.format_exc())
            results[n] = False
        if not results[n]:
            log.err(T("ui.stepfail", n=n))
            break

    log.line("\n" + "=" * 62)
    log.line(T("ui.summary"))
    for n in sorted(cfg.steps):
        mark = "✓" if results.get(n) else ("·" if n not in results else "✗")
        if mark == "✓" and n in cfg.pending:
            mark = "!"
        extra = f" — {cfg.status[n]}" if n in cfg.status else ""
        log.line(T("ui.sumline", mark=mark, n=n, label=T(f"lbl.{n}"), extra=extra))
    ok = all(results.get(n) for n in cfg.steps)
    log.line("=" * 62)
    if not ok:
        log.err(T("ui.failed"))
        log.warn(T("ui.checklog", path=log.log_path))
        return 1
    if cfg.dry_run:
        log.ok(T("ui.dry_done"))
        return 0
    verified = bool(results.get(7))
    if cfg.warnings:
        log.warn(T("ui.done_warn") if verified else T("ui.partial_warn"))
        for w in cfg.warnings:
            log.warn(w)
    else:
        log.ok(T("ui.done") if verified else T("ui.partial"))
    if verified:
        log.info(T("ui.next1"))
        log.info(T("ui.next2_auto") if cfg.autostart else T("ui.next2"))
        log.info(T("ui.next3"))
        log.info(T("ui.next4"))
    log.info(T("ui.checklog", path=log.log_path))
    return 2 if cfg.warnings else 0


if __name__ == "__main__":
    raise SystemExit(main())
