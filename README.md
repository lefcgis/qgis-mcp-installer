# QGIS MCP — Instalador ETL

> 🇧🇷 [Leia esta documentação em português](README_pt-BR.md) · 🇪🇸 Estás leyendo la versión en español.

Instalador **transparente y auditable** que deja un equipo Windows listo para usar
**QGIS** con **Claude AI** vía el Model Context Protocol (MCP): instala lo que
falte, lo configura y **comprueba que el servidor MCP responde** antes de decir
que terminó.

Versión actual: **2.1.0** — ver [`CHANGELOG.md`](CHANGELOG.md).

## Dos formas de instalar

No necesitas Python ni permisos de administrador para ninguna de las dos.

### A. El `.exe` (lo más simple)

1. Descarga `qgis-mcp-installer.exe` desde
   [Releases](https://github.com/lefcgis/qgis-mcp-installer/releases).
2. Doble clic. Enter acepta los valores por defecto.

El `.exe` **aún no lleva firma de código**, así que Windows puede mostrar el aviso
azul de SmartScreen («Windows protegió su PC» → *Más información* → *Ejecutar de
todas formas*) o un antivirus puede retenerlo. Si no te deja abrirlo, usa la
forma B.

### B. `instalar.cmd` (si Windows no deja abrir el `.exe`)

1. En la página del repositorio: **Code → Download ZIP**, y **extrae el ZIP
   completo**.
2. Doble clic en `instalar.cmd`.

`instalar.cmd` ejecuta exactamente el mismo código, pero sin ningún ejecutable
propio: descarga `uv` con `curl.exe`, comprueba su SHA-256 con `certutil.exe` y
lo extrae con `tar.exe` (las tres vienen con Windows 10/11), instala un Python
propio y lanza `etl_installer.py`.

### Con Python ya instalado (3.10 o superior)

```bash
python etl_installer.py
```

## Qué hace (6 pasos + verificación)

| Paso | Acción | Cómo |
|------|--------|------|
| 1 | **Claude Desktop** | Lo detecta (MSIX, por usuario o clásica). Si falta, descarga el `Setup.exe` oficial de Anthropic, verifica su firma e instala **por usuario, sin administrador**; después lo lleva a **la última versión estable** que publica el canal oficial (`RELEASES`) y comprueba la versión y la firma del `claude.exe` instalado. Si ya estaba instalado, lo actualiza cuando es una instalación por usuario |
| 2 | **QGIS 3.44 LTR** | Lo detecta **leyendo la versión del binario**; un QGIS de otra serie (3.40, 4.x) no cuenta. Si falta — con admin: el último MSI 3.44.x de qgis.org. **Sin admin: OSGeo4W en tu carpeta de usuario (cero UAC)**. Tras instalar vuelve a leer la versión y, si no es 3.44.x, el paso falla. Si hay un parche nuevo y la instalación es la propia, la actualiza |
| 3 | **Entorno de Python** | Descarga `uv` (hash fijado) y un CPython 3.12 propio; instala las librerías en una carpeta aislada. No usa el Python del sistema ni el de QGIS |
| 4 | **Plugin + servidor MCP** | Descarga el fork ([lefcgis/qgis-mcp](https://github.com/lefcgis/qgis-mcp), con fallback al upstream) e instala el servidor |
| 5 | **Configura QGIS** | Copia el plugin al perfil activo y lo habilita (crea el perfil si QGIS nunca se abrió) |
| 6 | **Configura Claude** | Añade la entrada `qgis` a `claude_desktop_config.json` sin tocar lo demás, con respaldo |
| 7 | **Verificación** | Arranca el servidor MCP **igual que lo hará Claude Desktop** y comprueba que responde y lista sus herramientas |

Si el paso 7 no pasa, el instalador **no** dice «instalación completa»: dice qué
falló y dónde está el log.

Al terminar:

1. Abre QGIS → menú **Complementos → QGIS MCP → Start Server**.
2. Cierra Claude Desktop **por completo** (icono de la bandeja del sistema →
   *Salir*; cerrar la ventana no basta) y vuelve a abrirlo.
3. En Claude, pide: «haz ping a QGIS».

## Dónde queda cada cosa

Todo vive en la carpeta raíz que elijas (por defecto `C:\Users\<tú>\qgis-mcp`):

```
qgis-mcp\
├── tools\uv\          uv.exe (versión y hash fijados en manifest.py)
├── python\            CPython 3.12 propio (no es el del sistema)
├── env\
│   ├── site-packages\ librerías del servidor (mcp, pydantic, …)
│   └── run_server.py  lanzador que ejecuta Claude Desktop
├── server\            copia auditable del código del servidor (src/, pyproject.toml)
├── qgis\              QGIS LTR, solo si se instaló sin administrador
├── downloads\         lo descargado
└── logs\              un log con fecha por cada ejecución
```

Fuera de esa carpeta solo se toca:

- `%APPDATA%\QGIS\QGIS3\profiles\<perfil>\` — el plugin y **una línea** de
  `QGIS3.ini` (con respaldo `QGIS3.ini.bak-qgismcp-<fecha>`).
- `%APPDATA%\Claude\claude_desktop_config.json` — la entrada `mcpServers.qgis`
  (con respaldo `.bak-<fecha>`).

La entrada que se escribe en Claude es:

```json
{
  "mcpServers": {
    "qgis": {
      "command": "C:\\Users\\<tú>\\qgis-mcp\\python\\cpython-3.12.x-windows-x86_64-none\\python.exe",
      "args": ["-I", "C:\\Users\\<tú>\\qgis-mcp\\env\\run_server.py"]
    }
  }
}
```

Rutas absolutas: no depende del `PATH` ni del directorio de trabajo.

## Opciones

```bash
# Ver el plan completo SIN tocar el sistema
python etl_installer.py --dry-run

# Instalación desatendida
python etl_installer.py --non-interactive --base-dir "C:/qgis-mcp"

# "Ya tengo Claude y QGIS; solo configúrame el resto"
python etl_installer.py --non-interactive --assume-installed claude,qgis

# Solo algunos pasos (re-desplegar el plugin, reconfigurar y verificar)
python etl_installer.py --steps 4-7

# Solo verificar una instalación existente
python etl_installer.py --steps 7

# QGIS sin administrador aunque seas administrador
python etl_installer.py --qgis-install user

# Que el servidor del plugin arranque solo al abrir QGIS (sin pulsar Start Server)
python etl_installer.py --autostart

# Otro perfil de QGIS (por defecto: el perfil activo)
python etl_installer.py --profile trabajo

# Otro fork del plugin
python etl_installer.py --plugin-url "https://github.com/<USUARIO>/qgis-mcp/archive/refs/heads/main.zip"

# Idioma (por defecto detecta el de Windows): es | pt
python etl_installer.py --lang pt

# Quitar el plugin y la entrada de Claude (no desinstala Claude ni QGIS)
python etl_installer.py --uninstall
```

Las mismas opciones valen para `qgis-mcp-installer.exe` e `instalar.cmd`.

**Códigos de salida:** `0` todo correcto · `1` un paso falló · `2` completado,
pero queda algo por hacer a mano (se indica qué) · `130` cancelado.

## Si algo falla

| Síntoma | Causa habitual | Qué hacer |
|---|---|---|
| Windows no deja abrir el `.exe` | SmartScreen / antivirus / Smart App Control: el `.exe` no está firmado | Usa `instalar.cmd` |
| Paso 1: «No pude resolver la dirección oficial…» / «no dejó la aplicación instalada» | Sin internet, proxy o antivirus que bloquea `downloads.claude.ai` | Instálalo desde <https://claude.com/download>; la configuración ya quedó escrita, no hace falta repetir el instalador |
| Paso 1: Claude quedó en una versión anterior a la del canal | La actualización no pudo completarse | Abre Claude Desktop (se actualiza solo) o repite `--steps 1` |
| Paso 2: «qgis-ltr … ya es la X, que no es de la serie 3.44 LTR» | OSGeo4W pasó a otra serie LTR | El instalador no instala otra serie. Usa `--qgis-install msi` (admin) o espera una versión nueva del instalador |
| Paso 7: «El QGIS instalado es X, NO de la serie 3.44 LTR» | Solo hay un QGIS de otra serie | Ejecuta `--steps 2 --force-install qgis` |
| Paso 2: «la carpeta … es demasiado larga» | OSGeo4W no admite rutas largas (límite de 260 de Windows) | Elige una raíz corta, p. ej. `C:\qgis-mcp` |
| Paso 2: espacio insuficiente | QGIS necesita ~6 GB entre descarga e instalación | Libera espacio u otra unidad con `--base-dir` |
| Pasos 3–4: falla una descarga | Proxy, antivirus o sin internet | Reintenta; el instalador ya hace 3 intentos por descarga |
| Paso 7: «el servidor MCP NO respondió» | Un antivirus bloqueó el Python propio | Añade una excepción para la carpeta raíz y ejecuta `--steps 3-7` |
| Claude no muestra las herramientas de QGIS | Claude Desktop no se reinició del todo | Bandeja del sistema → *Salir* y volver a abrir |
| Claude las muestra pero «no conecta con QGIS» | Falta pulsar *Start Server* en QGIS | Complementos → QGIS MCP → Start Server |
| El plugin no aparece en QGIS | Se instaló en otro perfil | `--profile <nombre>` y `--steps 5,7` |

Cada ejecución deja un log completo en `<raíz>\logs\`. Si pides ayuda, adjunta
ese archivo.

Para probarlo en un equipo nuevo paso a paso, ver [`TESTING.md`](TESTING.md).

## Integridad y seguridad (por diseño)

- **Todo declarado en claro**: cada URL que se descarga vive en `manifest.py`.
- **Firma Authenticode** antes de ejecutar: Claude (`Anthropic`), QGIS y
  OSGeo4W (`OPEN SOURCE GEOSPATIAL`). Un archivo que no pasa la verificación se
  borra y no se ejecuta.
- **SHA-256 fijado** para `uv`, igual al que publica su propio release.
- **Aislado**: nada se instala en el Python del sistema ni en el de QGIS.
- **Respaldo** de `claude_desktop_config.json` y de `QGIS3.ini` antes de tocarlos.
- **Sin ejecutables propios sin firma en tiempo de ejecución**: el servidor MCP
  se lanza con el `python.exe` de la distribución, no con un lanzador de entorno
  virtual (Smart App Control los bloquea).

> ⚠️ El plugin QGIS MCP expone la herramienta `execute_code`, que ejecuta código
> Python/PyQGIS arbitrario en la máquina. Instálalo solo desde fuentes en las que
> confíes y no dejes el servidor MCP activo si no lo estás usando.

### Integridad de los releases

Los `.exe` de [Releases](https://github.com/lefcgis/qgis-mcp-installer/releases)
los construye GitHub Actions desde el código público de este repositorio, sin
ofuscar, y cada release publica su **SHA-256**:

```powershell
Get-FileHash .\qgis-mcp-installer.exe -Algorithm SHA256
# compara con el SHA256SUMS.txt del release
```

Se solicitó la firma gratuita de **SignPath Foundation** (jul 2026); pidieron que
el proyecto gane primero visibilidad pública. El workflow de firma está preparado
y se activará cuando haya certificado. Ver [`SIGNING.md`](SIGNING.md).

## Desarrollo

```bash
# Pruebas unitarias (solo librería estándar)
python -m unittest discover -s tests -v

# Construir el .exe
python -m pip install -r requirements-build.txt
python build_exe.py --clean        # -> dist/qgis-mcp-installer.exe
```

```
qgis-mcp-installer/
├── etl_installer.py         el instalador (solo librería estándar de Python)
├── manifest.py              ÚNICA fuente de URLs, versiones y hashes
├── messages.py              textos en español y portugués
├── instalar.cmd             arranque sin Python ni .exe
├── build_exe.py             empaqueta el .exe con PyInstaller (sin ofuscar)
├── tests/                   pruebas unitarias
├── .github/workflows/       CI (pruebas en Windows limpio) y release
├── TESTING.md               cómo probarlo en un equipo nuevo
├── CHANGELOG.md             cambios por versión
├── SIGNING.md  sign.ps1     firma de código
├── UPSTREAM_REVIEW.md       revisión de nkarasiak/qgis-mcp
└── fork_patch/              kit para publicar el fork del plugin
```

## Créditos y licencia

- Plugin y servidor MCP: **Nicolas Karasiak** — https://github.com/nkarasiak/qgis-mcp (MIT, © 2025).
- Instalador ETL y mejoras del fork: **Luis Ferrer** (MIT, © 2026).

Distribuido bajo licencia MIT, preservando la atribución original. Ver `LICENSE`
y `fork_patch/NOTICE`.
