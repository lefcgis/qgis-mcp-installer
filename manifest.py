"""
manifest.py — Fuente única de verdad para descargas y versiones del ETL.

Todo lo que el instalador descarga o ejecuta está declarado AQUÍ, en claro y
auditable. No hay URLs ocultas ni lógica de descarga en otros módulos: si
quieres saber qué toca la red este instalador, este archivo lo dice todo.

Estrategia de integridad (Windows-first):
  1. Firma Authenticode  -> comprobación PRIMARIA. Se verifica que el binario
     esté firmado, con firma válida y por el publisher esperado. Es más robusto
     que un checksum fijo porque sobrevive a las subidas de versión.
  2. SHA-256 fijado       -> comprobación SECUNDARIA opcional. Si `sha256` no es
     None, el archivo descargado debe coincidir exactamente. Deja None para
     dependencias que suben de versión con frecuencia (QGIS/Claude) y confía en
     la firma; fija el hash para builds reproducibles/auditorías.
  3. Tamaño esperado      -> chequeo de cordura barato (detecta 404/HTML/cortes).

Verificado el 2026-07-05 con peticiones HEAD reales a los servidores oficiales.
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
    # Hash secundario opcional. None = confiar en la firma (recomendado para
    # instaladores que suben de versión). Fíjalo para builds auditables.
    sha256: str | None = None
    # Chequeo de cordura de tamaño (bytes). Tolerancia amplia por defecto.
    expected_size: int | None = None
    notes: str = ""


# ─────────────────────────────────────────────────────────────────────────────
# Versiones fijadas
# ─────────────────────────────────────────────────────────────────────────────

QGIS_VERSION = "3.44.12"  # LTR (Long Term Release), rama 3.44. Última al 2026-07-05.
QGIS_BUILD = "1"

# ─────────────────────────────────────────────────────────────────────────────
# Paso 1 — Claude Desktop (Windows x64)
# URL oficial servida por el bucket de descargas de Anthropic. 200 OK verificado.
# Claude Desktop NO publica un checksum público -> confiamos en la firma
# Authenticode del binario (publisher "Anthropic").
# ─────────────────────────────────────────────────────────────────────────────

CLAUDE_DESKTOP = Download(
    key="claude_desktop",
    name="Claude Desktop (Windows x64)",
    url=(
        "https://storage.googleapis.com/"
        "osprey-downloads-c02f6a0d-347c-492b-a752-3e0651722e97/"
        "nest-win-x64/Claude-Setup-x64.exe"
    ),
    filename="Claude-Setup-x64.exe",
    expected_publisher_contains="Anthropic",
    sha256=None,  # sube de versión con frecuencia; la firma es la garantía
    expected_size=132_098_208,  # ~126 MB observado el 2026-07-05 (chequeo de cordura)
    notes="Instalador NSIS por-usuario; ejecuta silencioso con /S.",
)

# ─────────────────────────────────────────────────────────────────────────────
# Paso 2 — QGIS 3.44 LTR (instalador MSI de OSGeo4W, todo-en-uno con Python/GDAL)
# download.qgis.org redirige (302) a un mirror; el MSI está firmado por QGIS.ORG.
# ─────────────────────────────────────────────────────────────────────────────

QGIS_LTR = Download(
    key="qgis_ltr",
    name=f"QGIS {QGIS_VERSION} LTR (OSGeo4W MSI)",
    url=f"https://download.qgis.org/downloads/QGIS-OSGeo4W-{QGIS_VERSION}-{QGIS_BUILD}.msi",
    filename=f"QGIS-OSGeo4W-{QGIS_VERSION}-{QGIS_BUILD}.msi",
    expected_publisher_contains="QGIS",  # firmado por "QGIS.ORG Association"
    sha256=None,  # fija el valor del .sha256sum oficial para una auditoría
    expected_size=None,
    notes="MSI todo-en-uno: incluye Python 3.12, GDAL, Qt. msiexec /i /qb.",
)

# ─────────────────────────────────────────────────────────────────────────────
# Paso 4 — Plugin QGIS MCP (versión mejorada, fork del usuario)
# El ETL descarga el ZIP del repositorio del USUARIO. Configurable: si el fork
# aún no existe, `--plugin-url` o la variable de entorno QGIS_MCP_PLUGIN_URL lo
# sobreescriben, y hay fallback al upstream original de Nicolas Karasiak.
# ─────────────────────────────────────────────────────────────────────────────

PLUGIN_FORK_OWNER = "lefcgis"   # usuario de GitHub de Luis Ferrer (del repo original)
PLUGIN_FORK_REPO = "qgis-mcp"   # nombre previsto para el fork mejorado
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
    sha256=None,  # fija el hash del release para distribución pública seria
    notes="Solo se copia la subcarpeta qgis_mcp_plugin/ al perfil de QGIS.",
)

# Fallback al upstream original (MIT, Nicolas Karasiak) si el fork no responde.
PLUGIN_UPSTREAM = Download(
    key="plugin_upstream",
    name="Plugin QGIS MCP (upstream nkarasiak, fallback)",
    url="https://github.com/nkarasiak/qgis-mcp/archive/refs/heads/main.zip",
    filename="qgis-mcp-upstream.zip",
    notes="Fallback. Preserva la atribución original bajo licencia MIT.",
)

# ─────────────────────────────────────────────────────────────────────────────
# Paso 3 — Dependencias de Python del servidor MCP
# Fijadas y actualizadas (2026-07-05). Se instalan en un venv aislado, NUNCA en
# el Python del sistema ni en el de QGIS. `mcp` es el único requerido en runtime;
# el resto son transitivas que fijamos para reproducibilidad y seguridad.
# ─────────────────────────────────────────────────────────────────────────────

PYTHON_MIN = (3, 12)

# Requisito directo del servidor MCP. Rango con techo para evitar roturas por
# cambios mayores, pero permitiendo parches de seguridad.
RUNTIME_DEPENDENCIES: list[str] = [
    "mcp[cli]>=1.20.0,<2.0.0",
]

DOWNLOADS: dict[str, Download] = {
    d.key: d
    for d in (CLAUDE_DESKTOP, QGIS_LTR, PLUGIN_FORK, PLUGIN_UPSTREAM)
}
