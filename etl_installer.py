#!/usr/bin/env python3
"""
QGIS MCP — Instalador ETL (Extract · Transform · Load)
======================================================

Aprovisiona de cero un equipo Windows para usar QGIS con Claude AI vía el
Model Context Protocol, en 6 pasos:

    1. Claude Desktop         (descarga + instala)
    2. QGIS 3.44 LTR          (descarga + instala)
    3. Dependencias de Python (venv aislado con librerías fijadas)
    4. Plugin QGIS MCP        (descarga el fork mejorado + lo despliega)
    5. Configura QGIS         (habilita el plugin en el perfil)
    6. Configura Claude       (escribe claude_desktop_config.json)

FILOSOFÍA DE DISEÑO
-------------------
Este instalador es DELIBERADAMENTE transparente y auditable:

  • Todo lo que descarga está declarado en `manifest.py`, en claro.
  • Cada acción se imprime en pantalla y se registra en un log con fecha.
  • Los binarios se verifican por firma Authenticode (publisher esperado)
    antes de ejecutarse. Nada se ejecuta a ciegas.
  • El usuario elige TODAS las carpetas de instalación.
  • No hay ofuscación, empaquetado anti-análisis ni evasión de detección.
    Cuando se distribuye como .exe (ver build_exe.py), se recomienda FIRMARLO
    con un certificado de código para que Windows y los antivirus confíen —
    lo contrario de esconderse.

Uso:
    python etl_installer.py                     # asistente interactivo
    python etl_installer.py --non-interactive \\
        --base-dir "D:/QGIS-Claude" \\
        --steps 1,2,3,4,5,6
    python etl_installer.py --dry-run           # muestra el plan, no toca nada
    python etl_installer.py --steps 4,5,6       # solo plugin + configuración
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import os
import shutil
import subprocess
import sys
import urllib.request
import zipfile
from dataclasses import dataclass, field
from pathlib import Path

import manifest

# ─────────────────────────────────────────────────────────────────────────────
# Presentación / logging
# ─────────────────────────────────────────────────────────────────────────────

try:  # mejora acentos en consolas que soportan UTF-8; inofensivo si falla
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

_C = {
    "reset": "\033[0m", "bold": "\033[1m", "dim": "\033[2m",
    "green": "\033[32m", "yellow": "\033[33m", "red": "\033[31m",
    "cyan": "\033[36m",
}
if os.environ.get("NO_COLOR") or not sys.stdout.isatty():
    _C = {k: "" for k in _C}


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
        self.line(f"\n===== Sesión iniciada {_dt.datetime.now().isoformat()} =====")

    def _write(self, msg: str) -> None:
        print(msg)
        if self._fh:
            self._fh.write(msg + "\n")
            self._fh.flush()

    def line(self, msg: str = "") -> None:
        print(msg)
        if self._fh:
            self._fh.write(msg + "\n")
            self._fh.flush()

    def step(self, n: int, title: str) -> None:
        self._write(f"\n{_C['bold']}{_C['cyan']}[Paso {n}] {title}{_C['reset']}")

    def info(self, msg: str) -> None:
        self._write(f"  {msg}")

    def ok(self, msg: str) -> None:
        self._write(f"  {_C['green']}✓{_C['reset']} {msg}")

    def warn(self, msg: str) -> None:
        self._write(f"  {_C['yellow']}⚠{_C['reset']}  {msg}")

    def err(self, msg: str) -> None:
        self._write(f"  {_C['red']}✗{_C['reset']} {msg}")


# ─────────────────────────────────────────────────────────────────────────────
# Configuración de la ejecución
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class Config:
    base_dir: Path            # raíz elegida por el usuario para todo
    downloads_dir: Path       # donde caen los instaladores descargados
    venv_dir: Path            # entorno Python aislado para el servidor MCP
    server_dir: Path          # donde vive el código del servidor MCP
    qgis_profile: str         # perfil de QGIS a configurar
    steps: set[int]
    dry_run: bool
    non_interactive: bool
    skip_signature: bool
    plugin_url: str
    assume_installed: set[str] = field(default_factory=set)  # {'claude','qgis'}
    status: dict[int, str] = field(default_factory=dict)     # etiqueta por paso

    @property
    def claude_config_path(self) -> Path:
        appdata = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
        return appdata / "Claude" / "claude_desktop_config.json"

    def qgis_major(self) -> str:
        """Detecta la versión mayor de QGIS por el directorio de perfiles.

        Prefiere QGIS4 si su carpeta de datos existe; si no, QGIS3 (la versión
        que este ETL instala). Así el plugin va al perfil correcto tanto si el
        usuario ya tiene QGIS 4 como si acabamos de instalar 3.44.
        """
        appdata = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
        for major in ("4", "3"):
            if (appdata / "QGIS" / f"QGIS{major}").exists():
                return major
        return "3"

    def qgis_profile_dir(self) -> Path:
        appdata = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
        return (appdata / "QGIS" / f"QGIS{self.qgis_major()}"
                / "profiles" / self.qgis_profile)

    def qgis_plugins_dir(self) -> Path:
        return self.qgis_profile_dir() / "python" / "plugins"

    def qgis_ini_path(self) -> Path:
        return self.qgis_profile_dir() / "QGIS" / f"QGIS{self.qgis_major()}.ini"


# ─────────────────────────────────────────────────────────────────────────────
# Utilidades: descarga + verificación de integridad
# ─────────────────────────────────────────────────────────────────────────────

def _human(n: int) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024:
            return f"{n:.1f}{unit}"
        n /= 1024
    return f"{n:.1f}TB"


def download(dl: "manifest.Download", dest_dir: Path, log: Logger,
             dry_run: bool) -> Path:
    """Descarga con barra de progreso. Devuelve la ruta al archivo."""
    dest = dest_dir / dl.filename
    if dry_run:
        log.info(f"[dry-run] descargaría {dl.url} -> {dest}")
        return dest
    if dest.exists() and dest.stat().st_size > 0:
        log.ok(f"Ya descargado: {dest.name} ({_human(dest.stat().st_size)})")
        return dest

    dest_dir.mkdir(parents=True, exist_ok=True)
    log.info(f"Descargando {dl.name}")
    log.info(f"  desde: {dl.url}")
    tmp = dest.with_suffix(dest.suffix + ".part")
    req = urllib.request.Request(dl.url, headers={"User-Agent": "qgis-mcp-etl/1.0"})
    with urllib.request.urlopen(req, timeout=60) as resp, tmp.open("wb") as fh:
        total = int(resp.headers.get("Content-Length", 0))
        read = 0
        block = 1024 * 256
        while True:
            chunk = resp.read(block)
            if not chunk:
                break
            fh.write(chunk)
            read += len(chunk)
            if total and sys.stdout.isatty():
                pct = read / total * 100
                sys.stdout.write(f"\r    {pct:5.1f}%  {_human(read)}/{_human(total)}")
                sys.stdout.flush()
    if sys.stdout.isatty():
        sys.stdout.write("\n")
    tmp.replace(dest)
    log.ok(f"Descargado {dest.name} ({_human(dest.stat().st_size)})")
    return dest


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
        log.ok(f"SHA-256 verificado: {actual[:16]}…")
        return True
    log.err(f"SHA-256 NO coincide. esperado={expected[:16]}… actual={actual[:16]}…")
    return False


def verify_signature(path: Path, publisher_contains: str | None,
                     log: Logger, skip: bool) -> bool:
    """Verifica la firma Authenticode del binario (solo Windows)."""
    if publisher_contains is None:
        return True
    if skip:
        log.warn("Verificación de firma OMITIDA por el usuario (--skip-signature).")
        return True
    if sys.platform != "win32":
        log.warn("No es Windows: se omite la verificación Authenticode.")
        return True
    ps = (
        f"$s = Get-AuthenticodeSignature -LiteralPath '{path}'; "
        "$subject = $s.SignerCertificate.Subject; "
        "Write-Output $s.Status; Write-Output $subject"
    )
    try:
        out = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", ps],
            capture_output=True, text=True, timeout=60,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        log.err(f"No se pudo ejecutar la verificación de firma: {exc}")
        return False
    lines = [ln.strip() for ln in out.stdout.splitlines() if ln.strip()]
    status = lines[0] if lines else "Unknown"
    subject = lines[1] if len(lines) > 1 else ""
    if status != "Valid":
        log.err(f"Firma inválida o ausente (Status={status}).")
        return False
    if publisher_contains.lower() not in subject.lower():
        log.err(f"Publisher inesperado. esperado ~'{publisher_contains}', "
                f"firma='{subject}'")
        return False
    log.ok(f"Firma válida. Publisher: {subject}")
    return True


def fetch_verified(dl: "manifest.Download", cfg: Config, log: Logger) -> Path | None:
    """Descarga y verifica integridad (firma + hash). None si falla."""
    path = download(dl, cfg.downloads_dir, log, cfg.dry_run)
    if cfg.dry_run:
        return path
    if not verify_signature(path, dl.expected_publisher_contains, log,
                            cfg.skip_signature):
        return None
    if not verify_sha256(path, dl.sha256, log):
        return None
    if dl.expected_size and abs(path.stat().st_size - dl.expected_size) > dl.expected_size * 0.25:
        log.warn(f"Tamaño inesperado ({_human(path.stat().st_size)}); "
                 "continúo, pero revísalo.")
    return path


# ─────────────────────────────────────────────────────────────────────────────
# Detección de software ya instalado + confirmación del usuario
# ─────────────────────────────────────────────────────────────────────────────

def _local_appdata() -> Path:
    return Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))


def detect_claude() -> tuple[bool, str | None, Path | None]:
    """Busca Claude Desktop instalado (por-usuario) y su versión."""
    local = _local_appdata()
    candidates = [
        local / "AnthropicClaude",
        local / "Programs" / "claude",
        local / "Programs" / "Claude",
    ]
    for base in candidates:
        if not base.exists():
            continue
        # Los builds de Claude Desktop se despliegan en carpetas app-<version>.
        versions = sorted(
            (p.name[len("app-"):] for p in base.glob("app-*") if p.is_dir()),
            reverse=True,
        )
        ver = versions[0] if versions else None
        has_exe = any(base.glob("**/Claude.exe")) or (base / "Claude.exe").exists()
        if ver or has_exe:
            return True, ver, base
    return False, None, None


def detect_qgis() -> tuple[bool, str | None, Path | None]:
    """Busca una instalación de QGIS y su versión."""
    roots = [
        Path(os.environ.get("ProgramFiles", r"C:\Program Files")),
        Path(r"C:\Program Files"),
        Path(r"C:\Program Files (x86)"),
    ]
    seen: set[Path] = set()
    for root in roots:
        if not root.exists() or root in seen:
            continue
        seen.add(root)
        for d in sorted(root.glob("QGIS *"), reverse=True):
            if (d / "bin").exists():
                ver = d.name.replace("QGIS", "").strip() or None
                return True, ver, d
    for p in (Path(r"C:\OSGeo4W"), Path(r"C:\OSGeo4W64")):
        if (p / "bin" / "qgis-bin.exe").exists():
            return True, None, p
    return False, None, None


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


def confirm_installed(name: str, key: str,
                      detected: tuple[bool, str | None, Path | None],
                      cfg: Config, log: Logger) -> tuple[bool, str | None]:
    """Muestra la detección y pregunta al usuario si ya tiene el software.

    Devuelve (ya_lo_tiene, version). En modo no interactivo usa la detección
    automática. En interactivo, el usuario confirma y puede corregir la versión.
    """
    found, ver, loc = detected
    if found:
        detail = f" v{ver}" if ver else " (versión no detectada)"
        log.info(f"Detectado {name}{detail}" + (f"  ·  {loc}" if loc else ""))
    else:
        log.info(f"No detecté {name} automáticamente en las rutas habituales.")

    # El usuario puede forzar 'ya instalado' por CLI (--assume-installed).
    if key in cfg.assume_installed:
        log.info(f"--assume-installed: se asume {name} ya presente.")
        return True, ver

    if cfg.non_interactive:
        return found, ver

    prompt_default = "S/n" if found else "s/N"
    ans = input(f"  ¿Ya tienes {name} instalado? [{prompt_default}]: ").strip().lower()
    if not ans:
        ans = "s" if found else "n"
    has = ans in ("s", "y", "si", "sí", "yes")
    if not has:
        return False, None
    typed = input(f"  ¿Qué versión de {name} tienes? "
                  f"[{ver or 'no sé'}]: ").strip()
    return True, (typed or ver)


# ─────────────────────────────────────────────────────────────────────────────
# Resolución de intérprete Python / uv (crítico al correr como .exe congelado)
# ─────────────────────────────────────────────────────────────────────────────

def _real_python() -> str | None:
    """Devuelve un intérprete de Python REAL.

    Al ejecutarse como .exe de PyInstaller, `sys.executable` es el PROPIO
    instalador, no Python — así que no sirve para crear un venv. En ese caso
    buscamos un Python de verdad: primero en el PATH (py/python), luego el que
    QGIS trae empaquetado (siempre presente tras el paso 2).
    """
    if not getattr(sys, "frozen", False):
        return sys.executable  # ejecución normal: el intérprete actual vale
    for cand in ("py", "python", "python3"):
        exe = shutil.which(cand)
        if exe and "qgis-mcp-installer" not in exe.lower():
            return exe
    for base in (Path(os.environ.get("ProgramFiles", r"C:\Program Files")),
                 Path(r"C:\Program Files")):
        if not base.exists():
            continue
        for d in sorted(base.glob("QGIS *"), reverse=True):
            for p in sorted((d / "apps").glob("Python*/python.exe"), reverse=True):
                return str(p)
    return None


def _ensure_uv(real_py: str | None, log: Logger, dry_run: bool) -> str | None:
    """Garantiza `uv` (que arranca el servidor MCP) y devuelve su ruta absoluta.

    Usar la ruta absoluta en el config de Claude lo hace independiente del PATH,
    que es justo el problema clásico: Claude Desktop lanza procesos sin ver el
    PATH del usuario.
    """
    exe = shutil.which("uv")
    if exe:
        return exe
    if dry_run:
        return "uv"
    if real_py:
        log.info("Instalando 'uv' (gestor de entorno del servidor MCP)…")
        subprocess.run([real_py, "-m", "pip", "install", "--upgrade", "uv"])
        scripts = "Scripts" if sys.platform == "win32" else "bin"
        cand = Path(real_py).parent / scripts / ("uv.exe" if sys.platform == "win32" else "uv")
        if cand.exists():
            return str(cand)
        exe = shutil.which("uv")
        if exe:
            return exe
    log.warn("No pude asegurar 'uv'. El servidor podría no arrancar hasta "
             "instalarlo (https://docs.astral.sh/uv/).")
    return None


# ─────────────────────────────────────────────────────────────────────────────
# PASOS DEL ETL
# ─────────────────────────────────────────────────────────────────────────────

def step1_claude_desktop(cfg: Config, log: Logger) -> bool:
    log.step(1, "Claude Desktop")
    has, ver = confirm_installed("Claude Desktop", "claude", detect_claude(), cfg, log)
    if has:
        cfg.status[1] = f"ya presente{f' (v{ver})' if ver else ''}"
        log.ok(f"Usas tu Claude Desktop existente{f' (v{ver})' if ver else ''}. "
               "Se omite la instalación; igual se configurará en el paso 6.")
        return True
    installer = fetch_verified(manifest.CLAUDE_DESKTOP, cfg, log)
    if installer is None:
        return False
    if cfg.dry_run:
        log.info("[dry-run] ejecutaría el instalador de Claude Desktop (/S).")
        return True
    log.info("Ejecutando instalador (silencioso)…")
    rc = subprocess.run([str(installer), "/S"]).returncode
    if rc == 0:
        cfg.status[1] = "instalado"
        log.ok("Claude Desktop instalado.")
        return True
    log.err(f"El instalador de Claude devolvió código {rc}.")
    return False


def step2_qgis(cfg: Config, log: Logger) -> bool:
    log.step(2, f"QGIS {manifest.QGIS_VERSION} LTR")
    has, ver = confirm_installed("QGIS", "qgis", detect_qgis(), cfg, log)
    if has:
        cfg.status[2] = f"ya presente{f' (v{ver})' if ver else ''}"
        if _version_tuple(ver) and _version_tuple(ver) < (3, 28):
            log.warn(f"Tu QGIS ({ver}) es anterior a 3.28; el plugin exige >= 3.28. "
                     "Puede que no cargue. Considera actualizar.")
        log.ok(f"Usas tu QGIS existente{f' (v{ver})' if ver else ''}. "
               "Se omite la instalación; el plugin se desplegará en tu perfil.")
        return True
    installer = fetch_verified(manifest.QGIS_LTR, cfg, log)
    if installer is None:
        return False
    if cfg.dry_run:
        log.info("[dry-run] ejecutaría msiexec para instalar QGIS.")
        return True
    log.info("Instalando QGIS con msiexec (barra de progreso básica)…")
    rc = subprocess.run(
        ["msiexec", "/i", str(installer), "/qb", "/norestart"]
    ).returncode
    if rc in (0, 3010):  # 3010 = éxito, requiere reinicio
        cfg.status[2] = "instalado"
        log.ok("QGIS instalado.")
        return True
    log.err(f"msiexec devolvió código {rc}.")
    return False


def step3_python_deps(cfg: Config, log: Logger) -> bool:
    log.step(3, "Dependencias de Python (venv aislado)")
    if sys.version_info < manifest.PYTHON_MIN:
        log.warn(f"Este proceso corre en Python {sys.version.split()[0]}; "
                 f"el servidor necesita >= {'.'.join(map(str, manifest.PYTHON_MIN))}.")
    if cfg.dry_run:
        log.info(f"[dry-run] crearía venv en {cfg.venv_dir} e instalaría: "
                 f"{', '.join(manifest.RUNTIME_DEPENDENCIES)}")
        return True

    real_py = _real_python()
    if real_py is None:
        log.err("No encontré un intérprete de Python real para crear el venv. "
                "Instala QGIS (paso 2) o Python, y reintenta el paso 3.")
        return False
    log.info(f"Usando Python: {real_py}")

    if not (cfg.venv_dir / "pyvenv.cfg").exists():
        log.info(f"Creando venv en {cfg.venv_dir}")
        rc = subprocess.run([real_py, "-m", "venv", str(cfg.venv_dir)]).returncode
        if rc != 0:
            log.err("No se pudo crear el venv.")
            return False
    py = cfg.venv_dir / ("Scripts" if sys.platform == "win32" else "bin") / \
        ("python.exe" if sys.platform == "win32" else "python")
    log.info("Actualizando pip e instalando dependencias fijadas…")
    subprocess.run([str(py), "-m", "pip", "install", "--upgrade", "pip"])
    rc = subprocess.run(
        [str(py), "-m", "pip", "install", *manifest.RUNTIME_DEPENDENCIES]
    ).returncode
    if rc != 0:
        log.err("Falló la instalación de dependencias.")
        return False
    log.ok("Dependencias instaladas en el venv.")

    # `uv` arranca el servidor MCP (paso 6). Lo aseguramos aquí y guardamos su
    # ruta absoluta para un config independiente del PATH.
    cfg._uv_path = _ensure_uv(real_py, log, cfg.dry_run)  # type: ignore[attr-defined]
    cfg.status[3] = "venv + deps"
    return True


def step4_plugin(cfg: Config, log: Logger) -> bool:
    log.step(4, "Plugin QGIS MCP (fork mejorado)")
    dl = manifest.PLUGIN_FORK
    if cfg.plugin_url:
        dl = manifest.Download(key=dl.key, name=dl.name, url=cfg.plugin_url,
                               filename=dl.filename)
        log.info(f"Usando URL de plugin indicada: {cfg.plugin_url}")

    zip_path = None
    try:
        zip_path = fetch_verified(dl, cfg, log)
    except Exception as exc:  # noqa: BLE001 - queremos el fallback
        log.warn(f"No se pudo obtener el fork ({exc}).")
    if zip_path is None and not cfg.dry_run:
        log.warn("Recurriendo al upstream original (nkarasiak, MIT).")
        zip_path = fetch_verified(manifest.PLUGIN_UPSTREAM, cfg, log)
    if zip_path is None:
        return cfg.dry_run  # en dry-run seguimos; si no, es fallo

    if cfg.dry_run:
        log.info("[dry-run] extraería el ZIP y copiaría qgis_mcp_plugin/ + src/.")
        return True

    # Extraer y localizar la carpeta del plugin + el código del servidor.
    extract_dir = cfg.downloads_dir / "plugin_extract"
    if extract_dir.exists():
        shutil.rmtree(extract_dir)
    with zipfile.ZipFile(zip_path) as zf:
        zf.extractall(extract_dir)
    roots = [p for p in extract_dir.iterdir() if p.is_dir()]
    if not roots:
        log.err("El ZIP del plugin está vacío.")
        return False
    repo_root = roots[0]

    plugin_src = repo_root / "qgis_mcp_plugin"
    if not (plugin_src / "metadata.txt").exists():
        log.err("El repositorio no contiene qgis_mcp_plugin/metadata.txt.")
        return False

    # Copiar el código del servidor MCP a server_dir (para el paso 6).
    server_src = repo_root / "src"
    if server_src.exists():
        if cfg.server_dir.exists():
            shutil.rmtree(cfg.server_dir)
        shutil.copytree(server_src, cfg.server_dir)
        # copiar también pyproject/uv.lock si existen (para `uv run`)
        for extra in ("pyproject.toml", "uv.lock", ".python-version"):
            src = repo_root / extra
            if src.exists():
                shutil.copy2(src, cfg.server_dir.parent / extra)
        log.ok(f"Código del servidor MCP copiado a {cfg.server_dir}")
    else:
        log.warn("El repo no trae src/; se usará el modo remoto (uvx) en el paso 6.")

    # Guardar la ruta del plugin extraído para el paso 5.
    cfg._plugin_src = plugin_src  # type: ignore[attr-defined]
    log.ok("Plugin obtenido y preparado.")
    return True


def step5_configure_qgis(cfg: Config, log: Logger) -> bool:
    log.step(5, "Configurar QGIS (desplegar y habilitar el plugin)")
    if cfg.dry_run:
        dest = cfg.qgis_plugins_dir() / "qgis_mcp_plugin"
        log.info(f"[dry-run] copiaría el plugin extraído -> {dest}")
        log.info("[dry-run] habilitaría 'qgis_mcp_plugin' en QGIS3.ini")
        return True

    plugin_src = getattr(cfg, "_plugin_src", None)
    if plugin_src is None:
        # Permite ejecutar el paso 5 aislado si el plugin ya se extrajo antes.
        guess = cfg.downloads_dir / "plugin_extract"
        cand = list(guess.glob("*/qgis_mcp_plugin")) if guess.exists() else []
        plugin_src = cand[0] if cand else None
    if plugin_src is None:
        log.err("No encuentro el plugin extraído. Ejecuta antes el paso 4.")
        return False

    dest = cfg.qgis_plugins_dir() / "qgis_mcp_plugin"
    if cfg.dry_run:
        log.info(f"[dry-run] copiaría {plugin_src} -> {dest}")
        log.info("[dry-run] habilitaría el plugin en QGIS3.ini")
        return True

    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists():
        shutil.rmtree(dest)
    shutil.copytree(plugin_src, dest)
    log.ok(f"Plugin copiado a {dest}")

    # Habilitar el plugin en la config de QGIS (QGIS3.ini / QGIS4.ini).
    ini = cfg.qgis_ini_path()
    try:
        _enable_plugin_in_ini(ini, "qgis_mcp_plugin", log)
    except Exception as exc:  # noqa: BLE001 - no es crítico
        log.warn(f"No pude editar QGIS3.ini automáticamente ({exc}). "
                 "Habilita 'QGIS MCP' a mano en Complementos.")
    log.ok("QGIS configurado. Recuerda: Complementos → QGIS MCP → Start Server.")
    return True


def _enable_plugin_in_ini(ini: Path, plugin_name: str, log: Logger) -> None:
    """Añade `PythonPlugins/<plugin>=true` en la sección [PythonPlugins]."""
    if not ini.exists():
        log.warn(f"{ini} no existe todavía (abre QGIS una vez). Se omite.")
        return
    import configparser
    cp = configparser.ConfigParser()
    cp.optionxform = str  # preservar mayúsculas
    cp.read(ini, encoding="utf-8")
    section = "PythonPlugins"
    if not cp.has_section(section):
        cp.add_section(section)
    cp.set(section, plugin_name, "true")
    with ini.open("w", encoding="utf-8") as fh:
        cp.write(fh)
    log.ok(f"Plugin habilitado en {ini.name}")


def step6_configure_claude(cfg: Config, log: Logger) -> bool:
    log.step(6, "Configurar Claude Desktop (claude_desktop_config.json)")
    cfg_path = cfg.claude_config_path

    # Ruta absoluta a uv (independiente del PATH; Claude lanza sin ver el PATH
    # del usuario). Fallback a 'uv'/'uvx' en PATH si no se resolvió en el paso 3.
    uv_path = getattr(cfg, "_uv_path", None) or shutil.which("uv") or "uv"
    uvx_path = (str(Path(uv_path).with_name(
        "uvx.exe" if sys.platform == "win32" else "uvx"))
        if uv_path not in ("uv",) and Path(uv_path).name.startswith("uv")
        else "uvx")

    # Preferimos el modo local (uv run del server_dir) si existe el código;
    # si no, modo remoto con uvx desde el repo del fork.
    server_main = cfg.server_dir / "qgis_mcp" / "server.py"
    if server_main.exists():
        entry = {
            "command": uv_path,
            "args": ["run", "--no-sync", str(server_main)],
        }
        mode = f"local (uv run) · {uv_path}"
    else:
        entry = {
            "command": uvx_path,
            "args": ["--from",
                     f"git+https://github.com/{manifest.PLUGIN_FORK_OWNER}/"
                     f"{manifest.PLUGIN_FORK_REPO}.git",
                     "qgis-mcp-server"],
        }
        mode = "remoto (uvx)"

    log.info(f"Modo de servidor: {mode}")
    if cfg.dry_run:
        log.info(f"[dry-run] escribiría en {cfg_path}:")
        log.info("    " + json.dumps({"mcpServers": {"qgis": entry}}, indent=2))
        return True

    cfg_path.parent.mkdir(parents=True, exist_ok=True)
    data: dict = {}
    if cfg_path.exists():
        # Respaldo antes de tocar nada del usuario.
        backup = cfg_path.with_suffix(f".json.bak-{_dt.datetime.now():%Y%m%d%H%M%S}")
        shutil.copy2(cfg_path, backup)
        log.ok(f"Respaldo creado: {backup.name}")
        try:
            data = json.loads(cfg_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            log.warn("El config existente no era JSON válido; se reemplaza.")
            data = {}
    data.setdefault("mcpServers", {})["qgis"] = entry
    cfg_path.write_text(json.dumps(data, indent=2, ensure_ascii=False),
                        encoding="utf-8")
    log.ok(f"Config de Claude escrita en {cfg_path}")
    return True


STEPS = {
    1: step1_claude_desktop,
    2: step2_qgis,
    3: step3_python_deps,
    4: step4_plugin,
    5: step5_configure_qgis,
    6: step6_configure_claude,
}


# ─────────────────────────────────────────────────────────────────────────────
# Interfaz de usuario / arranque
# ─────────────────────────────────────────────────────────────────────────────

BANNER = r"""
+==============================================================+
|      QGIS MCP - Instalador ETL   ·   Distribucion publica    |
|      Aprovisiona Claude Desktop + QGIS 3.44 LTR + plugin     |
+==============================================================+
"""


def _prompt_dir(prompt: str, default: Path) -> Path:
    raw = input(f"{prompt}\n  [{default}]: ").strip()
    return Path(raw).expanduser() if raw else default


def build_config(args: argparse.Namespace) -> Config:
    default_base = Path(args.base_dir).expanduser() if args.base_dir else \
        Path.home() / "qgis-mcp"

    if not args.non_interactive and not args.base_dir:
        print(BANNER)
        print("El usuario elige DÓNDE se instala todo. Enter = valor por defecto.\n")
        default_base = _prompt_dir("Carpeta raíz para QGIS MCP:", default_base)

    base = default_base
    steps = {int(s) for s in args.steps.split(",") if s.strip()} if args.steps \
        else {1, 2, 3, 4, 5, 6}

    return Config(
        base_dir=base,
        downloads_dir=base / "downloads",
        venv_dir=base / "venv",
        server_dir=base / "server" / "src",
        qgis_profile=args.profile,
        steps=steps,
        dry_run=args.dry_run,
        non_interactive=args.non_interactive,
        skip_signature=args.skip_signature,
        plugin_url=args.plugin_url or os.environ.get("QGIS_MCP_PLUGIN_URL", ""),
        assume_installed={s.strip().lower() for s in args.assume_installed.split(",")
                          if s.strip()},
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Instalador ETL de QGIS MCP (transparente y auditable).")
    parser.add_argument("--base-dir", help="Carpeta raíz de instalación.")
    parser.add_argument("--profile", default="default", help="Perfil de QGIS.")
    parser.add_argument("--steps", default="",
                        help="Pasos a ejecutar, ej. '4,5,6'. Vacío = todos.")
    parser.add_argument("--plugin-url", default="",
                        help="URL del ZIP del plugin (sobreescribe el fork).")
    parser.add_argument("--assume-installed", default="",
                        help="Asume ya instalado y omite su instalación. "
                             "Lista: claude,qgis (útil en modo desatendido).")
    parser.add_argument("--non-interactive", action="store_true",
                        help="Sin preguntas (requiere --base-dir).")
    parser.add_argument("--dry-run", action="store_true",
                        help="Muestra el plan sin descargar ni instalar nada.")
    parser.add_argument("--skip-signature", action="store_true",
                        help="Omite la verificación de firma (NO recomendado).")
    args = parser.parse_args()

    cfg = build_config(args)
    log = Logger(cfg.base_dir / "logs" /
                 f"install-{_dt.datetime.now():%Y%m%d-%H%M%S}.log",
                 to_file=not cfg.dry_run)

    print(BANNER)
    log.info(f"Carpeta raíz : {cfg.base_dir}")
    log.info(f"Descargas    : {cfg.downloads_dir}")
    log.info(f"venv Python  : {cfg.venv_dir}")
    log.info(f"Perfil QGIS  : {cfg.qgis_profile}")
    log.info(f"Pasos        : {sorted(cfg.steps)}")
    log.info(f"Modo         : {'DRY-RUN (no toca nada)' if cfg.dry_run else 'real'}")
    if cfg.skip_signature:
        log.warn("Verificación de firma DESACTIVADA.")

    if not args.non_interactive and not cfg.dry_run:
        if input("\n¿Continuar? [s/N]: ").strip().lower() not in ("s", "y"):
            log.info("Cancelado por el usuario.")
            return 130

    results: dict[int, bool] = {}
    for n in sorted(cfg.steps):
        try:
            results[n] = STEPS[n](cfg, log)
        except KeyboardInterrupt:
            log.err("Interrumpido por el usuario.")
            return 130
        except Exception as exc:  # noqa: BLE001 - reportar y seguir con resumen
            log.err(f"Paso {n} lanzó una excepción: {exc}")
            results[n] = False
        if not results[n]:
            log.err(f"El paso {n} falló. Detengo la cadena ETL.")
            break

    _labels = {1: "Claude Desktop", 2: "QGIS", 3: "Dependencias Python",
               4: "Plugin QGIS MCP", 5: "Configurar QGIS", 6: "Configurar Claude"}
    log.line("\n" + "=" * 62)
    log.line("RESUMEN")
    for n in sorted(cfg.steps):
        mark = "✓" if results.get(n) else ("·" if n not in results else "✗")
        extra = f" — {cfg.status[n]}" if n in cfg.status else ""
        log.line(f"  [{mark}] Paso {n}: {_labels.get(n, '')}{extra}")
    ok = all(results.get(n) for n in cfg.steps)
    log.line("=" * 62)
    if ok:
        log.ok("Instalación completa. Abre QGIS → Complementos → QGIS MCP → "
               "Start Server, luego abre Claude Desktop.")
    else:
        log.warn(f"Revisa el log: {log.log_path}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
