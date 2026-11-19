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

# La serie que este instalador garantiza. NO es "la última de QGIS" (hoy la
# estable más nueva es la 4.x): es la 3.44 LTR, que es la que usa el plugin y el
# taller. El instalador resuelve en tiempo de ejecución el ÚLTIMO PARCHE de esta
# serie y, tras instalar, lee la versión del binario y exige que sea 3.44.x.
QGIS_SERIES = (3, 44)
QGIS_SERIES_TEXT = "3.44"

# Último parche conocido de la serie, verificado el 2026-11-18. Solo se usa como
# respaldo si no se puede leer el índice de descargas de qgis.org.
QGIS_VERSION = "3.44.15"
QGIS_BUILD = "2"

# Índice oficial de MSI (listado HTML) y paquete LTR del repositorio OSGeo4W.
# Con ellos se resuelve el último 3.44.x sin tener una versión fijada a mano.
QGIS_DOWNLOADS_INDEX = "https://download.qgis.org/downloads/"
QGIS_MSI_URL_TEMPLATE = "https://download.qgis.org/downloads/QGIS-OSGeo4W-{version}-{build}.msi"
QGIS_MSI_NAME_RE = r"QGIS-OSGeo4W-(\d+\.\d+\.\d+)-(\d+)\.msi"
OSGEO4W_SETUP_INI = "https://download.osgeo.org/osgeo4w/v2/x86_64/setup.ini.bz2"
OSGEO4W_LTR_PACKAGE = "qgis-ltr"

# ─────────────────────────────────────────────────────────────────────────────
# Paso 1 — Claude Desktop (Windows x64)
#
# Anthropic publica dos formas de instalar Claude Desktop en Windows, ambas en
# downloads.claude.ai y ambas firmadas por «Anthropic, PBC»:
#
#   · MSIX (la que documenta "Deploy Claude Desktop for Windows",
#     support.claude.com/en/articles/12622703): registra un servicio de Windows,
#     por eso SIN administrador falla con 0x80073D28 («Administrator privileges
#     required to install packaged service», registro AppXDeployment-Server,
#     eventos 404/605 «Failure in the Approved state handler»). Además el
#     redirect «msix/latest» va por detrás del canal de actualizaciones.
#   · Setup.exe (Squirrel.Windows): el instalador por usuario que usa el botón
#     de claude.com/download. Instala en %LOCALAPPDATA%\AnthropicClaude, NO pide
#     administrador y se mantiene al día con el canal RELEASES.
#
# El instalador usa la segunda. La URL del Setup.exe de una versión tiene el
# mismo nombre (hash incluido) que su MSIX con otra extensión, así que se obtiene
# del redirect documentado cambiando .msix por .exe. Como ese redirect puede ir
# una versión por detrás, después de instalar se aplica la actualización del
# canal oficial (RELEASES) con el propio Update.exe y se comprueba que la versión
# instalada es la que publica el canal.
#
# No hay checksum público -> la garantía es la firma Authenticode ("Anthropic").
# Verificado el 2026-11-18: canal = 6.6395.1; redirect MSIX/Setup = 5.11492.5.
# ─────────────────────────────────────────────────────────────────────────────

CLAUDE_MSIX_REDIRECT = "https://claude.ai/api/desktop/win32/x64/msix/latest/redirect"
CLAUDE_RELEASES_BASE = "https://downloads.claude.ai/releases/win32/x64"
CLAUDE_RELEASES_FEED = CLAUDE_RELEASES_BASE + "/RELEASES"
CLAUDE_DOWNLOAD_HOST = "downloads.claude.ai"
CLAUDE_PUBLISHER = "Anthropic"

CLAUDE_SETUP = Download(
    key="claude_setup",
    # La URL real se resuelve en tiempo de ejecución (ver arriba); esta es la
    # del redirect documentado y solo sirve para que el plan en seco la muestre.
    name="Claude Desktop (Windows x64, Setup.exe por usuario)",
    url=CLAUDE_MSIX_REDIRECT,
    filename="Claude-Setup.exe",
    expected_publisher_contains=CLAUDE_PUBLISHER,
    sha256=None,  # "latest": sube de versión; la firma es la garantía
    expected_size=267_307_680,  # ~255 MB observado el 2026-11-18 (cordura)
    cache=False,
    notes="Instalador Squirrel por usuario, sin administrador. Se ejecuta con "
          "--silent y luego Update.exe --update contra el canal oficial.",
)

# Página oficial para la instalación manual cuando la automática no es posible.
CLAUDE_DOWNLOAD_PAGE = "https://claude.com/download"
# Nombre de familia del paquete MSIX de Claude Desktop (identifica su carpeta
# de datos en %LOCALAPPDATA%\Packages). Solo se usa para detectar y configurar
# instalaciones MSIX que ya existan.
CLAUDE_MSIX_FAMILY = "Claude_pzs8sxrjxfjjc"

# ─────────────────────────────────────────────────────────────────────────────
# Paso 2 — QGIS 3.44 LTR (instalador MSI de OSGeo4W, todo-en-uno con Python/GDAL)
# download.qgis.org redirige (302) a un mirror; el MSI está firmado por la OSGeo
# Foundation. La URL se resuelve en tiempo de ejecución al último 3.44.x.
# ─────────────────────────────────────────────────────────────────────────────

QGIS_LTR = Download(
    key="qgis_ltr",
    name=f"QGIS {QGIS_VERSION} LTR (OSGeo4W MSI)",
    url=QGIS_MSI_URL_TEMPLATE.format(version=QGIS_VERSION, build=QGIS_BUILD),
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
# `qgis-ltr-full` instala `qgis-ltr`: es el paquete cuya versión se comprueba.
# Ojo: `qgis` (sin -ltr) ya es la serie 4.x; nunca se pide.
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
    for d in (CLAUDE_SETUP, QGIS_LTR, OSGEO4W_SETUP, UV, PLUGIN_FORK,
              PLUGIN_UPSTREAM)
}
