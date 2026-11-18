"""
manifest.py — Fuente única de verdad para descargas y versiones del ETL.

Todo lo que el instalador descarga o ejecuta está declarado AQUÍ, en claro y
auditable. No hay URLs ocultas ni lógica de descarga en otros módulos: si
quieres saber qué toca la red este instalador, este archivo lo dice todo.

Estrategia de integridad (Windows-first):
  1. Firma Authenticode  -> comprobación PRIMARIA para instaladores que suben de
     versión solos (Claude, QGIS, OSGeo4W). Se verifica que el binario esté
     firmado, con firma válida y por el publisher esperado.
  2. SHA-256 fijado       -> comprobación PRIMARIA para artefactos de versión
     fija (uv). Si `sha256` no es None, el archivo debe coincidir exactamente.
  3. Tamaño esperado      -> chequeo de cordura barato (detecta 404/HTML/cortes).

Verificado el 2026-11-18 con peticiones reales a los servidores oficiales.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Download:
    """Un artefacto descargable y cómo verificar su integridad."""

    key: str
    name: str
    url: str
    filename: str
    # Comprobación de firma Authenticode (Windows). None = no verificar firma.
    expected_publisher_contains: str | None = None
    # Hash fijado. None = confiar en la firma (instaladores que suben de versión).
    sha256: str | None = None
    # Chequeo de cordura de tamaño (bytes). Tolerancia amplia por defecto.
    expected_size: int | None = None
    # False = volver a descargar siempre (URLs "latest" o ramas que cambian).
    cache: bool = True
    notes: str = ""


# ─────────────────────────────────────────────────────────────────────────────
# Versiones fijadas
# ─────────────────────────────────────────────────────────────────────────────

QGIS_VERSION = "3.44.15"  # LTR, rama 3.44. Última publicada al 2026-11-18.
QGIS_BUILD = "2"

# ─────────────────────────────────────────────────────────────────────────────
# Paso 1 — Claude Desktop (Windows x64)
# Desde 2026 Claude Desktop para Windows se distribuye como paquete MSIX. Esta
# es la URL que documenta Anthropic en "Deploy Claude Desktop for Windows"
# (support.claude.com/en/articles/12622703); redirige a downloads.claude.ai.
# No hay checksum público -> confiamos en la firma del paquete ("Anthropic").
# ─────────────────────────────────────────────────────────────────────────────

CLAUDE_DESKTOP = Download(
    key="claude_desktop",
    name="Claude Desktop (Windows x64, MSIX)",
    url="https://claude.ai/api/desktop/win32/x64/msix/latest/redirect",
    filename="Claude.msix",
    expected_publisher_contains="Anthropic",
    sha256=None,  # "latest": sube de versión; la firma es la garantía
    expected_size=299_362_172,  # ~285 MB observado el 2026-11-18 (cordura)
    cache=False,
    notes="Paquete MSIX. Se instala con Add-AppxPackage (por usuario) o "
          "Add-AppxProvisionedPackage (toda la máquina, requiere administrador).",
)

# Página oficial para la instalación manual cuando la automática no es posible.
CLAUDE_DOWNLOAD_PAGE = "https://claude.com/download"
# Nombre de familia del paquete MSIX de Claude Desktop (identifica su carpeta
# de datos en %LOCALAPPDATA%\Packages).
CLAUDE_MSIX_FAMILY = "Claude_pzs8sxrjxfjjc"

# ─────────────────────────────────────────────────────────────────────────────
# Paso 2 — QGIS 3.44 LTR (instalador MSI de OSGeo4W, todo-en-uno con Python/GDAL)
# download.qgis.org redirige (302) a un mirror; el MSI está firmado por QGIS.ORG.
# ─────────────────────────────────────────────────────────────────────────────

QGIS_LTR = Download(
    key="qgis_ltr",
    name=f"QGIS {QGIS_VERSION} LTR (OSGeo4W MSI)",
    url=f"https://download.qgis.org/downloads/QGIS-OSGeo4W-{QGIS_VERSION}-{QGIS_BUILD}.msi",
    filename=f"QGIS-OSGeo4W-{QGIS_VERSION}-{QGIS_BUILD}.msi",
    # El MSI lo firma la OSGeo Foundation, no "QGIS": con "QGIS" la verificación
    # rechazaba el instalador legítimo (visto en campo el 2026-08-31).
    expected_publisher_contains="OPEN SOURCE GEOSPATIAL",
    sha256=None,
    expected_size=580_468_736,  # ~554 MB observado el 2026-11-18 (cordura)
    notes="MSI todo-en-uno: incluye Python 3.12, GDAL, Qt. msiexec /i /qb. "
          "REQUIERE permisos de administrador (instala a nivel máquina).",
)

# Espacio libre mínimo (bytes) para instalar QGIS: descarga + instalación.
QGIS_MIN_FREE_BYTES = 6 * 1024**3

# ─────────────────────────────────────────────────────────────────────────────
# Paso 2 (alternativa SIN administrador) — Instalador de red OSGeo4W
# Con --root apuntando a una carpeta del usuario instala QGIS LTR completo sin
# pedir elevación (UAC). Verificado 2026-11-18: 1.0 MB, firma Authenticode
# válida de "THE OPEN SOURCE GEOSPATIAL FOUNDATION", sin manifiesto de elevación.
# ─────────────────────────────────────────────────────────────────────────────

OSGEO4W_SETUP = Download(
    key="osgeo4w_setup",
    name="Instalador de red OSGeo4W (QGIS sin admin)",
    url="https://download.osgeo.org/osgeo4w/v2/osgeo4w-setup.exe",
    filename="osgeo4w-setup.exe",
    expected_publisher_contains="OPEN SOURCE GEOSPATIAL",
    sha256=None,  # el setup se actualiza; la firma de OSGeo es la garantía
    expected_size=1_032_336,
    cache=False,
    notes="Con --root en carpeta del usuario NO requiere administrador.",
)

# Repositorio oficial de paquetes OSGeo4W (v2) y meta-paquete a instalar.
# qgis-ltr-full = QGIS LTR completo (equivalente al contenido del MSI).
OSGEO4W_SITE = "https://download.osgeo.org/osgeo4w/v2"
OSGEO4W_PACKAGES = "qgis-ltr-full"
# Longitud máxima de la carpeta donde OSGeo4W instala o guarda paquetes. Sus
# rutas internas llegan a ~180 caracteres y Windows corta en 260 (MAX_PATH).
OSGEO4W_MAX_ROOT_LEN = 70

# ─────────────────────────────────────────────────────────────────────────────
# Paso 3 — Entorno de Python del servidor MCP
#
# El instalador NO depende del Python del sistema ni del de QGIS. Descarga `uv`
# (gestor de entornos de Astral, un único binario) con hash fijado, y `uv` trae
# un CPython propio y crea el venv. Así el resultado es el mismo en cualquier PC,
# tenga o no Python, y aunque el "python" del PATH sea el alias de la Microsoft
# Store.
#
# El hash es el que publica el propio release
# (uv-x86_64-pc-windows-msvc.zip.sha256), comprobado el 2026-11-18.
# ─────────────────────────────────────────────────────────────────────────────

UV_VERSION = "0.13.7"

UV = Download(
    key="uv",
    name=f"uv {UV_VERSION} (gestor de entornos Python)",
    url=(
        f"https://github.com/astral-sh/uv/releases/download/{UV_VERSION}/"
        "uv-x86_64-pc-windows-msvc.zip"
    ),
    filename=f"uv-{UV_VERSION}-x86_64-pc-windows-msvc.zip",
    expected_publisher_contains=None,  # es un ZIP; la garantía es el hash
    sha256="0cdc5b38fe5a8168ed6a25814f5ba43c21d313dd3187314fccb37b7cec46e021",
    expected_size=15_236_317,
    notes="ZIP con uv.exe. Se extrae en <raíz>/tools/uv; no toca el PATH.",
)

# Versión de CPython que `uv` descarga para el venv (la misma rama que usa
# QGIS 3.44 y que exige el servidor: requires-python >= 3.12).
PYTHON_VERSION = "3.12"
PYTHON_MIN = (3, 12)

# Requisito directo del servidor MCP. Rango con techo para evitar roturas por
# cambios mayores, pero permitiendo parches de seguridad.
RUNTIME_DEPENDENCIES: list[str] = [
    "mcp[cli]>=1.20.0,<2.0.0",
]

# ─────────────────────────────────────────────────────────────────────────────
# Paso 4 — Plugin QGIS MCP + servidor MCP (fork del usuario)
# El ETL descarga el ZIP del repositorio del fork. `--plugin-url` o la variable
# de entorno QGIS_MCP_PLUGIN_URL lo sobreescriben, y hay fallback al upstream
# original de Nicolas Karasiak.
# ─────────────────────────────────────────────────────────────────────────────

PLUGIN_FORK_OWNER = "lefcgis"
PLUGIN_FORK_REPO = "qgis-mcp"
PLUGIN_FORK_BRANCH = "main"

PLUGIN_FORK = Download(
    key="plugin_fork",
    name="Plugin QGIS MCP (fork mejorado)",
    url=(
        f"https://github.com/{PLUGIN_FORK_OWNER}/{PLUGIN_FORK_REPO}"
        f"/archive/refs/heads/{PLUGIN_FORK_BRANCH}.zip"
    ),
    filename="qgis-mcp-fork.zip",
    expected_publisher_contains=None,  # zip de código, no binario firmado
    sha256=None,  # la rama cambia; fija un tag + hash para una auditoría
    cache=False,
    notes="Del ZIP se usan qgis_mcp_plugin/ (plugin) y src/ (servidor MCP).",
)

# Fallback al upstream original (MIT, Nicolas Karasiak) si el fork no responde.
PLUGIN_UPSTREAM = Download(
    key="plugin_upstream",
    name="Plugin QGIS MCP (upstream nkarasiak, fallback)",
    url="https://github.com/nkarasiak/qgis-mcp/archive/refs/heads/main.zip",
    filename="qgis-mcp-upstream.zip",
    cache=False,
    notes="Fallback. Preserva la atribución original bajo licencia MIT.",
)

# Nombre de la carpeta del plugin dentro del perfil de QGIS y del módulo que
# arranca el servidor MCP (python -m <módulo>).
PLUGIN_DIRNAME = "qgis_mcp_plugin"
SERVER_MODULE = "qgis_mcp.server"
# Nombre de la entrada en mcpServers de claude_desktop_config.json.
MCP_SERVER_NAME = "qgis"

DOWNLOADS: dict[str, Download] = {
    d.key: d
    for d in (CLAUDE_DESKTOP, QGIS_LTR, OSGEO4W_SETUP, UV, PLUGIN_FORK,
              PLUGIN_UPSTREAM)
}
