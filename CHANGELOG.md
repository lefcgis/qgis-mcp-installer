# Cambios

## 2.1.0 — 2026-11-18

Corrección pedida tras la 2.0.0: el instalador tiene que dejar instalada **la
última versión estable de Claude Desktop** y **QGIS 3.44 LTR**, y no dar por
bueno nada que no lo sea.

### Errores corregidos

- **Claude Desktop (paso 1) no quedaba instalado sin administrador.** Causa
  exacta: el instalador descargaba el paquete **MSIX** y lo registraba con
  `Add-AppxPackage`. Ese paquete declara un servicio de Windows, y registrar un
  paquete con servicio exige elevación: sin ella Windows lo rechaza con
  `0x80073D28` («Administrator privileges required to install packaged
  service»; registro `Microsoft-Windows-AppXDeploymentServer/Operational`,
  eventos 404 y 605 «Failure in the Approved state handler», con el instalador
  de la 2.0.0 el 2026-11-18 17:33). No es política, ni sideloading, ni firma, ni
  dependencia faltante: es el requisito del propio paquete. Por eso la 2.0.0
  caía a una guía manual (código de salida 2).
  Ahora usa el instalador **por usuario** de Anthropic (`Setup.exe`, Squirrel,
  firmado por «Anthropic, PBC»), que instala en `%LOCALAPPDATA%\AnthropicClaude`
  **sin administrador**.
- **El redirect «MSIX latest» no es la última versión.** El 2026-11-18 servía la
  5.11492.5 mientras el canal oficial de actualizaciones (`RELEASES`, el mismo
  que consulta la aplicación) ya publicaba la 6.6395.1. El instalador consulta
  ese canal, instala y luego ejecuta `Update.exe --update` contra él, y exige
  que la versión instalada sea la del canal. Si no lo logra, queda instalado
  pero lo dice como advertencia (código 2), no como éxito.
- **QGIS: la versión estaba fijada a mano (3.44.15-2) y nada comprobaba lo que
  quedaba instalado.** Con `qgis-ltr` en OSGeo4W, el día que el paquete pase a
  otra serie el instalador habría dejado esa serie y reportado «QGIS LTR
  instalado». Ahora:
  - Con administrador, el MSI se resuelve leyendo el índice de `qgis.org` y se
    toma el último `3.44.x` (en orden numérico: 3.44.10 > 3.44.9). Si el índice
    no responde, usa la última versión verificada.
  - Sin administrador, antes de instalar se lee `setup.ini` de OSGeo4W: si
    `qgis-ltr` ya no es 3.44.x, **no instala** y lo explica.
  - Tras instalar se lee la **versión del propio binario** (`qgis_process
    --version`; respaldo: la base de paquetes de OSGeo4W). Si no es 3.44.x, el
    paso 2 falla.
  - La detección ya no mira el nombre de la carpeta: lee la versión del binario,
    y un QGIS de otra serie (3.40, 4.x) **no cuenta** como instalado: se instala
    la 3.44 aparte.
  - Si hay un parche nuevo de 3.44 y la instalación es la propia (OSGeo4W de
    usuario), la actualiza; si es ajena, avisa.
- **El paso 7 daba «verificado» sin mirar QGIS ni Claude.** Ahora comprueba que
  haya un QGIS 3.44.x (leído del binario) y que Claude Desktop, si está, tenga
  firma válida de Anthropic, e informa si es la última publicada.
- `Setup.exe` y `Update.exe` de Squirrel pueden dejar procesos hijos con la
  salida abierta; se ejecutan con la salida a un archivo y un tiempo máximo, para
  que el instalador no se cuelgue.
- Un bug propio, hallado por las pruebas nuevas: comparar «3.44.15-1» (versión
  de paquete OSGeo4W) con `_version_tuple` daba 3.44.151.

### Cambios de comportamiento

- `--steps 3-7` o `--steps 7` en un equipo **sin QGIS 3.44** ahora falla en el
  paso 7 (antes lo pasaba por alto). Si tu QGIS está en un lugar no estándar,
  usa `--assume-installed qgis`.
- El paso 1 ya no intenta `Add-AppxProvisionedPackage` ni `Add-AppxPackage`. Las
  instalaciones MSIX que ya existan se siguen detectando y configurando.
- `manifest.py`: `CLAUDE_DESKTOP` (MSIX) pasó a `CLAUDE_SETUP`; nuevas constantes
  del canal oficial y de la serie de QGIS (`QGIS_SERIES`).

### Pruebas

53 pruebas unitarias (20 nuevas en `tests/test_claude_qgis.py`). Pruebas reales
y lo que no se pudo probar: `TESTING.md`.

## 2.0.0 — 2026-11-18

Revisión completa tras reportes de que el instalador «no quedaba al 100 %» en
algunos equipos. Se reprodujeron los fallos en un Windows 11 con Smart App
Control activado y sin administrador, y se corrigió la causa de cada uno.

### Errores corregidos

- **El servidor MCP no arrancaba aunque el instalador decía «instalación
  completa».** El paso 6 configuraba Claude con `uv run --no-sync server.py`,
  que no usa el entorno creado en el paso 3: el servidor moría con
  `ModuleNotFoundError: No module named 'mcp'`. Ahora Claude ejecuta un
  intérprete propio con las librerías instaladas, por ruta absoluta.
- **Smart App Control bloqueaba el `python.exe` del entorno virtual** (es un
  lanzador sin firma). Ya no se crea ningún venv: se usa el `python.exe` real de
  la distribución y las librerías van a `env\site-packages`.
- **Dependía del Python que hubiera en el equipo.** Con el `.exe`, buscaba
  `python` en el PATH (que en Windows suele ser el alias de la Microsoft Store) o
  el Python de QGIS. Ahora descarga `uv` (hash fijado) y un CPython 3.12 propio.
- **Claude Desktop no se detectaba** cuando estaba instalado como paquete MSIX
  (la forma en que se distribuye hoy), y se descargaba un instalador de octubre
  de 2025 con un parámetro silencioso que no le correspondía. Ahora se detecta el
  MSIX y se usa el paquete oficial vigente.
- **QGIS se daba por instalado si quedaba una carpeta `QGIS x.y.z\bin` vacía**
  de una desinstalación anterior, y entonces nunca se instalaba. Ahora se exige
  el ejecutable.
- **La instalación de QGIS sin administrador fallaba a media descarga** cuando la
  carpeta raíz era larga (límite de 260 caracteres de Windows). Se acortó la
  carpeta de paquetes y se valida la longitud antes de empezar.
- **El MSI legítimo de QGIS se rechazaba** («Publisher inesperado»): el
  manifiesto esperaba la firma de «QGIS» y el MSI lo firma la OSGeo Foundation.
- **La instalación de QGIS sin administrador podía abortar con `WinError 740`**
  («requiere elevación»): Windows trataba `osgeo4w-setup.exe` como instalador
  que necesita elevar. Ahora se lanza con `RunAsInvoker`.
- **El plugin quedaba sin habilitar en equipos donde QGIS nunca se había
  abierto** (no existía `QGIS3.ini`). Ahora se crea el perfil con el plugin
  habilitado.
- **`QGIS3.ini` se reescribía entero con `configparser`**, que no entiende el
  formato INI de Qt y podía alterar otras claves. Ahora se edita una sola línea y
  el resto queda byte a byte, con respaldo.
- **Un `claude_desktop_config.json` guardado con BOM** (Bloc de notas,
  PowerShell) se trataba como inválido y se reemplazaba, perdiendo los demás
  servidores MCP. Ahora se lee correctamente.
- **Una descarga dañada quedaba en caché** y todos los reintentos fallaban con el
  mismo archivo. Ahora lo que no pasa la verificación se borra, y las descargas
  de ramas y de «latest» no se cachean.
- **El asistente se cancelaba al pulsar Enter** en «¿Continuar?» (el valor por
  defecto era No) y **la ventana del `.exe` se cerraba al terminar** sin dejar
  leer el resultado.
- El plugin iba al perfil `default` aunque el perfil activo fuera otro, y a
  `QGIS4` si existía esa carpeta aunque se usara QGIS 3. Ahora usa el perfil
  activo y cubre cada versión mayor presente.
- En la consola clásica de Windows los colores salían como `←[32m`.
- La verificación de firma fallaba si la ruta tenía un apóstrofo, y podía fallar
  al lanzar el instalador desde PowerShell 7.
- `--steps 9` terminaba en una excepción en vez de un mensaje claro.

### Nuevo

- **Paso 7 — Verificación:** arranca el servidor MCP como lo hará Claude Desktop
  (PATH mínimo, directorio neutro) y comprueba que responde y lista sus
  herramientas. Sin eso no hay «instalación completa».
- **`instalar.cmd`:** arranque sin Python y sin el `.exe`, solo con herramientas
  que trae Windows. Para equipos donde no se puede abrir el `.exe` sin firma.
- La configuración de Claude se escribe también en la copia virtualizada del
  paquete MSIX cuando existe.
- `--autostart`: el servidor del plugin arranca solo al abrir QGIS (opcional).
- `--uninstall`, `--force-install`, `--version`, rangos en `--steps` (`3-7`),
  `--profile auto`.
- Reintentos de descarga (3), comprobación de espacio libre antes de instalar
  QGIS, aviso si QGIS o Claude Desktop están abiertos.
- El log incluye la salida de los programas ejecutados y los datos del entorno.
- Pruebas unitarias (`tests/`) y CI en Windows limpio.
- QGIS 3.44.15 (antes 3.44.12).

### Cambios que conviene conocer

- La carpeta `venv\` de versiones anteriores ya no se usa; puede borrarse.
- El código de salida `2` significa «completado, pero queda algo por hacer a
  mano».

## 1.0.0, 1.1.0 y 1.2.0 — 2026-07-15

Primeras versiones públicas. No se llevó registro de cambios entre ellas.
