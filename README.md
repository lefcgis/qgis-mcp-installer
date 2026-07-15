# QGIS MCP — Instalador ETL

Instalador **transparente y auditable** que aprovisiona de cero un equipo Windows
para usar **QGIS** con **Claude AI** vía el Model Context Protocol (MCP).

Empaquetable como un único `.exe` para que el usuario final no tenga que instalar
Python ni manejar archivos sueltos — pero **sin ofuscación ni evasión**: el código
que va dentro es exactamente el de este repositorio, publicado y verificable.

## Integridad de los releases

Los `.exe` publicados en [GitHub Releases](https://github.com/lefcgis/qgis-mcp-installer/releases)
**aún no llevan firma de código de un tercero**. En su lugar, cada release incluye
su **hash SHA-256**, y el binario lo construye GitHub Actions directamente desde
el código público de este repositorio (sin ofuscar), por lo que cualquiera puede
auditarlo o reproducir la construcción.

Para verificar tu descarga en PowerShell:

```powershell
Get-FileHash .\qgis-mcp-installer.exe -Algorithm SHA256
# compara el resultado con el SHA-256 publicado en la página del release
```

> Se solicitó la firma gratuita de **SignPath Foundation** (jul 2026); pidieron que
> el proyecto gane primero visibilidad pública (estrellas, usuarios, menciones) y
> reaplicaremos más adelante. El workflow de firma ya está preparado y se activará
> solo cuando haya certificado. Ver `SIGNING.md`.

## Qué hace (los 6 pasos del ETL)

| Paso | Acción | Cómo |
|------|--------|------|
| 1 | Instala **Claude Desktop** | Descarga el instalador oficial (win x64) y lo ejecuta en silencio |
| 2 | Instala **QGIS 3.44 LTR** | Con admin: MSI oficial vía `msiexec`. **Sin admin: OSGeo4W en tu carpeta de usuario (cero UAC)** |
| 3 | Instala **dependencias de Python** | Crea un **venv aislado** con librerías fijadas y actualizadas |
| 4 | Obtiene el **plugin QGIS MCP** | Descarga el fork mejorado de tu GitHub (con fallback al upstream) |
| 5 | Configura **QGIS** | Copia el plugin al perfil y lo habilita en `QGIS3.ini` |
| 6 | Configura **Claude** | Escribe `claude_desktop_config.json` (con respaldo previo) |

*Extract* = descargas · *Transform* = verificación de integridad + preparación ·
*Load* = instalación y configuración.

## Sin permisos de administrador: no hay problema

**No necesitas ser administrador del equipo.** Si QGIS no está instalado, el
paso 2 detecta automáticamente tus permisos:

- **Con administrador** → instala el MSI oficial de QGIS (a nivel máquina,
  en `C:\Program Files`), como siempre.
- **Sin administrador** → usa el **instalador de red OSGeo4W oficial** (firmado
  por la OSGeo Foundation y verificado antes de ejecutarse) para instalar el
  mismo QGIS LTR completo (`qgis-ltr-full`: Python, GDAL, GRASS, processing)
  dentro de **tu carpeta de usuario** (`<raíz>/qgis`). Cero ventanas de UAC.

También puedes forzar la vía con `--qgis-install msi|user|auto` (por defecto
`auto`). Claude Desktop siempre se instala por-usuario, así que **el flujo
completo funciona de punta a punta sin elevación**:

```bash
# instalación completa garantizada sin administrador
python etl_installer.py --qgis-install user
```

## Detección: no reinstala lo que ya tienes

Antes de instalar Claude (paso 1) y QGIS (paso 2), el ETL **detecta** si ya están
en el sistema, muestra la **versión** encontrada y te **pregunta** si ya cuentas
con ese software:

- **Si ya lo tienes** → omite esa instalación y pasa directo a las dependencias
  de Python, el plugin y la configuración. El artefacto deja todo listo sin
  reinstalar nada.
- **Si no tienes nada** → descarga e instala como estaba previsto.

La detección es consciente de la versión mayor de QGIS: despliega el plugin en el
perfil **QGIS4** o **QGIS3** según cuál tengas (probado con QGIS 4.0.0 y 3.44 LTR).
Si tu QGIS es anterior a 3.28, avisa (el plugin exige ≥ 3.28).

En modo desatendido usa la detección automática, o fuerza el resultado con
`--assume-installed`:

```bash
# "Ya tengo Claude y QGIS; solo configúrame el resto"
python etl_installer.py --non-interactive --base-dir "D:/QGIS-Claude" \
    --assume-installed claude,qgis
```

## Uso

```bash
# Asistente interactivo (el usuario elige las carpetas)
python etl_installer.py

# Ver el plan completo SIN tocar el sistema
python etl_installer.py --non-interactive --base-dir "D:/QGIS-Claude" --dry-run

# Instalación desatendida completa
python etl_installer.py --non-interactive --base-dir "D:/QGIS-Claude"

# Solo algunos pasos (ej. re-desplegar el plugin y reconfigurar)
python etl_installer.py --steps 4,5,6

# Usar tu fork concreto sin recompilar
python etl_installer.py --plugin-url "https://github.com/<TU_USUARIO>/qgis-mcp/archive/refs/heads/main.zip"
```

El usuario elige **todas** las carpetas de instalación (raíz, descargas, venv,
código del servidor). Cada ejecución deja un **log con fecha** en `<raíz>/logs/`.

## Construir el `.exe`

```bash
python -m pip install -r requirements-build.txt
python build_exe.py --clean
# -> dist/qgis-mcp-installer.exe
```

### Firma de código (recomendado para distribución pública)

Un `.exe` sin firmar dispara avisos de SmartScreen y antivirus. La forma correcta
de generar confianza **no es esconderse, sino firmar**. Dos vías:

- **Automática vía SignPath Foundation (PENDIENTE de aprobación)** — el workflow
  `.github/workflows/build-and-sign.yml` ya está preparado para firmar cada
  release; se activará cuando SignPath apruebe el proyecto (ver **`SIGNING.md`**).
  Mientras tanto, el workflow publica el `.exe` **sin firmar** junto a su SHA-256.
- **Manual** — con tu propio certificado, usando `sign.ps1`:
  ```powershell
  .\sign.ps1 -PfxPath "C:\certs\mi-cert.pfx" -Password "****"
  # o con certificado EV en token de hardware:
  .\sign.ps1 -Thumbprint "A1B2C3..."
  ```

Publica siempre el **SHA-256** del `.exe` junto a la descarga (lo generan tanto
`sign.ps1` como el workflow) para verificación independiente del certificado.

## Integridad y seguridad (por diseño)

- **Firma Authenticode**: los instaladores de Claude y QGIS se verifican por
  publisher (`Anthropic`, `QGIS`) y validez de firma **antes** de ejecutarse.
  Nada corre a ciegas. (`--skip-signature` existe pero avisa; no lo uses en
  distribución.)
- **SHA-256 opcional**: fija hashes en `manifest.py` para builds reproducibles.
- **venv aislado**: las dependencias de Python NUNCA tocan el Python del sistema
  ni el de QGIS.
- **Respaldo**: el `claude_desktop_config.json` existente se respalda antes de
  modificarlo.
- **Todo declarado en claro**: cada URL que se descarga vive en `manifest.py`.

> ⚠️ El plugin QGIS MCP expone la herramienta `execute_code`, que ejecuta código
> Python/PyQGIS arbitrario en la máquina. Instálalo solo desde fuentes en las que
> confíes y no dejes el servidor MCP activo si no lo estás usando.

## Estructura del proyecto

```
qgis_mcp_installer/
├── etl_installer.py         # el ETL (solo librería estándar de Python)
├── manifest.py              # ÚNICA fuente de URLs, versiones y checksums
├── build_exe.py             # empaqueta el .exe con PyInstaller (sin ofuscar)
├── requirements-build.txt   # PyInstaller fijado (solo para construir)
├── LICENSE                  # MIT: Karasiak (original) + Ferrer (mejoras)
├── UPSTREAM_REVIEW.md        # errores/mejoras hallados en nkarasiak/qgis-mcp
└── fork_patch/              # kit para publicar tu fork mejorado (paso 4)
    ├── LICENSE  ├── NOTICE  └── PUBLISH.md
```

## Créditos y licencia

- Plugin y servidor MCP: **Nicolas Karasiak** — https://github.com/nkarasiak/qgis-mcp (MIT, © 2025).
- Instalador ETL y mejoras del fork: **Luis Ferrer** (MIT, © 2026).

Distribuido bajo licencia MIT, preservando la atribución original. Ver `LICENSE`
y `fork_patch/NOTICE`.
